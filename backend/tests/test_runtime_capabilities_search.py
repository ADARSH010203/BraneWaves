"""Runtime capability and production web-search regression tests."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.agents.planner import PlannerAgent


@pytest.mark.asyncio
async def test_planner_replans_code_when_sandbox_unavailable(monkeypatch):
    import app.agents.memory as memory_module
    import app.agents.planner as planner_module

    async def no_memory(*_args, **_kwargs):
        return []

    monkeypatch.setattr(memory_module, "search_memory_graph", no_memory)
    monkeypatch.setattr(
        planner_module,
        "get_settings",
        lambda: SimpleNamespace(PYTHON_SANDBOX_URL=None),
    )

    responses = [
        {
            "content": (
                '{"steps":[{"id":"code_1","title":"Compute","type":"code",'
                '"description":"Run Python","depends_on":[],"input_data":{}}],'
                '"confidence":0.8,"rationale":"Use Python"}'
            ),
            "tokens": {"prompt": 10, "completion": 10, "total": 20},
            "cost_usd": 0.001,
        },
        {
            "content": (
                '{"steps":[{"id":"data_1","title":"Analyze","type":"data",'
                '"description":"Analyze without Python","depends_on":[],"input_data":{}}],'
                '"confidence":0.8,"rationale":"Sandbox unavailable"}'
            ),
            "tokens": {"prompt": 12, "completion": 8, "total": 20},
            "cost_usd": 0.001,
        },
    ]

    agent = PlannerAgent(task_id="task-1", step_id="planner", user_id="user-1")

    async def fake_call_llm(*_args, **_kwargs):
        return responses.pop(0)

    monkeypatch.setattr(agent, "call_llm", fake_call_llm)
    output = await agent.run({"title": "Compute", "description": "Analyze values"})

    assert [step["type"] for step in output["steps"]] == ["data"]
    assert output["runtime_capabilities"]["python_sandbox"] is False
    assert output["runtime_capabilities"]["allowed_step_types"] == ["research", "data"]
    assert output["cost_usd"] == pytest.approx(0.002)
    assert output["tokens"]["total"] == 40


@pytest.mark.asyncio
async def test_web_search_auto_falls_back_to_next_provider(monkeypatch):
    import app.tools.web_search as module

    monkeypatch.setattr(module.settings, "WEB_SEARCH_PROVIDER", "auto")
    monkeypatch.setattr(module.settings, "BRAVE_SEARCH_API_KEY", "configured")
    monkeypatch.setattr(module.settings, "TAVILY_API_KEY", None)
    monkeypatch.setattr(module.settings, "SERPER_API_KEY", None)

    async def brave_failure(*_args, **_kwargs):
        raise RuntimeError("provider down")

    async def ddg_success(*_args, **_kwargs):
        return [{
            "title": "Result",
            "url": "https://example.com",
            "snippet": "Useful result",
            "source": "DuckDuckGo",
        }]

    monkeypatch.setitem(module._SEARCHERS, "brave", brave_failure)
    monkeypatch.setitem(module._SEARCHERS, "duckduckgo", ddg_success)

    result = await module.WebSearchTool().execute(
        {"query": "test query", "num_results": 3, "language": "en"},
        "user-1",
    )
    assert result["success"] is True
    assert result["provider"] == "duckduckgo"
    assert result["fallback_used"] is True


@pytest.mark.asyncio
async def test_explicit_web_provider_fails_closed_without_key(monkeypatch):
    import app.tools.web_search as module

    monkeypatch.setattr(module.settings, "WEB_SEARCH_PROVIDER", "brave")
    monkeypatch.setattr(module.settings, "BRAVE_SEARCH_API_KEY", None)

    result = await module.WebSearchTool().execute(
        {"query": "test query", "num_results": 3, "language": "en"},
        "user-1",
    )
    assert result["success"] is False
    assert result["provider"] is None
    assert "BRAVE_SEARCH_API_KEY" in result["error"]
