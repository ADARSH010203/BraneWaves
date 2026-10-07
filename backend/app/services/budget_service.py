"""Atomic task budget reservations for concurrent LLM calls."""
from __future__ import annotations

import json
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase


class BudgetReservationError(RuntimeError):
    """Raised when a task cannot reserve enough budget for an LLM call."""


def estimate_llm_reservation(messages: list[dict[str, Any]], max_tokens: int) -> float:
    """Return a conservative USD upper-bound reservation for configured models.

    The bound intentionally uses the highest pricing tier currently supported by
    BaseAgent (prompt $0.80/M, completion $4.00/M) plus a safety margin. This is
    a reservation only; unused budget is released after the provider returns.
    """
    serialized = json.dumps(messages, ensure_ascii=False, default=str)
    # Conservative approximation: UTF-8/chat tokenization is normally much less
    # dense than one token per two characters.
    estimated_prompt_tokens = max(1, len(serialized) // 2)
    prompt_cost = estimated_prompt_tokens * 0.80 / 1_000_000
    completion_cost = max_tokens * 4.00 / 1_000_000
    return round(max(0.0001, (prompt_cost + completion_cost) * 1.25), 6)


async def reserve_task_budget(
    db: AsyncIOMotorDatabase,
    task_id: str,
    user_id: str,
    amount_usd: float,
) -> None:
    """Atomically reserve task budget, accounting for concurrent LLM calls."""
    amount_usd = max(0.0, float(amount_usd))
    result = await db.tasks.update_one(
        {
            "_id": task_id,
            "user_id": user_id,
            "status": {"$nin": ["failed", "cancelled", "completed"]},
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


async def finalize_task_budget(
    db: AsyncIOMotorDatabase,
    task_id: str,
    user_id: str,
    reserved_usd: float,
    actual_usd: float,
) -> None:
    """Release a reservation and charge the actual provider cost."""
    await db.tasks.update_one(
        {"_id": task_id, "user_id": user_id},
        {
            "$inc": {
                "budget.reserved_usd": -float(reserved_usd),
                "budget.spent_usd": float(actual_usd),
            }
        },
    )


async def release_task_budget(
    db: AsyncIOMotorDatabase,
    task_id: str,
    user_id: str,
    reserved_usd: float,
) -> None:
    """Release a reservation after a failed/cancelled provider call."""
    await db.tasks.update_one(
        {"_id": task_id, "user_id": user_id},
        {"$inc": {"budget.reserved_usd": -float(reserved_usd)}},
    )
