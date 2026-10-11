from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends

from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user

router = APIRouter()
settings = get_settings()


async def _total_spent(db, user_id: str) -> float:
    rows = await db.usage_cost.aggregate([
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": None, "total": {"$sum": "$cost_usd"}}},
    ]).to_list(length=1)
    return float(rows[0]["total"]) if rows else 0.0


@router.get("/summary")
async def get_dashboard_summary(current_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    """Authoritative dashboard/account usage summary."""
    db = get_db()
    user_id = current_user["_id"]

    total_tasks = await db.tasks.count_documents({"user_id": user_id})
    completed_tasks = await db.tasks.count_documents({"user_id": user_id, "status": "completed"})
    active_tasks = await db.tasks.count_documents(
        {"user_id": user_id, "status": {"$in": ["planning", "running"]}}
    )
    active_agents = await db.agent_runs.count_documents(
        {"user_id": user_id, "status": "running"}
    )
    total_runs = await db.agent_runs.count_documents({"user_id": user_id})
    total_spent = await _total_spent(db, user_id)

    quota = float(current_user.get("usage_quota_usd", 10.0))
    remaining = max(0.0, quota - total_spent)
    usage_percent = 0.0 if quota <= 0 else min(100.0, (total_spent / quota) * 100)

    return {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "active_tasks": active_tasks,
        "active_agents": active_agents,
        "total_agent_runs": total_runs,
        "total_spent_usd": round(total_spent, 6),
        "usage_quota_usd": quota,
        "remaining_quota_usd": round(remaining, 6),
        "usage_percent": round(usage_percent, 2),
    }


@router.get("/capabilities")
async def get_capabilities(current_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    """Expose non-secret runtime capabilities so the UI cannot drift from backend config."""
    return {
        "llm_provider": "Groq",
        "primary_model": settings.GROQ_MODEL,
        "fallback_models": settings.LLM_FALLBACK_ROUTING,
        "llm_configured": bool(settings.GROQ_API_KEY),
        "python_sandbox_configured": bool(settings.PYTHON_SANDBOX_URL),
        "max_task_budget_usd": settings.MAX_TASK_BUDGET_USD,
        "max_agent_budget_usd": settings.MAX_AGENT_BUDGET_USD,
        "max_steps_per_task": settings.MAX_STEPS_PER_TASK,
        "max_file_size_mb": settings.MAX_FILE_SIZE_MB,
        "supported_knowledge_files": ["pdf", "docx", "txt", "md", "csv", "json"],
        "rag_top_k": settings.RAG_TOP_K,
    }


@router.get("/costs")
async def get_cost_analytics(current_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    """Aggregated, internally consistent cost analytics for the authenticated user."""
    db = get_db()
    user_id = current_user["_id"]

    agent_pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {
            "_id": "$agent_type",
            "total_cost": {"$sum": "$cost_usd"},
            "total_tokens": {"$sum": "$tokens_total"},
            "runs": {"$sum": 1},
        }},
        {"$sort": {"total_cost": -1}},
    ]
    agent_stats_raw = await db.usage_cost.aggregate(agent_pipeline).to_list(length=None)

    agent_breakdown = [
        {
            "name": str(item["_id"]).replace("_", " ").title(),
            "value": round(float(item["total_cost"]), 6),
            "tokens": int(item["total_tokens"]),
            "runs": int(item["runs"]),
        }
        for item in agent_stats_raw
    ]

    total_spent = sum(float(item["total_cost"]) for item in agent_stats_raw)
    total_runs = sum(int(item["runs"]) for item in agent_stats_raw)
    total_tasks = await db.tasks.count_documents({"user_id": user_id})
    avg_per_task = total_spent / total_tasks if total_tasks else 0.0

    start_day = datetime.now(timezone.utc).date() - timedelta(days=29)
    start_dt = datetime.combine(start_day, datetime.min.time(), tzinfo=timezone.utc)
    daily_pipeline = [
        {"$match": {"user_id": user_id, "created_at": {"$gte": start_dt}}},
        {"$project": {
            "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at", "timezone": "UTC"}},
            "cost_usd": 1,
        }},
        {"$group": {"_id": "$date", "cost": {"$sum": "$cost_usd"}}},
        {"$sort": {"_id": 1}},
    ]
    daily_stats_raw = await db.usage_cost.aggregate(daily_pipeline).to_list(length=None)
    date_map = {item["_id"]: float(item["cost"]) for item in daily_stats_raw}
    daily_trend = [
        {
            "date": (start_day + timedelta(days=i)).isoformat(),
            "cost": round(date_map.get((start_day + timedelta(days=i)).isoformat(), 0.0), 6),
        }
        for i in range(30)
    ]

    recent_tasks_raw = await db.tasks.find(
        {"user_id": user_id},
        {"title": 1, "budget.spent_usd": 1, "status": 1, "created_at": 1},
    ).sort("created_at", -1).limit(10).to_list(length=10)

    tasks_comparison = [
        {
            "task": item.get("title", f"Task {str(item['_id'])[:6]}"),
            "cost": round(float(item.get("budget", {}).get("spent_usd", 0.0)), 6),
            "status": item.get("status", "unknown"),
        }
        for item in reversed(recent_tasks_raw)
    ]

    return {
        "success": True,
        "data": {
            "total_spent_usd": round(total_spent, 6),
            "average_cost_per_task_usd": round(avg_per_task, 6),
            "total_tasks": total_tasks,
            "total_runs": total_runs,
            "agent_type_count": len(agent_breakdown),
            "agent_breakdown": agent_breakdown,
            "daily_trend": daily_trend,
            "tasks_comparison": tasks_comparison,
        },
        "message": "Analytics fetched successfully",
    }
