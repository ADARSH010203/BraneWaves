"""
ARC Platform — Task & TaskStep Models
Core task lifecycle with dependency graph and budget controls.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────────────────
class TaskStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class StepType(str, Enum):
    RESEARCH = "research"
    DATA = "data"
    CODE = "code"
    CRITIQUE = "critique"
    REPORT = "report"
    REPAIR = "repair"


# ── Task ─────────────────────────────────────────────────────────────────────
class TaskCreate(BaseModel):
    """Request body for creating a new task."""
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1, max_length=10000)
    budget_usd: Optional[float] = Field(default=None, ge=0.01, le=100.0)
    max_steps: Optional[int] = Field(default=None, ge=1, le=200)
    tags: list[str] = Field(default_factory=list)


class TaskBudget(BaseModel):
    """Budget configuration embedded in task document."""
    max_usd: float = 5.0
    spent_usd: float = 0.0
    max_steps: int = 50
    steps_used: int = 0


class TaskDoc(BaseModel):
    """MongoDB task document shape."""
    id: str = Field(alias="_id")
    user_id: str
    title: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    budget: TaskBudget = Field(default_factory=TaskBudget)
    tags: list[str] = Field(default_factory=list)
    plan: Optional[dict[str, Any]] = None  # Agent-generated execution plan
    result_summary: Optional[str] = None
    report_id: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

    model_config = {"populate_by_name": True}


class TaskResponse(BaseModel):
    """Task response DTO."""
    id: str
    user_id: str
    title: str
    description: str
    status: TaskStatus
    budget: TaskBudget
    tags: list[str]
    plan: Optional[dict[str, Any]] = None
    result_summary: Optional[str] = None
    report_id: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


class TaskListResponse(BaseModel):
    """Paginated task list."""
    tasks: list[TaskResponse]
    total: int
    page: int
    page_size: int


# ── Task Step ────────────────────────────────────────────────────────────────
class TaskStepDoc(BaseModel):
    """MongoDB task_steps document."""
    id: str = Field(alias="_id")
    task_id: str
    order: int
    step_type: StepType
    title: str
    description: str
    status: StepStatus = StepStatus.PENDING
    depends_on: list[str] = Field(default_factory=list)  # Step IDs this depends on
    agent_type: str = ""
    input_data: Optional[dict[str, Any]] = None
    output_data: Optional[dict[str, Any]] = None
    confidence: Optional[float] = None  # 0.0–1.0
    retries: int = 0
    max_retries: int = 3
    cost_usd: float = 0.0
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True}


class TaskStepResponse(BaseModel):
    """Task step response DTO."""
    id: str
    task_id: str
    order: int
    step_type: StepType
    title: str
    description: str
    status: StepStatus
    depends_on: list[str]
    agent_type: str
    confidence: Optional[float] = None
    retries: int
    cost_usd: float
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
