"""Atomic task and account budget reservations for concurrent LLM calls."""
from __future__ import annotations

import json
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase


class BudgetReservationError(RuntimeError):
    """Raised when a task/account cannot reserve enough budget for an LLM call."""


def estimate_llm_reservation(messages: list[dict[str, Any]], max_tokens: int) -> float:
    """Return a conservative USD upper-bound reservation for configured models."""
    serialized = json.dumps(messages, ensure_ascii=False, default=str)
    estimated_prompt_tokens = max(1, len(serialized) // 2)
    prompt_cost = estimated_prompt_tokens * 0.80 / 1_000_000
    completion_cost = max_tokens * 4.00 / 1_000_000
    return round(max(0.0001, (prompt_cost + completion_cost) * 1.25), 6)


async def _account_committed_usd(db: AsyncIOMotorDatabase, user_id: str) -> float:
    """Return actual task spend plus all in-flight LLM reservations for a user."""
    rows = await db.tasks.aggregate([
        {"$match": {"user_id": user_id}},
        {"$group": {
            "_id": None,
            "spent": {"$sum": {"$ifNull": ["$budget.spent_usd", 0.0]}},
            "reserved": {"$sum": {"$ifNull": ["$budget.reserved_usd", 0.0]}},
        }},
    ]).to_list(length=1)
    if not rows:
        return 0.0
    return float(rows[0].get("spent", 0.0)) + float(rows[0].get("reserved", 0.0))


async def _reserve_with_checks(
    db: AsyncIOMotorDatabase,
    task_id: str,
    user_id: str,
    amount_usd: float,
    blocked_statuses: list[str],
    enforce_account_quota: bool,
) -> None:
    if enforce_account_quota:
        user = await db.users.find_one({"_id": user_id}, {"usage_quota_usd": 1})
        if not user:
            raise BudgetReservationError("User account not found")
        quota = float(user.get("usage_quota_usd", 10.0))
        committed = await _account_committed_usd(db, user_id)
        if committed + amount_usd > quota + 1e-9:
            raise BudgetReservationError("Account usage quota does not have enough remaining capacity")

    result = await db.tasks.update_one(
        {
            "_id": task_id,
            "user_id": user_id,
            "status": {"$nin": blocked_statuses},
            "$expr": {
                "$lte": [
                    {
                        "$add": [
                            {"$ifNull": ["$budget.spent_usd", 0.0]},
                            {"$ifNull": ["$budget.reserved_usd", 0.0]},
                            amount_usd,
                        ]
                    },
                    "$budget.max_usd",
                ]
            },
        },
        {"$inc": {"budget.reserved_usd": amount_usd}},
    )
    if result.modified_count != 1:
        raise BudgetReservationError("Task budget does not have enough remaining capacity for this LLM call")


async def reserve_task_budget(
    db: AsyncIOMotorDatabase,
    task_id: str,
    user_id: str,
    amount_usd: float,
    *,
    allow_completed: bool = False,
    enforce_account_quota: bool = True,
) -> None:
    """Atomically reserve task budget and serialize per-user account quota checks."""
    amount_usd = max(0.0, float(amount_usd))
    blocked_statuses = ["failed", "cancelled"] if allow_completed else ["failed", "cancelled", "completed"]

    # Production task execution already requires Redis. A per-user Redis lock
    # serializes reservations across different tasks/processes for the same user.
    if enforce_account_quota:
        from app.database import get_redis
        redis = get_redis()
        if redis is not None:
            lock = redis.lock(
                f"budget:user:{user_id}",
                timeout=10,
                blocking_timeout=5,
            )
            acquired = await lock.acquire()
            if not acquired:
                raise BudgetReservationError("Could not acquire account budget lock; retry the request")
            try:
                await _reserve_with_checks(
                    db, task_id, user_id, amount_usd, blocked_statuses, True
                )
            finally:
                try:
                    await lock.release()
                except Exception:
                    pass
            return

    await _reserve_with_checks(
        db, task_id, user_id, amount_usd, blocked_statuses, enforce_account_quota
    )


async def finalize_task_budget(
    db: AsyncIOMotorDatabase,
    task_id: str,
    user_id: str,
    reserved_usd: float,
    actual_usd: float,
) -> None:
    """Release a reservation and atomically charge the actual task cost."""
    await db.tasks.update_one(
        {"_id": task_id, "user_id": user_id},
        {"$inc": {
            "budget.reserved_usd": -float(reserved_usd),
            "budget.spent_usd": float(actual_usd),
        }},
    )


async def release_task_budget(
    db: AsyncIOMotorDatabase,
    task_id: str,
    user_id: str,
    reserved_usd: float,
) -> None:
    """Release an in-flight reservation after a failed/cancelled provider call."""
    await db.tasks.update_one(
        {"_id": task_id, "user_id": user_id},
        {"$inc": {"budget.reserved_usd": -float(reserved_usd)}},
    )
