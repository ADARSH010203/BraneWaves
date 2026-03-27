"""
ARC Platform — File Routes
POST /files/upload
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.deps import DbDep, UserDep
from app.models.file import FileUploadResponse
from app.security.rate_limiter import rate_limit_by_user
from app.services.file_service import upload_file

router = APIRouter()


@router.post(
    "/upload",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload(
    file: UploadFile = File(...),
    task_id: str | None = None,
    db: DbDep = None,
    user: UserDep = None,
):
    """Upload a file for RAG indexing."""
    await rate_limit_by_user(user["_id"])

    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filename required")

    file_bytes = await file.read()

    try:
        return await upload_file(
            db=db,
            user_id=user["_id"],
            filename=file.filename,
            content_type=file.content_type or "application/octet-stream",
            file_bytes=file_bytes,
            task_id=task_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
