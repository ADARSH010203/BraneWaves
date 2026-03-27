"""
ARC Platform — Auth Routes
POST /auth/register, /auth/login, /auth/refresh
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.deps import DbDep
from app.models.user import RefreshRequest, TokenResponse, UserCreate, UserLogin, UserResponse
from app.security.rate_limiter import rate_limit_by_ip
from app.services.auth_service import login_user, refresh_tokens, register_user

router = APIRouter()


@router.post(
    "/register",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_by_ip)],
)
async def register(data: UserCreate, db: DbDep):
    """Register a new user account."""
    try:
        user, tokens = await register_user(db, data)
        return {"user": user.model_dump(), "tokens": tokens.model_dump()}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post(
    "/login",
    response_model=dict,
    dependencies=[Depends(rate_limit_by_ip)],
)
async def login(data: UserLogin, db: DbDep):
    """Authenticate user and return tokens."""
    try:
        user, tokens = await login_user(db, data)
        return {"user": user.model_dump(), "tokens": tokens.model_dump()}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post(
    "/refresh",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit_by_ip)],
)
async def refresh(data: RefreshRequest, db: DbDep):
    """Refresh access token using refresh token."""
    try:
        return await refresh_tokens(db, data.refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
