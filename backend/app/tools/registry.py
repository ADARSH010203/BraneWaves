"""
ARC Platform — Tool Registry
Central registry for all tools with permission checking and dispatch.
"""
from __future__ import annotations

import logging
from typing import Any

from app.tools.base import BaseTool

logger = logging.getLogger("arc.tools.registry")


class ToolRegistry:
    """
    Central registry for all ARC tools.
    Manages registration, permission checks, and execution dispatch.
    """

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        self._allowlist: set[str] = set()

    def register(self, tool: BaseTool) -> None:
        """Register a tool in the registry."""
        self._tools[tool.name] = tool
        self._allowlist.add(tool.name)
        logger.info("Registered tool: %s", tool.name)

    def get(self, name: str) -> BaseTool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[dict[str, Any]]:
        """List all registered tools with metadata."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "timeout_seconds": t.timeout_seconds,
                "cost_estimate_usd": t.cost_estimate_usd,
                "permission_scope": t.permission_scope,
                "input_schema": t.input_schema.model_json_schema(),
            }
            for t in self._tools.values()
        ]

    async def execute(
        self,
        tool_name: str,
        params: dict[str, Any],
        user_id: str,
    ) -> dict[str, Any]:
        """Execute a tool by name with permission and allowlist checks."""
        # Allowlist check
        if tool_name not in self._allowlist:
            raise PermissionError(f"Tool '{tool_name}' is not in the allowlist")

        tool = self._tools.get(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found in registry")

        logger.info("Executing tool: %s for user: %s", tool_name, user_id)
        return await tool.run(params, user_id)

    def set_allowlist(self, allowed: list[str]) -> None:
        """Set the tool allowlist. Only listed tools can be executed."""
        self._allowlist = set(allowed)

    def is_allowed(self, tool_name: str) -> bool:
        """Check if a tool is in the allowlist."""
        return tool_name in self._allowlist


# ── Global singleton ─────────────────────────────────────────────────────────
tool_registry = ToolRegistry()


def register_all_tools() -> None:
    """Register all built-in tools."""
    from app.tools.web_search import WebSearchTool
    from app.tools.paper_search import PaperSearchTool
    from app.tools.dataset_search import DatasetSearchTool
    from app.tools.python_sandbox import PythonSandboxTool
    from app.tools.vector_search import VectorSearchTool
    from app.tools.citation_verify import CitationVerifyTool

    tool_registry.register(WebSearchTool())
    tool_registry.register(PaperSearchTool())
    tool_registry.register(DatasetSearchTool())
    tool_registry.register(PythonSandboxTool())
    tool_registry.register(VectorSearchTool())
    tool_registry.register(CitationVerifyTool())

    logger.info("All %d tools registered", len(tool_registry._tools))
