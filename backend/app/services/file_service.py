"""
ARC Platform — File Service
Handles file uploads, validation, and RAG indexing.
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import get_settings
from app.models.file import FileDoc, FileResponse, FileType, FileUploadResponse
from app.rag.chunker import chunk_text
from app.rag.embeddings import store_chunks_with_embeddings
from app.rag.ingestion import extract_document_segments

logger = logging.getLogger("arc.services.file")
settings = get_settings()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf", "txt", "md", "csv", "json", "docx"}


async def read_upload_file_capped(file, max_bytes: int | None = None) -> bytes:
    """Read upload file in chunks, aborting early if file exceeds size limit."""
    max_limit = max_bytes or (settings.MAX_FILE_SIZE_MB * 1024 * 1024)
    chunk_size = 64 * 1024
    total = 0
    chunks = []
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total += len(chunk)
        if total > max_limit:
            max_mb = max_limit // (1024 * 1024)
            raise ValueError(f"File size exceeds {max_mb} MB limit")
        chunks.append(chunk)
    return b"".join(chunks)


def _get_file_type(filename: str) -> FileType:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    mapping = {
        "pdf": FileType.PDF,
        "txt": FileType.TXT,
        "md": FileType.MD,
        "csv": FileType.CSV,
        "json": FileType.JSON,
        "docx": FileType.DOCX,
    }
    return mapping.get(ext, FileType.OTHER)


async def upload_file(
    db: AsyncIOMotorDatabase,
    user_id: str,
    filename: str,
    content_type: str,
    file_bytes: bytes,
    task_id: str | None = None,
) -> FileUploadResponse:
    """Upload, validate, store, and index a file."""
    # Validate extension
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"File type '.{ext}' not allowed. Allowed: {ALLOWED_EXTENSIONS}")

    # Validate size
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise ValueError(f"File size exceeds {settings.MAX_FILE_SIZE_MB} MB limit")

    file_id = str(uuid.uuid4())
    stored_name = f"{file_id}.{ext}"
    storage_path = str(UPLOAD_DIR / stored_name)

    # Write to disk
    with open(storage_path, "wb") as f:
        f.write(file_bytes)

    # Extract text with source provenance and index it. PDF pages retain
    # page_number metadata so local citations can point back to the source page.
    segments = await extract_document_segments(file_bytes, content_type, filename)
    chunks = []
    for segment in segments:
        segment_meta = {
            "file_id": file_id,
            "filename": filename,
            "original_name": filename,
            "page_number": segment.get("page_number"),
            "segment_index": segment.get("segment_index"),
        }
        chunks.extend(chunk_text(segment.get("text", ""), metadata=segment_meta))

    # Re-number chunks across the full document rather than per page/segment.
    for index, chunk in enumerate(chunks):
        chunk["index"] = index
        chunk.setdefault("metadata", {})["chunk_index"] = index
        chunk["metadata"]["total_chunks"] = len(chunks)

    chunk_ids = []
    if chunks:
        try:
            chunk_ids = await store_chunks_with_embeddings(chunks, user_id, file_id)
        except Exception as e:
            logger.error("Failed to index file %s: %s", file_id, e)

    # Save metadata
    file_doc = {
        "_id": file_id,
        "user_id": user_id,
        "filename": stored_name,
        "original_name": filename,
        "content_type": content_type,
        "file_type": _get_file_type(filename).value,
        "size_bytes": len(file_bytes),
        "storage_path": storage_path,
        "chunk_ids": chunk_ids,
        "is_indexed": len(chunk_ids) > 0,
        "task_id": task_id,
        "created_at": datetime.now(timezone.utc),
    }
    await db.files.insert_one(file_doc)

    file_response = FileResponse(
        id=file_id,
        filename=stored_name,
        original_name=filename,
        content_type=content_type,
        file_type=_get_file_type(filename),
        size_bytes=len(file_bytes),
        is_indexed=len(chunk_ids) > 0,
        task_id=task_id,
        created_at=file_doc["created_at"],
    )
    return FileUploadResponse(file=file_response)
