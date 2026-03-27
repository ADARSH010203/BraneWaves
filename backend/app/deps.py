"""
ARC Platform — FastAPI Dependency Injection
Common dependencies used across routers.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import Settings, get_settings
from app.database import get_db, get_redis
from app.security.jwt_handler import decode_access_token


async def get_database() -> AsyncIOMotorDatabase:
    """Dependency: MongoDB database."""
    return get_db()


async def get_redis_client():
    """Dependency: Redis client."""
    return get_redis()


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    """Extract and validate JWT from Authorization header, return user doc."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    token = authorization.removeprefix("Bearer ")
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    user = await db.users.find_one({"_id": payload["sub"]})
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Dependency: require admin role."""
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


# Type aliases for cleaner signatures
DbDep = Annotated[AsyncIOMotorDatabase, Depends(get_database)]
UserDep = Annotated[dict, Depends(get_current_user)]
AdminDep = Annotated[dict, Depends(require_admin)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
