"""
ARC Platform — Prompt Version Registry
Stores and retrieves versioned system prompts for each agent type.
Enables A/B testing, rollback, and compliance tracking.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.database import get_db

logger = logging.getLogger("arc.prompts.versioning")


async def save_prompt_version(
    agent_type: str,
    system_prompt: str,
    description: str = "",
    author: str = "system",
    is_active: bool = True,
) -> str:
    """
    Save a new version of a system prompt for an agent type.
    Deactivates previous active version if this one is active.
    Returns the version ID.
    """
    db = get_db()

    # Deactivate previous active version
    if is_active:
        await db.prompt_versions.update_many(
            {"agent_type": agent_type, "is_active": True},
            {"$set": {"is_active": False}},
        )

    # Get next version number
    last = await db.prompt_versions.find_one(
        {"agent_type": agent_type},
        sort=[("version", -1)],
    )
    version = (last["version"] + 1) if last else 1

    doc = {
        "agent_type": agent_type,
        "version": version,
        "system_prompt": system_prompt,
        "description": description,
        "author": author,
        "is_active": is_active,
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.prompt_versions.insert_one(doc)
    logger.info("Saved prompt v%d for %s (active=%s)", version, agent_type, is_active)
    return str(result.inserted_id)


async def get_active_prompt(agent_type: str) -> Optional[str]:
    """Get the currently active system prompt for an agent type."""
    db = get_db()
    doc = await db.prompt_versions.find_one(
        {"agent_type": agent_type, "is_active": True},
    )
    return doc["system_prompt"] if doc else None


async def get_prompt_history(agent_type: str) -> list[dict[str, Any]]:
    """Get all prompt versions for an agent type, newest first."""
    db = get_db()
    cursor = db.prompt_versions.find(
        {"agent_type": agent_type},
        sort=[("version", -1)],
    )
    return await cursor.to_list(length=100)


async def rollback_prompt(agent_type: str, version: int) -> bool:
    """Activate a specific version and deactivate others."""
    db = get_db()
    # Deactivate all
    await db.prompt_versions.update_many(
        {"agent_type": agent_type},
        {"$set": {"is_active": False}},
    )
    # Activate target
    result = await db.prompt_versions.update_one(
        {"agent_type": agent_type, "version": version},
        {"$set": {"is_active": True}},
    )
    if result.modified_count > 0:
        logger.info("Rolled back %s prompt to v%d", agent_type, version)
        return True
    return False
