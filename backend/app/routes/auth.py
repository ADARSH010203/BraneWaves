"""
ARC Platform — Auth Routes
POST /auth/register, /auth/login, /auth/refresh
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from starlette.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from app.config import get_settings

from app.deps import DbDep
from app.models.user import RefreshRequest, TokenResponse, UserCreate, UserLogin, UserResponse
from app.security.rate_limiter import rate_limit_by_ip
from app.services.auth_service import login_user, refresh_tokens, register_user, oauth_login_user

router = APIRouter()
settings = get_settings()

oauth = OAuth()
if settings.GOOGLE_CLIENT_ID:
    oauth.register(
        name='google',
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        client_kwargs={'scope': 'openid email profile'},
    )
if settings.GITHUB_CLIENT_ID:
    oauth.register(
        name='github',
        api_base_url='https://api.github.com/',
        access_token_url='https://github.com/login/oauth/access_token',
        authorize_url='https://github.com/login/oauth/authorize',
        client_id=settings.GITHUB_CLIENT_ID,
        client_secret=settings.GITHUB_CLIENT_SECRET,
        client_kwargs={'scope': 'user:email'},
    )


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


@router.get("/{provider}/login")
async def provider_login(provider: str, request: Request):
    """Redirects to the specified provider."""
    client = oauth.create_client(provider)
    if not client:
        raise HTTPException(status_code=404, detail="OAuth provider not supported or configured.")
    redirect_uri = request.url_for("provider_callback", provider=provider)
    return await client.authorize_redirect(request, redirect_uri)


@router.get("/{provider}/callback")
async def provider_callback(provider: str, request: Request, db: DbDep):
    """Handles OAuth callback and logs in the user."""
    client = oauth.create_client(provider)
    if not client:
        raise HTTPException(status_code=404, detail="OAuth provider not supported.")
    
    token = await client.authorize_access_token(request)
    
    if provider == "google":
        user_info = token.get("userinfo")
        email = user_info.get("email")
        name = user_info.get("name", "Google User")
    elif provider == "github":
        resp = await client.get('user', token=token)
        profile = resp.json()
        name = profile.get("name") or profile.get("login") or "GitHub User"
        
        resp_emails = await client.get('user/emails', token=token)
        emails = resp_emails.json()
        primary_email = next((e for e in emails if e.get("primary")), None)
        email = primary_email.get("email") if primary_email else (emails[0].get("email") if emails else None)
    else:
        raise HTTPException(status_code=400, detail="Invalid provider")

    if not email:
        raise HTTPException(status_code=400, detail="Email not provided by OAuth.")

    try:
        user, tokens = await oauth_login_user(db, email, name, provider)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    frontend_url = settings.ALLOWED_ORIGINS[0]
    return RedirectResponse(f"{frontend_url}/login/callback#access_token={tokens.access_token}&refresh_token={tokens.refresh_token}")
