"""
ARC Platform — Metrics Hooks
Simple in-process metric counters; pluggable for Prometheus / Datadog.
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Any

logger = logging.getLogger("arc.metrics")

# ── In-memory counters ───────────────────────────────────────────────────────
_counters: dict[str, float] = defaultdict(float)
_timers: dict[str, list[float]] = defaultdict(list)


def inc(metric: str, value: float = 1.0) -> None:
    """Increment a counter metric."""
    _counters[metric] += value


def observe(metric: str, duration_s: float) -> None:
    """Record an observation (e.g. latency)."""
    _timers[metric].append(duration_s)


class Timer:
    """Context manager to time a block and record it."""

    def __init__(self, metric: str):
        self.metric = metric
        self._start = 0.0

    def __enter__(self) -> "Timer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *_: Any) -> None:
        elapsed = time.perf_counter() - self._start
        observe(self.metric, elapsed)


def snapshot() -> dict:
    """Return current metrics snapshot."""
    return {
        "counters": dict(_counters),
        "timers": {k: {"count": len(v), "avg": sum(v) / len(v) if v else 0} for k, v in _timers.items()},
    }
