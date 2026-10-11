"""
ARC Platform — Paper Search Tool
Searches academic papers using Semantic Scholar API.
"""
from __future__ import annotations

from typing import Any

import httpx
from pydantic import Field

from app.tools.base import BaseTool, ToolInput


class PaperSearchInput(ToolInput):
    """Input schema for paper search."""
    query: str = Field(min_length=1, max_length=500, description="Search query for academic papers")
    num_results: int = Field(default=10, ge=1, le=50, description="Number of results")
    year_from: int | None = Field(default=None, description="Minimum publication year")
    fields_of_study: list[str] = Field(default_factory=list, description="Filter by field of study")


class PaperSearchTool(BaseTool):
    """Searches academic papers using Semantic Scholar API."""

    name = "paper_search"
    description = "Search for academic papers on a given topic"
    input_schema = PaperSearchInput
    timeout_seconds = 30
    cost_estimate_usd = 0.0
    permission_scope = "basic"

    async def execute(self, params: dict[str, Any], user_id: str) -> dict[str, Any]:
        query = params["query"]
        num_results = params.get("num_results", 10)
        year_from = params.get("year_from")
        fields_of_study = [str(v).strip() for v in params.get("fields_of_study", []) if str(v).strip()]

        search_params = {
            "query": query,
            "limit": num_results,
            "fields": "title,abstract,authors,year,citationCount,url,externalIds,fieldsOfStudy",
        }
        if year_from:
            search_params["year"] = f"{int(year_from)}-"
        if fields_of_study:
            search_params["fieldsOfStudy"] = ",".join(fields_of_study)

        try:
            async with httpx.AsyncClient(timeout=25) as client:
                resp = await client.get(
                    "https://api.semanticscholar.org/graph/v1/paper/search",
                    params=search_params,
                )
                resp.raise_for_status()
                data = resp.json()

            papers = []
            for paper in data.get("data", []):
                authors = [a.get("name", "") for a in paper.get("authors", [])]
                papers.append({
                    "title": paper.get("title", ""),
                    "abstract": paper.get("abstract", ""),
                    "authors": authors,
                    "year": paper.get("year"),
                    "citation_count": paper.get("citationCount", 0),
                    "url": paper.get("url", ""),
                    "doi": paper.get("externalIds", {}).get("DOI", ""),
                    "fields_of_study": paper.get("fieldsOfStudy", []),
                })

            return {
                "success": True,
                "results": papers,
                "query": query,
                "total_results": data.get("total", len(papers)),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "results": [],
                "query": query,
                "total_results": 0,
            }
