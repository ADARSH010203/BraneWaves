"""
ARC Platform — Audit Logger
Records security-sensitive actions to a MongoDB audit_logs collection for compliance.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.database import get_db

logger = logging.getLogger("arc.security.audit")


class AuditAction:
    """Constants for audit action types."""
    LOGIN = "auth.login"
    LOGOUT = "auth.logout"
    REGISTER = "auth.register"
    TOKEN_REFRESH = "auth.token_refresh"
    TASK_CREATE = "task.create"
    TASK_DELETE = "task.delete"
    FILE_UPLOAD = "file.upload"
    FILE_DELETE = "file.delete"
    AGENT_START = "agent.start"
    AGENT_COMPLETE = "agent.complete"
    AGENT_FAIL = "agent.fail"
    BUDGET_EXCEEDED = "cost.budget_exceeded"
    RATE_LIMITED = "security.rate_limited"
    PROMPT_INJECTION = "security.prompt_injection"
    LOOP_DETECTED = "security.loop_detected"
    SANDBOX_VIOLATION = "security.sandbox_violation"
    DATA_EXPORT = "data.export"
    DATA_DELETE = "data.delete"
    SETTINGS_CHANGE = "settings.change"


async def audit_log(
    action: str,
    user_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    success: bool = True,
) -> None:
    """
    Write an audit log entry to MongoDB.

    Args:
        action: AuditAction constant (e.g. "auth.login")
        user_id: Who performed the action
        resource_type: What type of resource was affected (task, file, etc.)
        resource_id: ID of affected resource
        details: Extra context
        ip_address: Client IP
        success: Whether the action succeeded
    """
    db = get_db()
    doc = {
        "action": action,
        "user_id": user_id,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "details": details or {},
        "ip_address": ip_address,
        "success": success,
        "timestamp": datetime.now(timezone.utc),
    }
    try:
        await db.audit_logs.insert_one(doc)
    except Exception as e:
        # Audit logging should never crash the app
        logger.error("Failed to write audit log: %s", e)
