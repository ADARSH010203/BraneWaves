"""
ARC Platform — Agent Run & Agent Log Models
Tracks individual agent executions and their detailed logs.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class AgentType(str, Enum):
    PLANNER = "planner"
    RESEARCH = "research"
    DATA = "data"
    CODE = "code"
    CRITIC = "critic"
    REPORT = "report"
    REPAIR = "repair"


class AgentRunStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


# ── Agent Run ────────────────────────────────────────────────────────────────
class AgentRunDoc(BaseModel):
    """MongoDB agent_runs document — one per agent invocation."""
    id: str = Field(alias="_id")
    task_id: str
    step_id: str
    agent_type: AgentType
    status: AgentRunStatus = AgentRunStatus.RUNNING
    input_data: Optional[dict[str, Any]] = None
    output_data: Optional[dict[str, Any]] = None
    tokens_prompt: int = 0
    tokens_completion: int = 0
    tokens_total: int = 0
    cost_usd: float = 0.0
    confidence: Optional[float] = None
    model_used: str = ""
    tools_called: list[str] = Field(default_factory=list)
    retries: int = 0
    error: Optional[str] = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None

    model_config = {"populate_by_name": True}


class AgentRunResponse(BaseModel):
    """Agent run response DTO."""
    id: str
    task_id: str
    step_id: str
    agent_type: AgentType
    status: AgentRunStatus
    tokens_total: int
    cost_usd: float
    confidence: Optional[float] = None
    model_used: str
    tools_called: list[str]
    retries: int
    error: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None


# ── Agent Log ────────────────────────────────────────────────────────────────
class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class AgentLogDoc(BaseModel):
    """MongoDB agent_logs document — granular trace entries."""
    id: str = Field(alias="_id")
    run_id: str
    task_id: str
    agent_type: AgentType
    level: LogLevel = LogLevel.INFO
    event: str  # e.g. "tool_call", "llm_response", "retry", "error"
    message: str
    data: Optional[dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True}
