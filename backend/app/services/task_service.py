"""
ARC Platform — Task Service
Task CRUD and orchestration dispatch.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import get_settings
from app.database import get_redis
from app.models.task import (
    TaskBudget, TaskCreate, TaskResponse, TaskStatus,
)

logger = logging.getLogger("arc.services.task")
settings = get_settings()


async def create_task(db: AsyncIOMotorDatabase, user_id: str, data: TaskCreate) -> TaskResponse:
    """Create a new task and enqueue it for execution."""
    task_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    user = await db.users.find_one({"_id": user_id}, {"usage_quota_usd": 1})
    if not user:
        raise ValueError("User not found")

    usage_rows = await db.usage_cost.aggregate([
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": None, "spent": {"$sum": "$cost_usd"}}},
    ]).to_list(length=1)
    lifetime_spent = float(usage_rows[0]["spent"]) if usage_rows else 0.0
    remaining_quota = max(0.0, float(user.get("usage_quota_usd", 10.0)) - lifetime_spent)
    if remaining_quota < 0.01:
        raise ValueError("Account usage quota exhausted")

    requested_budget = data.budget_usd if data.budget_usd is not None else settings.MAX_TASK_BUDGET_USD
    effective_budget = min(requested_budget, settings.MAX_TASK_BUDGET_USD, remaining_quota)
    effective_steps = min(data.max_steps or settings.MAX_STEPS_PER_TASK, settings.MAX_STEPS_PER_TASK)

    budget = TaskBudget(
        max_usd=effective_budget,
        max_steps=effective_steps,
    )

    task_doc = {
        "_id": task_id,
        "user_id": user_id,
        "title": data.title,
        "description": data.description,
        "status": TaskStatus.PENDING.value,
        "budget": budget.model_dump(),
        "tags": data.tags,
        "plan": None,
        "result_summary": None,
        "report_id": None,
        "error": None,
        "created_at": now,
        "updated_at": now,
        "completed_at": None,
    }
    await db.tasks.insert_one(task_doc)

    # Enqueue for background worker or fallback to in-memory
    try:
        redis = get_redis()
        await redis.ping()  # Verify connection
        await redis.rpush(
            "task_queue",
            json.dumps({"task_id": task_id, "user_id": user_id}),
        )
        logger.info("Task enqueued: %s", task_id)
    except Exception as e:
        if settings.ENVIRONMENT == "production":
            # A production API process is not a durable job queue. Roll back the
            # task creation so callers can retry cleanly when Redis recovers.
            await db.tasks.delete_one({"_id": task_id, "user_id": user_id})
            logger.error("Redis unavailable in production; task %s was not accepted: %s", task_id, e)
            raise RuntimeError("Task queue is unavailable. Please try again shortly.") from e

        logger.warning(
            "Redis unavailable, using development-only in-memory execution fallback for task %s (Error: %s)",
            task_id, e,
        )
        import asyncio
        from app.agents.orchestrator import TaskOrchestrator

        async def run_orchestrator_fallback():
            logger.info("Starting in-memory orchestrator for %s", task_id)
            try:
                orchestrator = TaskOrchestrator(task_id=task_id, user_id=user_id)
                await orchestrator.execute()
            except Exception as ex:
                logger.exception("In-memory orchestrator failed for %s: %s", task_id, ex)

        asyncio.create_task(run_orchestrator_fallback())

    return TaskResponse(
        id=task_id,
        user_id=user_id,
        title=data.title,
        description=data.description,
        status=TaskStatus.PENDING,
        budget=budget,
        tags=data.tags,
        created_at=now,
        updated_at=now,
    )


async def get_task(db: AsyncIOMotorDatabase, task_id: str, user_id: str) -> TaskResponse | None:
    """Get a task by ID, scoped to user."""
    doc = await db.tasks.find_one({"_id": task_id, "user_id": user_id})
    if not doc:
        return None
    return _doc_to_response(doc)


async def list_tasks(
    db: AsyncIOMotorDatabase,
    user_id: str,
    page: int = 1,
    page_size: int = 20,
    status_filter: str | None = None,
) -> tuple[list[TaskResponse], int]:
    """List tasks for a user with pagination."""
    query: dict[str, Any] = {"user_id": user_id}
    if status_filter:
        query["status"] = status_filter

    total = await db.tasks.count_documents(query)
    cursor = db.tasks.find(query).sort("created_at", -1).skip((page - 1) * page_size).limit(page_size)
    docs = await cursor.to_list(length=page_size)

    return [_doc_to_response(d) for d in docs], total


async def get_task_steps(db: AsyncIOMotorDatabase, task_id: str, user_id: str) -> list[dict]:
    """Get all steps for a task."""
    # Verify task belongs to user
    task = await db.tasks.find_one({"_id": task_id, "user_id": user_id})
    if not task:
        return None  # BUG-02 FIX: was returning [] — route checks None for 404

    cursor = db.task_steps.find({"task_id": task_id}).sort("order", 1)
    steps = await cursor.to_list(length=200)

    # Remove embeddings/large data for response
    for step in steps:
        step["id"] = step.pop("_id")
    return steps


async def get_task_result(db: AsyncIOMotorDatabase, task_id: str, user_id: str) -> dict | None:
    """Get the final result/report for a task."""
    task = await db.tasks.find_one({"_id": task_id, "user_id": user_id})
    if not task:
        return None

    result: dict[str, Any] = {
        "task_id": task_id,
        "status": task["status"],
        "result_summary": task.get("result_summary"),
    }

    # Get report if available
    if task.get("report_id"):
        report = await db.reports.find_one({"_id": task["report_id"]})
        if report:
            report["id"] = report.pop("_id")
            result["report"] = report

            # Get citations
            citations = await db.citations.find({"report_id": task["report_id"]}).to_list(length=100)
            for c in citations:
                c["id"] = c.pop("_id")
            result["citations"] = citations

    # Get cost summary
    pipeline = [
        {"$match": {"task_id": task_id}},
        {"$group": {
            "_id": None,
            "total_cost": {"$sum": "$cost_usd"},
            "total_tokens": {"$sum": "$tokens_total"},
            "num_runs": {"$sum": 1},
        }},
    ]
    cost_cursor = db.usage_cost.aggregate(pipeline)
    cost_results = await cost_cursor.to_list(length=1)
    if cost_results:
        result["cost_summary"] = {
            "total_cost_usd": cost_results[0]["total_cost"],
            "total_tokens": cost_results[0]["total_tokens"],
            "num_agent_runs": cost_results[0]["num_runs"],
        }

    return result



async def cancel_task(db: AsyncIOMotorDatabase, task_id: str, user_id: str) -> tuple[bool, str]:
    """
    Cancel a running or planning task.

    Sets a Redis cancel flag that the orchestrator checks before each step,
    updates MongoDB status, and publishes a cancellation event.

    Returns:
        (success, message) tuple.
    """
    task = await db.tasks.find_one({"_id": task_id, "user_id": user_id})
    if not task:
        return False, "Task not found"

    cancellable = {TaskStatus.RUNNING.value, TaskStatus.PLANNING.value, TaskStatus.PENDING.value}
    if task["status"] not in cancellable:
        return False, f"Cannot cancel task with status '{task['status']}'. Only running, planning, or pending tasks can be cancelled."

    now = datetime.now(timezone.utc)

    # Set Redis cancel flag — orchestrator checks this before each step
    try:
        redis = get_redis()
        await redis.set(f"task:{task_id}:cancel", "1", ex=3600)
        logger.info("Cancel flag set in Redis for task %s", task_id)
    except Exception as e:
        logger.warning("Could not set Redis cancel flag for task %s: %s", task_id, e)

    # Update task status in MongoDB
    await db.tasks.update_one(
        {"_id": task_id},
        {"$set": {
            "status": TaskStatus.CANCELLED.value,
            "error": "Task cancelled by user",
            "updated_at": now,
        }},
    )

    # Publish cancellation event for WebSocket streaming
    try:
        redis = get_redis()
        payload = json.dumps({
            "event": "task_status",
            "task_id": task_id,
            "status": "cancelled",
            "timestamp": now.isoformat(),
            "message": "Task cancelled by user",
        })
        await redis.publish(f"task:{task_id}", payload)
        logger.info("Cancellation event published for task %s", task_id)
    except Exception as e:
        logger.warning("Could not publish cancel event for task %s: %s", task_id, e)

    return True, "Task cancellation requested"


def _doc_to_response(doc: dict) -> TaskResponse:
    """Convert MongoDB document to TaskResponse."""
    return TaskResponse(
        id=doc["_id"],
        user_id=doc["user_id"],
        title=doc["title"],
        description=doc["description"],
        status=doc["status"],
        budget=TaskBudget(**doc.get("budget", {})),
        tags=doc.get("tags", []),
        plan=doc.get("plan"),
        result_summary=doc.get("result_summary"),
        report_id=doc.get("report_id"),
        error=doc.get("error"),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
        completed_at=doc.get("completed_at"),
    )
