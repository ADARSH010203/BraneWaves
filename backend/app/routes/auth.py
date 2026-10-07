"""ARC Platform — authentication routes.

Refresh tokens are kept in HttpOnly cookies.  Browser-visible responses expose
only short-lived access tokens.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from starlette.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth

from app.config import get_settings
from app.deps import DbDep
from app.models.user import UserCreate, UserLogin
from app.security.rate_limiter import rate_limit_by_ip
from app.services.auth_service import (
    login_user,
    logout_user,
    oauth_login_user,
    refresh_tokens,
    register_user,
)

router = APIRouter()
settings = get_settings()
REFRESH_COOKIE = "arc_refresh_token"

oauth = OAuth()
if settings.GOOGLE_CLIENT_ID:
    oauth.register(
        name="google",
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        client_kwargs={"scope": "openid email profile"},
    )
if settings.GITHUB_CLIENT_ID:
    oauth.register(
        name="github",
        api_base_url="https://api.github.com/",
        access_token_url="https://github.com/login/oauth/access_token",
        authorize_url="https://github.com/login/oauth/authorize",
        client_id=settings.GITHUB_CLIENT_ID,
        client_secret=settings.GITHUB_CLIENT_SECRET,
        client_kwargs={"scope": "user:email"},
    )


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE,
        path="/auth",
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
    )


def _public_auth_payload(user, tokens) -> dict:
    return {
        "user": user.model_dump(),
        "tokens": {
            "access_token": tokens.access_token,
            "token_type": tokens.token_type,
        },
    }


@router.post(
    "/register",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_by_ip)],
)
async def register(data: UserCreate, response: Response, db: DbDep):
    try:
        user, tokens = await register_user(db, data)
        _set_refresh_cookie(response, tokens.refresh_token)
        return _public_auth_payload(user, tokens)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post(
    "/login",
    response_model=dict,
    dependencies=[Depends(rate_limit_by_ip)],
)
async def login(data: UserLogin, response: Response, db: DbDep):
    try:
        user, tokens = await login_user(db, data)
        _set_refresh_cookie(response, tokens.refresh_token)
        return _public_auth_payload(user, tokens)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))


@router.post(
    "/refresh",
    response_model=dict,
    dependencies=[Depends(rate_limit_by_ip)],
)
async def refresh(request: Request, response: Response, db: DbDep):
    refresh_token = request.cookies.get(REFRESH_COOKIE)
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh session missing")
    try:
        tokens = await refresh_tokens(db, refresh_token)
        _set_refresh_cookie(response, tokens.refresh_token)
        return {"access_token": tokens.access_token, "token_type": tokens.token_type}
    except ValueError as exc:
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(rate_limit_by_ip)],
)
async def logout(request: Request, response: Response, db: DbDep):
    refresh_token = request.cookies.get(REFRESH_COOKIE)
    deleted = False
    if refresh_token:
        deleted = await logout_user(db, refresh_token)
    _clear_refresh_cookie(response)
    return {
        "success": True,
        "message": "Logged out successfully" if deleted else "Session was already inactive",
    }


@router.get("/{provider}/login")
async def provider_login(provider: str, request: Request):
    client = oauth.create_client(provider)
    if not client:
        raise HTTPException(status_code=404, detail="OAuth provider not supported or configured.")
    redirect_uri = request.url_for("provider_callback", provider=provider)
    return await client.authorize_redirect(request, redirect_uri)


@router.get("/{provider}/callback")
async def provider_callback(provider: str, request: Request, db: DbDep):
    client = oauth.create_client(provider)
    if not client:
        raise HTTPException(status_code=404, detail="OAuth provider not supported.")

    token = await client.authorize_access_token(request)

    if provider == "google":
        user_info = token.get("userinfo") or {}
        if user_info.get("email_verified") is not True:
            raise HTTPException(status_code=400, detail="Google account email is not verified.")
        email = user_info.get("email")
        name = user_info.get("name", "Google User")
    elif provider == "github":
        resp = await client.get("user", token=token)
        profile = resp.json()
        name = profile.get("name") or profile.get("login") or "GitHub User"
        resp_emails = await client.get("user/emails", token=token)
        emails = resp_emails.json()
        verified_emails = [e for e in emails if e.get("verified") and e.get("email")]
        primary_email = next((e for e in verified_emails if e.get("primary")), None)
        selected_email = primary_email or (verified_emails[0] if verified_emails else None)
        email = selected_email.get("email") if selected_email else None
    else:
        raise HTTPException(status_code=400, detail="Invalid provider")

    if not email:
        raise HTTPException(status_code=400, detail="Email not provided by OAuth.")

    try:
        _user, tokens = await oauth_login_user(db, email, name, provider)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=500, detail="OAuth login failed")

    frontend_url = settings.ALLOWED_ORIGINS[0].rstrip("/")
    response = RedirectResponse(
        f"{frontend_url}/login/callback#access_token={tokens.access_token}"
    )
    _set_refresh_cookie(response, tokens.refresh_token)
    return response
