"""
ARC Platform — Usage Cost Model
Per-task and per-user cost tracking with budget enforcement.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class UsageCostDoc(BaseModel):
    """MongoDB usage_cost document — cost entry per agent run."""
    id: str = Field(alias="_id")
    user_id: str
    task_id: str
    step_id: Optional[str] = None
    run_id: Optional[str] = None
    agent_type: str = ""
    model_used: str = ""
    tokens_prompt: int = 0
    tokens_completion: int = 0
    tokens_total: int = 0
    cost_usd: float = 0.0
    description: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True}


class CostSummary(BaseModel):
    """Aggregated cost summary for a task or user."""
    total_cost_usd: float = 0.0
    total_tokens: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    num_runs: int = 0
    budget_remaining_usd: Optional[float] = None


class UserCostDashboard(BaseModel):
    """Cost dashboard data for a user."""
    total_spent_usd: float = 0.0
    total_tokens: int = 0
    tasks_count: int = 0
    quota_usd: float = 10.0
    quota_remaining_usd: float = 10.0
    recent_costs: list[UsageCostDoc] = Field(default_factory=list)
