"""
ARC Platform — FastAPI Application Entry Point
Lifespan-managed connections · CORS · Middleware · Routers
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import connect_db, connect_redis, disconnect_db, disconnect_redis, get_db, get_redis
from app.middleware import RequestSizeLimitMiddleware, TraceIDMiddleware
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
    await connect_db()
    await connect_redis()
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
app.add_middleware(SessionMiddleware, secret_key=settings.JWT_SECRET_KEY)
app.add_middleware(TraceIDMiddleware)
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


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health():
    checks = {"api": "ok"}
    try:
        db = get_db()
        await db.command("ping")
        checks["mongodb"] = "ok"
    except Exception:
        checks["mongodb"] = "error"
    try:
        redis = get_redis()
        await redis.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"
    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": overall, "version": settings.APP_VERSION, "checks": checks}
