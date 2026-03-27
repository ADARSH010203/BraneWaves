"""
ARC Platform — Middleware
Request logging with trace IDs, request-size limiter, timing.
"""
from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import get_settings

logger = logging.getLogger("arc.middleware")


class TraceIDMiddleware(BaseHTTPMiddleware):
    """Inject a unique trace-id into every request/response."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
        request.state.trace_id = trace_id

        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        response.headers["X-Trace-ID"] = trace_id
        response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.1f}"

        logger.info(
            "[%s] %s %s → %s (%.1f ms)",
            trace_id[:8],
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests exceeding the configured body size."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        settings = get_settings()
        max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024

        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > max_bytes:
            return JSONResponse(
                status_code=413,
                content={"detail": f"Request body exceeds {settings.MAX_FILE_SIZE_MB} MB limit"},
            )
        return await call_next(request)
