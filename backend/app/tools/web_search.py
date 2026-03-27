"""
ARC Platform — Web Search Tool
Searches the web using an external search API.
"""
from __future__ import annotations

from typing import Any

import httpx
from pydantic import Field

from app.config import get_settings
from app.tools.base import BaseTool, ToolInput

settings = get_settings()


class WebSearchInput(ToolInput):
    """Input schema for web search."""
    query: str = Field(min_length=1, max_length=500, description="Search query")
    num_results: int = Field(default=10, ge=1, le=20, description="Number of results")
    language: str = Field(default="en", description="Language code")


class WebSearchTool(BaseTool):
    """Searches the web for relevant information."""

    name = "web_search"
    description = "Search the web for information on a given topic"
    input_schema = WebSearchInput
    timeout_seconds = 30
    cost_estimate_usd = 0.001
    permission_scope = "basic"

    async def execute(self, params: dict[str, Any], user_id: str) -> dict[str, Any]:
        query = params["query"]
        num_results = params.get("num_results", 10)

        # Use a search API (DuckDuckGo instant answer as fallback)
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                # DuckDuckGo Instant Answer API (free, no API key needed)
                resp = await client.get(
                    "https://api.duckduckgo.com/",
                    params={
                        "q": query,
                        "format": "json",
                        "no_redirect": 1,
                        "no_html": 1,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            results = []
            # Abstract
            if data.get("Abstract"):
                results.append({
                    "title": data.get("Heading", ""),
                    "url": data.get("AbstractURL", ""),
                    "snippet": data.get("Abstract", ""),
                    "source": data.get("AbstractSource", ""),
                })

            # Related topics
            for topic in data.get("RelatedTopics", [])[:num_results]:
                if isinstance(topic, dict) and "Text" in topic:
                    results.append({
                        "title": topic.get("Text", "")[:100],
                        "url": topic.get("FirstURL", ""),
                        "snippet": topic.get("Text", ""),
                        "source": "DuckDuckGo",
                    })

            return {
                "success": True,
                "results": results,
                "query": query,
                "total_results": len(results),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "results": [],
                "query": query,
                "total_results": 0,
            }
