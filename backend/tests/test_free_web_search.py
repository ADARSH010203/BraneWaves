"""Free web search mode: cost-policy routing and Tavily Bearer authentication."""
from __future__ import annotations

import pytest


def test_free_mode_prefers_tavily_and_excludes_paid_providers(monkeypatch):
    import app.tools.web_search as module

    monkeypatch.setattr(module.settings, "WEB_SEARCH_PROVIDER", "free")
    monkeypatch.setattr(module.settings, "TAVILY_API_KEY", "free-plan-key")
    monkeypatch.setattr(module.settings, "BRAVE_SEARCH_API_KEY", "paid-brave-key")
    monkeypatch.setattr(module.settings, "SERPER_API_KEY", "paid-serper-key")

    assert module.search_provider_order() == ["tavily", "duckduckgo"]


def test_free_mode_without_key_uses_keyless_fallback(monkeypatch):
    import app.tools.web_search as module

    monkeypatch.setattr(module.settings, "WEB_SEARCH_PROVIDER", "free")
    monkeypatch.setattr(module.settings, "TAVILY_API_KEY", None)
    monkeypatch.setattr(module.settings, "BRAVE_SEARCH_API_KEY", "configured")
    monkeypatch.setattr(module.settings, "SERPER_API_KEY", "configured")

    assert module.search_provider_order() == ["duckduckgo"]


@pytest.mark.asyncio
async def test_tavily_uses_bearer_auth_and_basic_search(monkeypatch):
    import app.tools.web_search as module

    monkeypatch.setattr(module.settings, "TAVILY_API_KEY", "test-free-key")
    seen = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"results": [{
                "title": "Useful page",
                "url": "https://example.com/page",
                "content": "Verified snippet",
            }]}

    class FakeClient:
        async def post(self, url, *, headers, json):
            seen.update({"url": url, "headers": headers, "body": json})
            return FakeResponse()

    results = await module._search_tavily(FakeClient(), "free search", 3, "en")
    assert seen["url"] == "https://api.tavily.com/search"
    assert seen["headers"]["Authorization"] == "Bearer test-free-key"
    assert "api_key" not in seen["body"]
    assert seen["body"]["search_depth"] == "basic"
    assert seen["body"]["include_raw_content"] is False
    assert results[0]["source"] == "Tavily"


@pytest.mark.asyncio
async def test_free_mode_uses_ddg_after_tavily_failure_without_touching_paid(monkeypatch):
    import app.tools.web_search as module

    monkeypatch.setattr(module.settings, "WEB_SEARCH_PROVIDER", "free")
    monkeypatch.setattr(module.settings, "TAVILY_API_KEY", "configured")
    monkeypatch.setattr(module.settings, "BRAVE_SEARCH_API_KEY", "configured")
    monkeypatch.setattr(module.settings, "SERPER_API_KEY", "configured")

    invoked = []

    async def tavily_failure(*_args, **_kwargs):
        invoked.append("tavily")
        raise RuntimeError("Free credits exhausted")

    async def ddg_success(*_args, **_kwargs):
        invoked.append("duckduckgo")
        return [{
            "title": "Result",
            "url": "https://example.com",
            "snippet": "Useful result",
            "source": "DuckDuckGo",
        }]

    async def forbidden_paid(*_args, **_kwargs):
        pytest.fail("Free mode must never call paid providers")

    monkeypatch.setitem(module._SEARCHERS, "tavily", tavily_failure)
    monkeypatch.setitem(module._SEARCHERS, "duckduckgo", ddg_success)
    monkeypatch.setitem(module._SEARCHERS, "brave", forbidden_paid)
    monkeypatch.setitem(module._SEARCHERS, "serper", forbidden_paid)

    result = await module.WebSearchTool().execute(
        {"query": "test query", "num_results": 3, "language": "en"},
        "user-1",
    )
    assert result["success"] is True
    assert result["provider"] == "duckduckgo"
    assert result["fallback_used"] is True
    assert invoked == ["tavily", "duckduckgo"]
