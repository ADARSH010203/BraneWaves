"""
ARC Platform — User & Session Models
Users collection + sessions collection for JWT refresh tokens.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ── Enums ────────────────────────────────────────────────────────────────────
class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class PlanTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


# ── User ─────────────────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    """Request body for user registration."""
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=100)


class UserLogin(BaseModel):
    """Request body for login."""
    email: EmailStr
    password: str


class UserDoc(BaseModel):
    """MongoDB user document shape."""
    id: str = Field(alias="_id")
    email: str
    name: str
    hashed_password: Optional[str] = None
    provider: str = "local"
    role: UserRole = UserRole.USER
    plan: PlanTier = PlanTier.FREE
    usage_quota_usd: float = 10.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True

    model_config = {"populate_by_name": True}


class UserResponse(BaseModel):
    """Safe user response (no password)."""
    id: str
    email: str
    name: str
    provider: str
    role: UserRole
    plan: PlanTier
    usage_quota_usd: float
    created_at: datetime
    is_active: bool


class TokenResponse(BaseModel):
    """JWT token pair response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Refresh token request body."""
    refresh_token: str


# ── Session ──────────────────────────────────────────────────────────────────
class SessionDoc(BaseModel):
    """MongoDB session document for refresh tokens."""
    id: str = Field(alias="_id")
    user_id: str
    refresh_token: str
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime

    model_config = {"populate_by_name": True}
