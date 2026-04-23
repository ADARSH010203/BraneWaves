from typing import Any
from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
from app.database import get_db
from app.deps import get_current_user

router = APIRouter()

@router.get("/costs")
async def get_cost_analytics(current_user: dict = Depends(get_current_user)) -> dict[str, Any]:
    """
    Get aggregated cost analytics for the user's tasks.
    Groups by agent type and date for visualizations.
    """
    db = get_db()
    
    # 1. Total Cost & Tokens (lifetime)
    agent_pipeline = [
        {"$match": {"user_id": current_user["_id"]}},
        {"$group": {
            "_id": "$agent_type",
            "total_cost": {"$sum": "$cost_usd"},
            "total_tokens": {"$sum": "$tokens_total"},
            "runs": {"$sum": 1}
        }},
        {"$sort": {"total_cost": -1}}
    ]
    agent_stats_raw = await db.usage_cost.aggregate(agent_pipeline).to_list(None)
    
    agent_breakdown = [
        {
            "name": str(item["_id"]).capitalize(),
            "value": round(item["total_cost"], 4),
            "tokens": item["total_tokens"],
            "runs": item["runs"]
        }
        for item in agent_stats_raw
    ]

    total_spent = sum(item["value"] for item in agent_breakdown)
    
    # 2. Daily Cost Trend (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    daily_pipeline = [
        {"$match": {
            "user_id": current_user["_id"],
            "created_at": {"$gte": thirty_days_ago}
        }},
        {"$project": {
            "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "cost_usd": 1
        }},
        {"$group": {
            "_id": "$date",
            "cost": {"$sum": "$cost_usd"}
        }},
        {"$sort": {"_id": 1}}
    ]
    daily_stats_raw = await db.usage_cost.aggregate(daily_pipeline).to_list(None)
    
    # Fill in missing dates with 0 for a continuous chart
    daily_trend = []
    date_map = {item["_id"]: item["cost"] for item in daily_stats_raw}
    for i in range(30):
        d_str = (thirty_days_ago + timedelta(days=i)).strftime("%Y-%m-%d")
        daily_trend.append({
            "date": d_str,
            "cost": round(date_map.get(d_str, 0.0), 4)
        })

    # 3. Tasks cost comparison (top 10 recent tasks)
    tasks_pipeline = [
        {"$match": {"user_id": current_user["_id"]}},
        {"$sort": {"created_at": -1}},
        {"$limit": 10},
        {"$project": {
            "title": 1,
            "spent_usd": "$budget.spent_usd",
            "status": 1
        }}
    ]
    recent_tasks_raw = await db.tasks.aggregate(tasks_pipeline).to_list(None)
    
    tasks_comparison = [
        {
            "task": item.get("title", f"Task {str(item['_id'])[:6]}"),
            "cost": round(item.get("spent_usd", 0.0), 4),
            "status": item.get("status", "unknown")
        }
        for item in reversed(recent_tasks_raw)  # oldest of the top 10 first
    ]

    return {
        "success": True,
        "data": {
            "total_spent_usd": round(total_spent, 4),
            "agent_breakdown": agent_breakdown,
            "daily_trend": daily_trend,
            "tasks_comparison": tasks_comparison
        },
        "message": "Analytics fetched successfully"
    }
