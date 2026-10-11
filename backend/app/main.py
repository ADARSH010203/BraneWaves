"""
ARC Platform — FastAPI Application Entry Point
Lifespan-managed connections · CORS · Middleware · Routers
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import connect_db, connect_redis, disconnect_db, disconnect_redis, get_db, get_redis
from app.middleware import RequestSizeLimitMiddleware, SecurityHeadersMiddleware, TraceIDMiddleware
from app.observability.logger import setup_logging
from app.routes import auth, files, tasks, ws, analytics, templates, knowledge_base, memory
from app.tools.registry import register_all_tools

settings = get_settings()

# ── Logging ──────────────────────────────────────────────────────────────────
setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger("arc.main")


# ── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("🚀 Starting %s v%s [%s]", settings.APP_NAME, settings.APP_VERSION, settings.ENVIRONMENT)

    # ── GROQ_API_KEY guard (only LLM provider) ────────────────────────
    if not settings.GROQ_API_KEY:
        message = (
            "GROQ_API_KEY is missing or empty. "
            "Set GROQ_API_KEY before running agent tasks."
        )
        if settings.ENVIRONMENT == "production":
            raise RuntimeError(message)
        logger.warning(message)

    if settings.ENVIRONMENT == "production":
        frontend_origin = settings.FRONTEND_URL.rstrip("/")
        allowed_origins = {origin.rstrip("/") for origin in settings.ALLOWED_ORIGINS}
        if "*" in allowed_origins:
            raise RuntimeError("Wildcard CORS origins are forbidden in production when credentials are enabled.")
        if frontend_origin not in allowed_origins:
            raise RuntimeError("FRONTEND_URL must be present in ALLOWED_ORIGINS in production.")
        if settings.REFRESH_COOKIE_SAMESITE == "none" and not frontend_origin.startswith("https://"):
            raise RuntimeError("SameSite=None refresh cookies require an HTTPS FRONTEND_URL.")

    if len(settings.JWT_SECRET_KEY) < 32:
        raise RuntimeError("JWT_SECRET_KEY must be at least 32 characters.")
    if settings.JWT_SECRET_KEY.startswith("CHANGE-ME"):
        raise RuntimeError("Refusing to start with the example JWT secret.")

    await connect_db()
    await connect_redis()
    if settings.ENVIRONMENT == "production" and get_redis() is None:
        await disconnect_db()
        raise RuntimeError("Redis is required in production for task queueing, budgets, and streaming.")
    register_all_tools()
    logger.info("✅ Tools registered")
    # Seed task templates if collection is empty
    from app.routes.templates import seed_templates
    await seed_templates()
    logger.info("✅ Templates checked/seeded")
    yield
    await disconnect_redis()
    await disconnect_db()
    logger.info("👋 Shutdown complete")


# ── Application ──────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# ── Middleware (order matters — outermost first) ─────────────────────────────
from starlette.middleware.sessions import SessionMiddleware
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.JWT_SECRET_KEY,
    https_only=settings.ENVIRONMENT == "production",
    same_site="lax",
)
app.add_middleware(TraceIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestSizeLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])
app.include_router(files.router, prefix="/files", tags=["Files"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
app.include_router(templates.router, prefix="/templates", tags=["Templates"])
app.include_router(knowledge_base.router, prefix="/knowledge-base", tags=["Knowledge Base"])
app.include_router(memory.router, prefix="/memory", tags=["Memory Graph"])
app.include_router(ws.router, tags=["WebSocket"])


# ── Health checks ─────────────────────────────────────────────────────────────
async def _readiness_payload() -> tuple[dict, bool]:
    checks = {"api": "ok"}

    try:
        db = get_db()
        await db.command("ping")
        checks["mongodb"] = "ok"
    except Exception:
        checks["mongodb"] = "error"

    try:
        redis = get_redis()
        if redis is None:
            raise RuntimeError("Redis unavailable")
        await redis.ping()
        checks["redis"] = "ok"

        if settings.ENVIRONMENT == "production":
            heartbeat = await redis.get("arc:worker:heartbeat")
            checks["worker"] = "ok" if heartbeat else "error"
    except Exception:
        checks["redis"] = "error"
        if settings.ENVIRONMENT == "production":
            checks["worker"] = "error"

    ready = all(value == "ok" for value in checks.values())
    payload = {
        "status": "ok" if ready else "degraded",
        "version": settings.APP_VERSION,
        "checks": checks,
    }
    return payload, ready


@app.get("/health/live", tags=["Health"])
async def health_live():
    """Process liveness: independent of external dependency availability."""
    return {"status": "ok", "version": settings.APP_VERSION}


@app.get("/health/ready", tags=["Health"])
async def health_ready():
    """Readiness for traffic. Returns 503 when required dependencies are unavailable."""
    payload, ready = await _readiness_payload()
    return JSONResponse(status_code=200 if ready else 503, content=payload)


@app.get("/health", tags=["Health"])
async def health():
    """Backward-compatible readiness endpoint."""
    return await health_ready()
