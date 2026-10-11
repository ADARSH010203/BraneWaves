"""
ARC Platform — Paper Search Tool
Academic search with Semantic Scholar primary and OpenAlex fallback.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx
from pydantic import Field

from app.tools.base import BaseTool, ToolInput

logger = logging.getLogger("arc.tools.paper_search")


class PaperSearchInput(ToolInput):
    query: str = Field(min_length=1, max_length=500, description="Search query for academic papers")
    num_results: int = Field(default=10, ge=1, le=50, description="Number of results")
    year_from: int | None = Field(default=None, description="Minimum publication year")
    fields_of_study: list[str] = Field(default_factory=list, description="Filter by field of study")


def _abstract_from_inverted(index: dict[str, list[int]] | None) -> str:
    if not index:
        return ""
    positioned: list[tuple[int, str]] = []
    for word, positions in index.items():
        for position in positions:
            positioned.append((int(position), word))
    positioned.sort(key=lambda item: item[0])
    return " ".join(word for _, word in positioned)


async def _semantic_scholar(
    client: httpx.AsyncClient,
    query: str,
    num_results: int,
    year_from: int | None,
    fields_of_study: list[str],
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "query": query,
        "limit": num_results,
        "fields": "title,abstract,authors,year,citationCount,url,externalIds,fieldsOfStudy",
    }
    if year_from:
        params["year"] = f"{int(year_from)}-"
    if fields_of_study:
        params["fieldsOfStudy"] = ",".join(fields_of_study)

    response = await client.get(
        "https://api.semanticscholar.org/graph/v1/paper/search",
        params=params,
    )
    response.raise_for_status()
    data = response.json()
    return [
        {
            "title": paper.get("title", ""),
            "abstract": paper.get("abstract", "") or "",
            "authors": [a.get("name", "") for a in paper.get("authors", [])],
            "year": paper.get("year"),
            "citation_count": paper.get("citationCount", 0),
            "url": paper.get("url", ""),
            "doi": (paper.get("externalIds") or {}).get("DOI", ""),
            "fields_of_study": paper.get("fieldsOfStudy", []) or [],
            "provider": "semantic_scholar",
        }
        for paper in data.get("data", [])
    ]


async def _openalex(
    client: httpx.AsyncClient,
    query: str,
    num_results: int,
    year_from: int | None,
    fields_of_study: list[str],
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "search": query,
        "per-page": min(50, max(num_results * 2, num_results)),
    }
    if year_from:
        params["filter"] = f"from_publication_date:{int(year_from)}-01-01"

    response = await client.get("https://api.openalex.org/works", params=params)
    response.raise_for_status()
    data = response.json()

    wanted = {value.casefold() for value in fields_of_study}
    papers: list[dict[str, Any]] = []
    for work in data.get("results", []):
        topics = [
            str(topic.get("display_name", ""))
            for topic in work.get("topics", [])
            if topic.get("display_name")
        ]
        if wanted and not any(
            any(w in topic.casefold() for topic in topics)
            for w in wanted
        ):
            continue

        primary_location = work.get("primary_location") or {}
        landing_page = primary_location.get("landing_page_url") or ""
        doi = str(work.get("doi") or "").removeprefix("https://doi.org/")
        papers.append({
            "title": work.get("title", "") or work.get("display_name", ""),
            "abstract": _abstract_from_inverted(work.get("abstract_inverted_index")),
            "authors": [
                ((authorship.get("author") or {}).get("display_name", ""))
                for authorship in work.get("authorships", [])
                if (authorship.get("author") or {}).get("display_name")
            ],
            "year": work.get("publication_year"),
            "citation_count": work.get("cited_by_count", 0),
            "url": landing_page or work.get("id", ""),
            "doi": doi,
            "fields_of_study": topics,
            "provider": "openalex",
        })
        if len(papers) >= num_results:
            break
    return papers


class PaperSearchTool(BaseTool):
    name = "paper_search"
    description = "Search academic papers with resilient provider fallback"
    input_schema = PaperSearchInput
    timeout_seconds = 30
    cost_estimate_usd = 0.0
    permission_scope = "basic"

    async def execute(self, params: dict[str, Any], user_id: str) -> dict[str, Any]:
        query = params["query"]
        num_results = params.get("num_results", 10)
        year_from = params.get("year_from")
        fields_of_study = [
            str(v).strip()
            for v in params.get("fields_of_study", [])
            if str(v).strip()
        ]
        errors: list[str] = []

        async with httpx.AsyncClient(timeout=25) as client:
            for provider, searcher in (
                ("semantic_scholar", _semantic_scholar),
                ("openalex", _openalex),
            ):
                try:
                    papers = await searcher(
                        client, query, num_results, year_from, fields_of_study
                    )
                    if papers:
                        return {
                            "success": True,
                            "results": papers[:num_results],
                            "query": query,
                            "total_results": len(papers[:num_results]),
                            "provider": provider,
                            "fallback_used": provider != "semantic_scholar",
                        }
                    errors.append(f"{provider}: returned no results")
                except Exception as exc:
                    logger.warning("Paper search provider %s failed: %s", provider, exc)
                    errors.append(f"{provider}: {exc}")

        return {
            "success": False,
            "error": "; ".join(errors),
            "results": [],
            "query": query,
            "total_results": 0,
            "provider": None,
            "fallback_used": False,
        }
