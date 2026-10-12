"""
ARC Platform — Web Search Tool
Provider-backed web search with normalized results and resilient fallback routing.
"""
from __future__ import annotations

import logging
from html import unescape
from html.parser import HTMLParser
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

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
    """Choose providers for the selected cost policy.

    Free mode never invokes Brave or Serper, even when those keys exist.
    Tavily must be enrolled in its no-card Free plan for zero-charge usage.
    """
    mode = settings.WEB_SEARCH_PROVIDER
    if mode == "free":
        return (["tavily"] if settings.TAVILY_API_KEY else []) + ["duckduckgo"]
    if mode == "auto":
        return configured_search_providers()
    return [mode]


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
        headers={"Authorization": f"Bearer {settings.TAVILY_API_KEY}"},
        json={
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


class _DuckDuckGoHTMLParser(HTMLParser):
    """Minimal parser for DuckDuckGo HTML result cards."""

    def __init__(self, limit: int):
        super().__init__(convert_charrefs=True)
        self.limit = limit
        self.results: list[dict[str, str]] = []
        self._current: dict[str, str] | None = None
        self._capture_title = False
        self._capture_snippet = False

    @staticmethod
    def _classes(attrs: list[tuple[str, str | None]]) -> set[str]:
        value = dict(attrs).get("class") or ""
        return set(value.split())

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if len(self.results) >= self.limit:
            return
        classes = self._classes(attrs)
        attr_map = dict(attrs)
        if tag == "a" and "result__a" in classes:
            self._current = {
                "title": "",
                "url": _decode_duckduckgo_url(attr_map.get("href") or ""),
                "snippet": "",
                "source": "DuckDuckGo",
            }
            self._capture_title = True
        elif self._current is not None and "result__snippet" in classes:
            self._capture_snippet = True

    def handle_data(self, data: str) -> None:
        if self._current is None:
            return
        if self._capture_title:
            self._current["title"] += data
        elif self._capture_snippet:
            self._current["snippet"] += data

    def handle_endtag(self, tag: str) -> None:
        if self._current is None:
            return
        if tag == "a" and self._capture_title:
            self._capture_title = False
            if self._current["url"]:
                self.results.append(self._current)
            self._current = None
        elif self._capture_snippet and tag in {"a", "div", "span"}:
            self._capture_snippet = False


def _decode_duckduckgo_url(url: str) -> str:
    value = unescape(url)
    if value.startswith("//"):
        value = "https:" + value
    try:
        parsed = urlparse(value)
        if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
            target = parse_qs(parsed.query).get("uddg", [])
            if target:
                return unquote(target[0])
    except Exception:
        pass
    return value


async def _search_duckduckgo_html(
    client: httpx.AsyncClient,
    query: str,
    num_results: int,
    language: str,
) -> list[dict[str, str]]:
    response = await client.get(
        "https://html.duckduckgo.com/html/",
        params={"q": query, "kl": language},
        headers={
            "User-Agent": (
                "Mozilla/5.0 (compatible; ARCResearchBot/1.0; "
                "+https://github.com/ADARSH010203/BraneWaves)"
            )
        },
    )
    response.raise_for_status()
    parser = _DuckDuckGoHTMLParser(num_results)
    parser.feed(response.text)
    return [
        _normalized(
            title=item.get("title", ""),
            url=item.get("url", ""),
            snippet=item.get("snippet", ""),
            source="DuckDuckGo",
        )
        for item in parser.results[:num_results]
        if item.get("url")
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

    if not results:
        results = await _search_duckduckgo_html(
            client, query, num_results, language
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

                # Explicit provider mode is fail-closed; free/auto allow fallback.
                if settings.WEB_SEARCH_PROVIDER not in {"free", "auto"}:
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
