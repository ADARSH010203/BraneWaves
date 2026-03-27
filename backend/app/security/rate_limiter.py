"""
ARC Platform — Rate Limiter
Redis-backed sliding-window rate limiter.
"""
from __future__ import annotations

import time
import logging

from fastapi import HTTPException, Request, status

from app.config import get_settings
from app.database import get_redis

logger = logging.getLogger("arc.rate_limiter")


async def check_rate_limit(key: str, max_requests: int | None = None, window_seconds: int = 60) -> None:
    """
    Sliding-window rate limit check against Redis.
    Raises HTTP 429 if exceeded.
    """
    settings = get_settings()
    limit = max_requests or settings.RATE_LIMIT_PER_MINUTE
    redis = get_redis()

    now = time.time()
    window_start = now - window_seconds
    rkey = f"rate:{key}"

    try:
        pipe = redis.pipeline()
        pipe.zremrangebyscore(rkey, 0, window_start)
        pipe.zadd(rkey, {str(now): now})
        pipe.zcard(rkey)
        pipe.expire(rkey, window_seconds + 1)
        results = await pipe.execute()
        
        count = results[2]
        if count > limit:
            logger.warning("Rate limit exceeded for key=%s count=%d limit=%d", key, count, limit)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please slow down.",
            )
    except HTTPException:
        raise
    except Exception as e:
        # Fallback gracefully if Redis is down
        logger.error("Rate limiter Redis error: %s", e)


async def rate_limit_by_ip(request: Request) -> None:
    """Rate limit dependency using client IP."""
    client_ip = request.client.host if request.client else "unknown"
    await check_rate_limit(f"ip:{client_ip}")


async def rate_limit_by_user(user_id: str) -> None:
    """Rate limit by authenticated user ID."""
    await check_rate_limit(f"user:{user_id}")
