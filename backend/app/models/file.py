"""
ARC Platform — File Model
Uploaded file metadata with RAG chunk references.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class FileType(str, Enum):
    PDF = "pdf"
    TXT = "txt"
    MD = "md"
    CSV = "csv"
    JSON = "json"
    DOCX = "docx"
    OTHER = "other"


class FileDoc(BaseModel):
    """MongoDB files document."""
    id: str = Field(alias="_id")
    user_id: str
    filename: str
    original_name: str
    content_type: str
    file_type: FileType = FileType.OTHER
    size_bytes: int
    storage_path: str
    chunk_ids: list[str] = Field(default_factory=list)  # RAG chunk references
    is_indexed: bool = False
    task_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True}


class FileResponse(BaseModel):
    """File metadata response DTO."""
    id: str
    filename: str
    original_name: str
    content_type: str
    file_type: FileType
    size_bytes: int
    is_indexed: bool
    task_id: Optional[str] = None
    created_at: datetime


class FileUploadResponse(BaseModel):
    """Response after successful file upload."""
    file: FileResponse
    message: str = "File uploaded successfully"
