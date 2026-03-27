"""
ARC Platform — BaseTool
Abstract base class for all tools with schema, timeout, cost, and permissions.
"""
from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger("arc.tools.base")


class ToolInput(BaseModel):
    """Base class for tool input schemas. Subclasses add specific fields."""
    pass


class ToolOutput(BaseModel):
    """Base class for tool output schemas."""
    success: bool = True
    results: Any = None
    error: str | None = None
    duration_ms: float = 0.0
    cost_estimate_usd: float = 0.0


class BaseTool(ABC):
    """
    Abstract base class for all ARC tools.

    Each tool must define:
    - name: unique identifier
    - description: what the tool does
    - input_schema: Pydantic model for validation
    - timeout_seconds: max execution time
    - cost_estimate_usd: estimated cost per invocation
    - permission_scope: required permission level
    """

    name: str = ""
    description: str = ""
    input_schema: type[ToolInput] = ToolInput
    timeout_seconds: int = 30
    cost_estimate_usd: float = 0.0
    permission_scope: str = "basic"  # basic, elevated, admin

    @abstractmethod
    async def execute(self, params: dict[str, Any], user_id: str) -> dict[str, Any]:
        """Execute the tool with the given parameters."""
        ...

    async def run(self, params: dict[str, Any], user_id: str) -> dict[str, Any]:
        """Validate input, enforce timeout, and execute."""
        # Validate input
        validated = self.input_schema(**params)

        start = time.perf_counter()
        try:
            result = await asyncio.wait_for(
                self.execute(validated.model_dump(), user_id),
                timeout=self.timeout_seconds,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            result["duration_ms"] = elapsed_ms
            result["cost_estimate_usd"] = self.cost_estimate_usd
            return result
        except asyncio.TimeoutError:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.warning("Tool %s timed out after %.0f ms", self.name, elapsed_ms)
            return {
                "success": False,
                "error": f"Tool {self.name} timed out after {self.timeout_seconds}s",
                "duration_ms": elapsed_ms,
                "cost_estimate_usd": 0.0,
            }
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.error("Tool %s error: %s", self.name, e)
            return {
                "success": False,
                "error": str(e),
                "duration_ms": elapsed_ms,
                "cost_estimate_usd": 0.0,
            }
