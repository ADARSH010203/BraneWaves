"""
ARC Platform — WebSocket Route
WS /tasks/{task_id}/stream — Live agent execution streaming.
"""
from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.database import get_redis
from app.security.jwt_handler import decode_access_token

logger = logging.getLogger("arc.routes.ws")

router = APIRouter()


@router.websocket("/tasks/{task_id}/stream")
async def task_stream(websocket: WebSocket, task_id: str):
    """
    WebSocket endpoint for live task execution streaming.

    Client must send a JWT token as the first message for authentication.
    Then receives real-time events via Redis pub/sub.
    """
    await websocket.accept()

    # ── Auth handshake ───────────────────────────────────────────────────
    try:
        auth_msg = await asyncio.wait_for(websocket.receive_text(), timeout=10)
        auth_data = json.loads(auth_msg)
        token = auth_data.get("token", "")
        payload = decode_access_token(token)
        if not payload:
            await websocket.send_json({"error": "Invalid token"})
            await websocket.close(code=4001)
            return
        user_id = payload["sub"]
    except (asyncio.TimeoutError, json.JSONDecodeError):
        await websocket.send_json({"error": "Authentication required"})
        await websocket.close(code=4001)
        return

    # Verify task belongs to user
    from app.database import get_db
    db = get_db()
    task = await db.tasks.find_one({"_id": task_id, "user_id": user_id})
    if not task:
        await websocket.send_json({"error": "Task not found"})
        await websocket.close(code=4004)
        return

    await websocket.send_json({"event": "connected", "task_id": task_id})
    logger.info("WS connected: user=%s task=%s", user_id, task_id)

    # ── Subscribe to Redis pub/sub ───────────────────────────────────────
    redis = get_redis()
    pubsub = redis.pubsub()
    channel = f"task:{task_id}"
    await pubsub.subscribe(channel)

    try:
        while True:
            # Check for Redis messages
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5)
            if message and message["type"] == "message":
                data = message["data"]
                if isinstance(data, str):
                    await websocket.send_text(data)
                elif isinstance(data, bytes):
                    await websocket.send_text(data.decode())

            # Small sleep to prevent busy loop
            await asyncio.sleep(0.1)

    except WebSocketDisconnect:
        logger.info("WS disconnected: user=%s task=%s", user_id, task_id)
    except Exception as e:
        logger.error("WS error: %s", e)
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
