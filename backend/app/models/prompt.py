"""
ARC Platform — Prompt Version Model
Versioned system prompts for each agent type.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class PromptVersionDoc(BaseModel):
    """MongoDB prompt_versions document — versioned prompts per agent."""
    id: str = Field(alias="_id")
    agent_type: str  # matches AgentType enum values
    version: int = 1
    system_prompt: str
    description: Optional[str] = None
    is_active: bool = True
    created_by: Optional[str] = None  # user_id of admin who created it
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True}


class PromptVersionResponse(BaseModel):
    """Prompt version response DTO."""
    id: str
    agent_type: str
    version: int
    system_prompt: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
