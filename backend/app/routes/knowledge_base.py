import uuid
from typing import Any
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException

from app.database import get_db
from app.deps import get_current_user
from app.models.file import FileResponse
from app.services.file_service import upload_file

router = APIRouter()

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Uploads a document to the persistent knowledge base for RAG retrieval."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")
        
    db = get_db()
    user_id = current_user["_id"]
    
    count = await db.files.count_documents({"user_id": user_id, "task_id": "KNOWLEDGE_BASE"})
    if count >= 20:
        raise HTTPException(status_code=400, detail="Knowledge base limit reached (20 docs). Delete some to upload more.")

    file_bytes = await file.read()
    try:
        res = await upload_file(
            db=db,
            user_id=user_id,
            filename=file.filename,
            content_type=file.content_type or "application/octet-stream",
            file_bytes=file_bytes,
            task_id="KNOWLEDGE_BASE"
        )
        return res.file
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/")
async def list_documents(current_user: dict = Depends(get_current_user)):
    """List all documents in the user's persistent knowledge base."""
    db = get_db()
    user_id = current_user["_id"]
    cursor = db.files.find({"user_id": user_id, "task_id": "KNOWLEDGE_BASE"}).sort("created_at", -1)
    docs = await cursor.to_list(None)
    
    return [
        FileResponse(
            id=str(d["_id"]),
            filename=d["filename"],
            original_name=d["original_name"],
            content_type=d["content_type"],
            file_type=d["file_type"],
            size_bytes=d["size_bytes"],
            is_indexed=d.get("is_indexed", False),
            task_id=d.get("task_id"),
            created_at=d["created_at"]
        ) for d in docs
    ]


@router.delete("/{doc_id}")
async def delete_document(doc_id: str, current_user: dict = Depends(get_current_user)):
    """Deletes a document from the knowledge base and its chunks."""
    db = get_db()
    user_id = current_user["_id"]
    result = await db.files.delete_one({"_id": doc_id, "user_id": user_id, "task_id": "KNOWLEDGE_BASE"})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")
        
    await db.chunks.delete_many({"file_id": doc_id, "user_id": user_id})
    return {"success": True, "message": "Document deleted"}
