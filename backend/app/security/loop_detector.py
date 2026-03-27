"""
ARC Platform — Loop Detector
Detects infinite loops in agent execution by tracking repeated tool calls and outputs.
"""
from __future__ import annotations

import hashlib
import logging
from collections import defaultdict
from typing import Any

logger = logging.getLogger("arc.security.loop_detector")

# Max times the same tool+input combo can repeat before flagging
MAX_REPEAT_CALLS = 3
# Max identical outputs in a row before flagging
MAX_IDENTICAL_OUTPUTS = 2


class LoopDetector:
    """
    Tracks agent actions per task and raises if loops are detected.

    Usage:
        detector = LoopDetector(task_id="t1")
        detector.record_action("web_search", {"query": "AI"})
        detector.record_output("some result text")
        detector.check()  # raises LoopDetectedError if stuck
    """

    def __init__(self, task_id: str, max_repeat_calls: int = MAX_REPEAT_CALLS, max_identical_outputs: int = MAX_IDENTICAL_OUTPUTS):
        self.task_id = task_id
        self.max_repeat_calls = max_repeat_calls
        self.max_identical_outputs = max_identical_outputs
        self._call_counts: dict[str, int] = defaultdict(int)
        self._recent_outputs: list[str] = []

    def _hash(self, data: Any) -> str:
        return hashlib.sha256(str(data).encode()).hexdigest()[:16]

    def record_action(self, tool_name: str, tool_input: dict[str, Any]) -> None:
        """Record a tool call."""
        key = f"{tool_name}:{self._hash(tool_input)}"
        self._call_counts[key] += 1

    def record_output(self, output: str) -> None:
        """Record an agent output."""
        h = self._hash(output)
        self._recent_outputs.append(h)
        # Keep only last N + 1 outputs
        if len(self._recent_outputs) > self.max_identical_outputs + 1:
            self._recent_outputs = self._recent_outputs[-(self.max_identical_outputs + 1):]

    def check(self) -> None:
        """Check for loops and raise if detected."""
        # Check repeated tool calls
        for key, count in self._call_counts.items():
            if count > self.max_repeat_calls:
                msg = f"Loop detected: tool call '{key}' repeated {count} times (max {self.max_repeat_calls})"
                logger.warning(msg)
                raise LoopDetectedError(msg)

        # Check identical consecutive outputs
        if len(self._recent_outputs) >= self.max_identical_outputs:
            recent = self._recent_outputs[-self.max_identical_outputs:]
            if len(set(recent)) == 1:
                msg = f"Loop detected: {self.max_identical_outputs} identical consecutive outputs"
                logger.warning(msg)
                raise LoopDetectedError(msg)

    def reset(self) -> None:
        """Reset all tracking state."""
        self._call_counts.clear()
        self._recent_outputs.clear()


class LoopDetectedError(Exception):
    """Raised when a loop is detected in agent execution."""
    pass
