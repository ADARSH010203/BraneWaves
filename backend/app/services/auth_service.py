"""
ARC Platform — Auth Service
Handles user registration, login, and token refresh with MongoDB persistence.
"""
from __future__ import annotations

import uuid
import logging
from datetime import datetime, timedelta, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.user import UserCreate, UserLogin, UserResponse, TokenResponse
from app.security.jwt_handler import create_access_token, create_refresh_token, decode_refresh_token
from app.security.password import hash_password, verify_password

logger = logging.getLogger("arc.services.auth")


async def register_user(db: AsyncIOMotorDatabase, data: UserCreate) -> tuple[UserResponse, TokenResponse]:
    """Register a new user and return tokens."""
    # Check existing
    existing = await db.users.find_one({"email": data.email})
    if existing:
        raise ValueError("Email already registered")

    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    user_doc = {
        "_id": user_id,
        "email": data.email,
        "name": data.name,
        "hashed_password": hash_password(data.password),
        "role": "user",
        "plan": "free",
        "usage_quota_usd": 10.0,
        "created_at": now,
        "updated_at": now,
        "is_active": True,
    }
    await db.users.insert_one(user_doc)
    logger.info("User registered: %s (%s)", data.email, user_id)

    # Create tokens
    access_token = create_access_token(user_id, "user")
    refresh_token = create_refresh_token(user_id)

    # Store session
    session_doc = {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "refresh_token": refresh_token,
        "created_at": now,
        "expires_at": now + timedelta(days=7),
    }
    await db.sessions.insert_one(session_doc)

    user_response = UserResponse(
        id=user_id,
        email=data.email,
        name=data.name,
        role="user",
        plan="free",
        usage_quota_usd=10.0,
        created_at=now,
        is_active=True,
    )
    token_response = TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )
    return user_response, token_response


async def login_user(db: AsyncIOMotorDatabase, data: UserLogin) -> tuple[UserResponse, TokenResponse]:
    """Authenticate user and return tokens."""
    user = await db.users.find_one({"email": data.email})
    if not user:
        raise ValueError("Invalid email or password")

    if not verify_password(data.password, user["hashed_password"]):
        raise ValueError("Invalid email or password")

    if not user.get("is_active", True):
        raise ValueError("Account is deactivated")

    user_id = user["_id"]
    now = datetime.now(timezone.utc)

    access_token = create_access_token(user_id, user.get("role", "user"))
    refresh_token = create_refresh_token(user_id)

    session_doc = {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "refresh_token": refresh_token,
        "created_at": now,
        "expires_at": now + timedelta(days=7),
    }
    await db.sessions.insert_one(session_doc)

    user_response = UserResponse(
        id=user_id,
        email=user["email"],
        name=user["name"],
        role=user.get("role", "user"),
        plan=user.get("plan", "free"),
        usage_quota_usd=user.get("usage_quota_usd", 10.0),
        created_at=user["created_at"],
        is_active=user.get("is_active", True),
    )
    token_response = TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )
    return user_response, token_response


async def refresh_tokens(db: AsyncIOMotorDatabase, refresh_token_str: str) -> TokenResponse:
    """Refresh access token using a valid refresh token."""
    payload = decode_refresh_token(refresh_token_str)
    if not payload:
        raise ValueError("Invalid or expired refresh token")

    user_id = payload["sub"]

    # Verify session exists
    session = await db.sessions.find_one({"refresh_token": refresh_token_str, "user_id": user_id})
    if not session:
        raise ValueError("Session not found")

    # Delete old session
    await db.sessions.delete_one({"_id": session["_id"]})

    # Get user
    user = await db.users.find_one({"_id": user_id})
    if not user:
        raise ValueError("User not found")

    # Create new tokens
    now = datetime.now(timezone.utc)
    new_access = create_access_token(user_id, user.get("role", "user"))
    new_refresh = create_refresh_token(user_id)

    session_doc = {
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "refresh_token": new_refresh,
        "created_at": now,
        "expires_at": now + timedelta(days=7),
    }
    await db.sessions.insert_one(session_doc)

    return TokenResponse(access_token=new_access, refresh_token=new_refresh)
