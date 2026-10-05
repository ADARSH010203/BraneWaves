"""
ARC Platform — Database connections
Motor (async MongoDB) + Redis (aioredis) setup with index creation.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import redis.asyncio as aioredis
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import get_settings

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger("arc.database")

# ── Module-level singletons ──────────────────────────────────────────────────
_mongo_client: AsyncIOMotorClient | None = None
_mongo_db: AsyncIOMotorDatabase | None = None
_redis_client: "Redis | None" = None


# ── Accessors ────────────────────────────────────────────────────────────────
def get_db() -> AsyncIOMotorDatabase:
    """Return the Motor database instance."""
    assert _mongo_db is not None, "Database not initialised — call connect_db() first"
    return _mongo_db


def get_redis() -> "Redis":
    """Return the Redis client instance."""
    assert _redis_client is not None, "Redis not initialised — call connect_redis() first"
    return _redis_client


# ── Connection lifecycle ─────────────────────────────────────────────────────
async def connect_db() -> None:
    """Open Motor connection and create indexes."""
    global _mongo_client, _mongo_db
    settings = get_settings()
    _mongo_client = AsyncIOMotorClient(str(settings.MONGO_URI))
    _mongo_db = _mongo_client[settings.MONGO_DB_NAME]
    logger.info("MongoDB connected → %s", settings.MONGO_DB_NAME)
    await _ensure_indexes(_mongo_db)


async def disconnect_db() -> None:
    """Close Motor connection."""
    global _mongo_client, _mongo_db
    if _mongo_client:
        _mongo_client.close()
        _mongo_client = None
        _mongo_db = None
        logger.info("MongoDB disconnected")


async def connect_redis() -> None:
    """Open Redis connection."""
    global _redis_client
    settings = get_settings()
    _redis_client = aioredis.from_url(
        str(settings.REDIS_URL),
        decode_responses=True,
    )
    logger.info("Redis connected → %s", settings.REDIS_URL)


async def disconnect_redis() -> None:
    """Close Redis connection."""
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("Redis disconnected")


# ── Index definitions ────────────────────────────────────────────────────────
async def _ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    """Create MongoDB indexes for all collections."""
    # Users
    await db.users.create_index("email", unique=True)
    await db.users.create_index("created_at")

    # Sessions
    await db.sessions.create_index("user_id")
    await db.sessions.create_index("refresh_token", unique=True)
    await db.sessions.create_index("expires_at", expireAfterSeconds=0)

    # Tasks
    await db.tasks.create_index("user_id")
    await db.tasks.create_index([("user_id", 1), ("status", 1)])
    await db.tasks.create_index("created_at")

    # Task Steps
    await db.task_steps.create_index("task_id")
    await db.task_steps.create_index([("task_id", 1), ("order", 1)])

    # Agent Runs
    await db.agent_runs.create_index("task_id")
    await db.agent_runs.create_index([("task_id", 1), ("step_id", 1)])

    # Agent Logs
    await db.agent_logs.create_index("run_id")
    await db.agent_logs.create_index("timestamp")

    # Files
    await db.files.create_index("user_id")
    await db.files.create_index([("user_id", 1), ("filename", 1)])

    # Chunks (RAG)
    await db.chunks.create_index([("user_id", 1), ("file_id", 1)])
    await db.chunks.create_index("user_id")

    # Citations
    await db.citations.create_index("report_id")
    await db.citations.create_index("task_id")

    # Reports
    await db.reports.create_index("task_id", unique=True)

    # Usage Cost
    await db.usage_cost.create_index("user_id")
    await db.usage_cost.create_index("task_id")

    # Prompt Versions
    await db.prompt_versions.create_index([("agent_type", 1), ("version", -1)])

    # Memory Graph
    await db.memory_nodes.create_index([("user_id", 1), ("label", 1)])
    await db.memory_nodes.create_index("user_id")
    await db.memory_nodes.create_index([("user_id", 1), ("occurrence_count", -1)])
    await db.memory_edges.create_index([("user_id", 1), ("from_node_id", 1)])
    await db.memory_edges.create_index([("user_id", 1), ("to_node_id", 1)])

    logger.info("MongoDB indexes ensured")
