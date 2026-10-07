"""
ARC Platform — Background Task Worker
Consumes tasks from Redis queue and executes them via the orchestrator.
"""
from __future__ import annotations

import asyncio
import json
import logging
import signal
import sys

from app.agents.orchestrator import TaskOrchestrator
from app.config import get_settings
from app.database import connect_db, connect_redis, disconnect_db, disconnect_redis, get_redis
from app.observability.logger import setup_logging
from app.tools.registry import register_all_tools

settings = get_settings()
setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger("arc.worker")

_shutdown = False


async def process_task(task_data: dict) -> None:
    """Execute a single task using the orchestrator."""
    task_id = task_data["task_id"]
    user_id = task_data["user_id"]

    logger.info("Processing task: %s (user: %s)", task_id, user_id)

    orchestrator = TaskOrchestrator(task_id=task_id, user_id=user_id)
    try:
        result = await orchestrator.execute()
        logger.info("Task %s completed: %s", task_id, result.get("status", "unknown"))
    except Exception as e:
        logger.exception("Task %s failed: %s", task_id, e)


async def worker_loop() -> None:
    """Main worker loop: consume tasks from Redis queue."""
    global _shutdown
    logger.info("🔧 Worker started — waiting for tasks...")

    redis = get_redis()
    if redis is None:
        raise RuntimeError("Redis is required for the background worker")

    # Recover jobs left in the processing list by a previously crashed worker.
    while True:
        stale = await redis.rpoplpush("task_processing", "task_queue")
        if stale is None:
            break

    while not _shutdown:
        try:
            # Atomically move the job into a processing list. A crash leaves the
            # payload recoverable instead of losing it after BLPOP.
            raw = await redis.brpoplpush("task_queue", "task_processing", timeout=5)
            if raw is None:
                continue

            task_data = json.loads(raw)
            await process_task(task_data)
            await redis.lrem("task_processing", 1, raw)

        except json.JSONDecodeError as e:
            logger.error("Invalid task data: %s", e)
            if "raw" in locals() and raw:
                await redis.lrem("task_processing", 1, raw)
        except Exception as e:
            logger.exception("Worker error: %s", e)
            await asyncio.sleep(1)


async def main() -> None:
    """Worker entrypoint."""
    global _shutdown

    def handle_shutdown(*_):
        global _shutdown
        _shutdown = True
        logger.info("Shutdown signal received")

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    # Initialize connections
    await connect_db()
    await connect_redis()
    register_all_tools()

    try:
        await worker_loop()
    finally:
        await disconnect_redis()
        await disconnect_db()
        logger.info("👋 Worker shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
