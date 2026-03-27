"""
ARC Platform — Dataset Search Tool
Searches for datasets using public dataset APIs.
"""
from __future__ import annotations

from typing import Any

import httpx
from pydantic import Field

from app.tools.base import BaseTool, ToolInput


class DatasetSearchInput(ToolInput):
    """Input schema for dataset search."""
    query: str = Field(min_length=1, max_length=500, description="Search query for datasets")
    num_results: int = Field(default=10, ge=1, le=50, description="Number of results")


class DatasetSearchTool(BaseTool):
    """Searches for datasets using public APIs (HuggingFace, Kaggle)."""

    name = "dataset_search"
    description = "Search for datasets related to a topic"
    input_schema = DatasetSearchInput
    timeout_seconds = 30
    cost_estimate_usd = 0.0005
    permission_scope = "basic"

    async def execute(self, params: dict[str, Any], user_id: str) -> dict[str, Any]:
        query = params["query"]
        num_results = params.get("num_results", 10)

        try:
            # Search HuggingFace datasets API (free, no key)
            async with httpx.AsyncClient(timeout=25) as client:
                resp = await client.get(
                    "https://huggingface.co/api/datasets",
                    params={
                        "search": query,
                        "limit": num_results,
                        "sort": "downloads",
                        "direction": -1,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            datasets = []
            for ds in data[:num_results]:
                datasets.append({
                    "name": ds.get("id", ""),
                    "description": ds.get("description", "")[:500],
                    "downloads": ds.get("downloads", 0),
                    "likes": ds.get("likes", 0),
                    "tags": ds.get("tags", [])[:10],
                    "url": f"https://huggingface.co/datasets/{ds.get('id', '')}",
                })

            return {
                "success": True,
                "results": datasets,
                "query": query,
                "total_results": len(datasets),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "results": [],
                "query": query,
                "total_results": 0,
            }
