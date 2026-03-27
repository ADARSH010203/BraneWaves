"""
ARC Platform — Structured Logging
JSON-structured logging with trace-ID propagation.
"""
from __future__ import annotations

import logging
import sys


class StructuredFormatter(logging.Formatter):
    """Simple structured log format with ISO timestamps."""

    def format(self, record: logging.LogRecord) -> str:
        level = record.levelname.ljust(8)
        name = record.name
        msg = record.getMessage()
        ts = self.formatTime(record, "%Y-%m-%dT%H:%M:%S")
        return f"{ts} | {level} | {name} | {msg}"


def setup_logging(level: str = "INFO") -> None:
    """Configure root logger with structured formatter."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Prevent duplicate handlers on reload
    if root.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())
    root.addHandler(handler)

    # Quiet noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("motor").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
