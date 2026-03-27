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

    budget = TaskBudget(
        max_usd=data.budget_usd or settings.MAX_TASK_BUDGET_USD,
        max_steps=data.max_steps or settings.MAX_STEPS_PER_TASK,
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
        logger.warning(
            "Redis unavailable, using IN-MEMORY execution fallback for task %s (Error: %s)", 
            task_id, e
        )
        # Fallback for college project so it always works even if Redis isn't running
        import asyncio
        from app.agents.orchestrator import TaskOrchestrator
        
        async def run_orchestrator_fallback():
            logger.info("Starting in-memory orchestrator for %s", task_id)
            try:
                orchestrator = TaskOrchestrator(task_id=task_id, user_id=user_id)
                await orchestrator.execute()
            except Exception as ex:
                logger.exception("In-memory orchestrator failed for %s: %s", task_id, ex)
                
        # Run it in background asyncio loop instead of Redis queue
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
        return []

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
