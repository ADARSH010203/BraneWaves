"""Container healthcheck for the background worker."""
from __future__ import annotations

import asyncio
import sys

import redis.asyncio as aioredis

from app.config import get_settings

WORKER_HEARTBEAT_KEY = "arc:worker:heartbeat"


async def main() -> int:
    settings = get_settings()
    client = aioredis.from_url(str(settings.REDIS_URL), decode_responses=True)
    try:
        value = await client.get(WORKER_HEARTBEAT_KEY)
        return 0 if value else 1
    except Exception:
        return 1
    finally:
        await client.aclose()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
