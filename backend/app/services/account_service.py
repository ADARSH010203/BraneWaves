"""Account profile and deletion services."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.user import UserResponse


def _to_user_response(user: dict) -> UserResponse:
    return UserResponse(
        id=str(user["_id"]),
        email=user["email"],
        name=user["name"],
        provider=user.get("provider", "local"),
        role=user.get("role", "user"),
        plan=user.get("plan", "free"),
        usage_quota_usd=float(user.get("usage_quota_usd", 10.0)),
        created_at=user["created_at"],
        is_active=user.get("is_active", True),
    )


async def update_profile(db: AsyncIOMotorDatabase, user_id: str, name: str) -> UserResponse:
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Display name cannot be empty")
    now = datetime.now(timezone.utc)
    await db.users.update_one(
        {"_id": user_id, "is_active": {"$ne": False}},
        {"$set": {"name": clean_name, "updated_at": now}},
    )
    user = await db.users.find_one({"_id": user_id})
    if not user:
        raise ValueError("User not found")
    return _to_user_response(user)


async def delete_account(db: AsyncIOMotorDatabase, user_id: str) -> None:
    """Permanently delete user-owned application data and uploaded files."""
    await db.users.update_one(
        {"_id": user_id},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}},
    )

    files = await db.files.find({"user_id": user_id}, {"storage_path": 1}).to_list(length=None)
    for file_doc in files:
        storage_path = file_doc.get("storage_path")
        if storage_path:
            try:
                path = Path(storage_path)
                if path.exists() and path.is_file():
                    path.unlink()
            except OSError:
                pass

    collections = [
        "sessions", "task_steps", "agent_runs", "agent_logs", "files", "chunks",
        "citations", "reports", "report_chunks", "report_chats", "usage_cost",
        "memory_nodes", "memory_edges", "tasks",
    ]
    for name in collections:
        await db[name].delete_many({"user_id": user_id})

    await db.users.delete_one({"_id": user_id})
