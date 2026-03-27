"""
ARC Platform — Report & Citation Models
Generated reports with citation traceability.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ReportFormat(str, Enum):
    MARKDOWN = "markdown"
    HTML = "html"
    JSON = "json"


class ReportDoc(BaseModel):
    """MongoDB reports document — final output of a task."""
    id: str = Field(alias="_id")
    task_id: str
    user_id: str
    title: str
    content: str  # Markdown report body
    format: ReportFormat = ReportFormat.MARKDOWN
    summary: Optional[str] = None
    sections: list[dict[str, Any]] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    word_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True}


class ReportResponse(BaseModel):
    """Report response DTO."""
    id: str
    task_id: str
    title: str
    content: str
    format: ReportFormat
    summary: Optional[str] = None
    citation_ids: list[str]
    confidence: float
    word_count: int
    created_at: datetime


# ── Citation ─────────────────────────────────────────────────────────────────
class CitationType(str, Enum):
    WEB = "web"
    PAPER = "paper"
    DATASET = "dataset"
    FILE = "file"
    CODE = "code"


class CitationDoc(BaseModel):
    """MongoDB citations document — source reference for report claims."""
    id: str = Field(alias="_id")
    report_id: str
    task_id: str
    citation_type: CitationType
    title: str
    url: Optional[str] = None
    authors: list[str] = Field(default_factory=list)
    excerpt: Optional[str] = None  # Relevant passage
    relevance_score: float = 0.0  # 0.0–1.0
    verified: bool = False
    verification_note: Optional[str] = None
    source_chunk_id: Optional[str] = None  # RAG chunk reference
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True}


class CitationResponse(BaseModel):
    """Citation response DTO."""
    id: str
    report_id: str
    citation_type: CitationType
    title: str
    url: Optional[str] = None
    authors: list[str]
    excerpt: Optional[str] = None
    relevance_score: float
    verified: bool
    verification_note: Optional[str] = None
