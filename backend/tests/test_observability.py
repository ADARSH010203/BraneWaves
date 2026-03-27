"""Tests for observability — logger, metrics."""
from app.observability.logger import setup_logging
from app.observability.metrics import inc, Timer, snapshot


class TestMetrics:
    def test_counter(self):
        inc("test.count", 1)
        inc("test.count", 1)
        snap = snapshot()
        assert snap["counters"]["test.count"] >= 2

    def test_timer(self):
        import time
        with Timer("test.timer"):
            time.sleep(0.01)
        snap = snapshot()
        assert "test.timer" in snap["timers"]
        assert snap["timers"]["test.timer"]["count"] >= 1

    def test_snapshot_structure(self):
        snap = snapshot()
        assert "counters" in snap
        assert "timers" in snap


class TestLogger:
    def test_setup_logging(self):
        setup_logging("INFO")
        # Should not raise
        import logging
        logger = logging.getLogger("arc")
        assert logger is not None
