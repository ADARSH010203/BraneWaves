"""
ARC Platform — Memory Graph Models
Nodes = research topics/entities, Edges = co-occurrence relationships
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field


class MemoryNodeDoc(BaseModel):
    id: str = Field(alias="_id")
    user_id: str
    label: str
    node_type: str = "topic"  # topic, entity, concept, technology
    description: str = ""
    embedding: list[float] = []
    task_ids: list[str] = []
    occurrence_count: int = 1
    last_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = {}

    class Config:
        populate_by_name = True


class MemoryEdgeDoc(BaseModel):
    id: str = Field(alias="_id")
    user_id: str
    from_node_id: str
    to_node_id: str
    weight: float = 1.0
    co_occurrence_count: int = 1
    task_ids: list[str] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        populate_by_name = True
