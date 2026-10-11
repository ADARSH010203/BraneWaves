"""
ARC Platform — Web Search Tool
Provider-backed web search with normalized results and resilient fallback routing.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx
from pydantic import Field

from app.config import get_settings
from app.tools.base import BaseTool, ToolInput

logger = logging.getLogger("arc.tools.web_search")
settings = get_settings()


class WebSearchInput(ToolInput):
    """Input schema for web search."""
    query: str = Field(min_length=1, max_length=500, description="Search query")
    num_results: int = Field(default=10, ge=1, le=20, description="Number of results")
    language: str = Field(default="en", description="Language code")


def configured_search_providers() -> list[str]:
    """Return providers that can actually be used with the current configuration."""
    providers: list[str] = []
    if settings.BRAVE_SEARCH_API_KEY:
        providers.append("brave")
    if settings.TAVILY_API_KEY:
        providers.append("tavily")
    if settings.SERPER_API_KEY:
        providers.append("serper")
    providers.append("duckduckgo")
    return providers


def search_provider_order() -> list[str]:
    configured = configured_search_providers()
    if settings.WEB_SEARCH_PROVIDER == "auto":
        return configured
    return [settings.WEB_SEARCH_PROVIDER]


def _normalized(
    *,
    title: str,
    url: str,
    snippet: str,
    source: str,
) -> dict[str, str]:
    return {
        "title": str(title or "").strip(),
        "url": str(url or "").strip(),
        "snippet": str(snippet or "").strip(),
        "source": str(source or "").strip(),
    }


async def _search_brave(
    client: httpx.AsyncClient,
    query: str,
    num_results: int,
    language: str,
) -> list[dict[str, str]]:
    if not settings.BRAVE_SEARCH_API_KEY:
        raise RuntimeError("BRAVE_SEARCH_API_KEY is not configured")
    response = await client.get(
        "https://api.search.brave.com/res/v1/web/search",
        params={
            "q": query,
            "count": num_results,
            "search_lang": language,
            "safesearch": "moderate",
        },
        headers={
            "Accept": "application/json",
            "X-Subscription-Token": settings.BRAVE_SEARCH_API_KEY,
        },
    )
    response.raise_for_status()
    data = response.json()
    return [
        _normalized(
            title=item.get("title", ""),
            url=item.get("url", ""),
            snippet=item.get("description", ""),
            source="Brave Search",
        )
        for item in data.get("web", {}).get("results", [])[:num_results]
        if item.get("url")
    ]


async def _search_tavily(
    client: httpx.AsyncClient,
    query: str,
    num_results: int,
    language: str,
) -> list[dict[str, str]]:
    if not settings.TAVILY_API_KEY:
        raise RuntimeError("TAVILY_API_KEY is not configured")
    response = await client.post(
        "https://api.tavily.com/search",
        json={
            "api_key": settings.TAVILY_API_KEY,
            "query": query,
            "max_results": num_results,
            "search_depth": "basic",
            "include_answer": False,
            "include_raw_content": False,
        },
    )
    response.raise_for_status()
    data = response.json()
    return [
        _normalized(
            title=item.get("title", ""),
            url=item.get("url", ""),
            snippet=item.get("content", ""),
            source="Tavily",
        )
        for item in data.get("results", [])[:num_results]
        if item.get("url")
    ]


async def _search_serper(
    client: httpx.AsyncClient,
    query: str,
    num_results: int,
    language: str,
) -> list[dict[str, str]]:
    if not settings.SERPER_API_KEY:
        raise RuntimeError("SERPER_API_KEY is not configured")
    response = await client.post(
        "https://google.serper.dev/search",
        headers={
            "X-API-KEY": settings.SERPER_API_KEY,
            "Content-Type": "application/json",
        },
        json={"q": query, "num": num_results, "hl": language},
    )
    response.raise_for_status()
    data = response.json()
    return [
        _normalized(
            title=item.get("title", ""),
            url=item.get("link", ""),
            snippet=item.get("snippet", ""),
            source="Google via Serper",
        )
        for item in data.get("organic", [])[:num_results]
        if item.get("link")
    ]


async def _search_duckduckgo(
    client: httpx.AsyncClient,
    query: str,
    num_results: int,
    language: str,
) -> list[dict[str, str]]:
    locale_map = {
        "en": "us-en",
        "de": "de-de",
        "fr": "fr-fr",
        "es": "es-es",
        "it": "it-it",
        "nl": "nl-nl",
        "no": "no-no",
        "sv": "se-sv",
        "hi": "in-en",
    }
    response = await client.get(
        "https://api.duckduckgo.com/",
        params={
            "q": query,
            "format": "json",
            "no_redirect": 1,
            "no_html": 1,
            "kl": locale_map.get(language, "us-en"),
        },
    )
    response.raise_for_status()
    data = response.json()
    results: list[dict[str, str]] = []
    if data.get("Abstract") and data.get("AbstractURL"):
        results.append(
            _normalized(
                title=data.get("Heading", ""),
                url=data.get("AbstractURL", ""),
                snippet=data.get("Abstract", ""),
                source=data.get("AbstractSource", "DuckDuckGo"),
            )
        )

    for topic in data.get("RelatedTopics", []):
        if len(results) >= num_results:
            break
        if not isinstance(topic, dict):
            continue
        nested = topic.get("Topics")
        candidates = nested if isinstance(nested, list) else [topic]
        for item in candidates:
            if len(results) >= num_results:
                break
            if not isinstance(item, dict) or not item.get("FirstURL"):
                continue
            results.append(
                _normalized(
                    title=str(item.get("Text", ""))[:120],
                    url=item.get("FirstURL", ""),
                    snippet=item.get("Text", ""),
                    source="DuckDuckGo",
                )
            )
    return results[:num_results]


_SEARCHERS = {
    "brave": _search_brave,
    "tavily": _search_tavily,
    "serper": _search_serper,
    "duckduckgo": _search_duckduckgo,
}


class WebSearchTool(BaseTool):
    """Searches the web using configured production providers with fallback routing."""

    name = "web_search"
    description = "Search the live web using a configured search provider"
    input_schema = WebSearchInput
    timeout_seconds = 30
    cost_estimate_usd = 0.0
    permission_scope = "basic"

    async def execute(self, params: dict[str, Any], user_id: str) -> dict[str, Any]:
        query = params["query"]
        num_results = params.get("num_results", 10)
        language = str(params.get("language", "en")).lower()
        errors: list[str] = []

        async with httpx.AsyncClient(timeout=settings.TOOL_TIMEOUT_WEB_SEARCH) as client:
            for provider in search_provider_order():
                searcher = _SEARCHERS[provider]
                try:
                    results = await searcher(client, query, num_results, language)
                    if results:
                        return {
                            "success": True,
                            "results": results,
                            "query": query,
                            "total_results": len(results),
                            "provider": provider,
                            "fallback_used": provider != search_provider_order()[0],
                        }
                    errors.append(f"{provider}: returned no results")
                except Exception as exc:
                    logger.warning("Web search provider %s failed: %s", provider, exc)
                    errors.append(f"{provider}: {exc}")

                # Explicit provider mode is fail-closed; auto mode may fall back.
                if settings.WEB_SEARCH_PROVIDER != "auto":
                    break

        return {
            "success": False,
            "error": "; ".join(errors) or "No search provider returned results",
            "results": [],
            "query": query,
            "total_results": 0,
            "provider": None,
            "fallback_used": False,
        }
