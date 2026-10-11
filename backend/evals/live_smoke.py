"""Live external-integration smoke checks."""
from __future__ import annotations

import asyncio
import json
import os

from app.agents.llm_client import chat_completion
from app.tools.dataset_search import DatasetSearchTool
from app.tools.paper_search import PaperSearchTool
from app.tools.python_sandbox import PythonSandboxTool
from app.tools.web_search import WebSearchTool


async def main() -> None:
    checks: dict[str, dict] = {}

    response = await chat_completion(
        messages=[{"role": "user", "content": "Reply with exactly: ARC_LLM_OK"}],
        temperature=0,
        max_tokens=32,
    )
    llm_text = (response.choices[0].message.content or "").strip()
    checks["groq_llm"] = {"ok": "ARC_LLM_OK" in llm_text, "response": llm_text[:120]}

    web = await WebSearchTool().execute(
        {"query": "OpenAI artificial intelligence research", "num_results": 3, "language": "en"},
        "live-smoke",
    )
    configured_primary = any(
        os.getenv(name)
        for name in ("BRAVE_SEARCH_API_KEY", "TAVILY_API_KEY", "SERPER_API_KEY")
    )
    provider = web.get("provider")
    checks["web_search"] = {
        "ok": bool(
            web.get("success")
            and web.get("results")
            and (not configured_primary or provider != "duckduckgo")
        ),
        "provider": provider,
        "fallback_used": web.get("fallback_used"),
        "count": len(web.get("results", [])),
        "error": web.get("error"),
    }

    papers = await PaperSearchTool().execute(
        {"query": "retrieval augmented generation", "num_results": 3, "year_from": 2023},
        "live-smoke",
    )
    checks["paper_search"] = {
        "ok": bool(papers.get("success") and papers.get("results")),
        "count": len(papers.get("results", [])),
        "error": papers.get("error"),
    }

    datasets = await DatasetSearchTool().execute(
        {"query": "question answering", "num_results": 3},
        "live-smoke",
    )
    checks["dataset_search"] = {
        "ok": bool(datasets.get("success") and datasets.get("results")),
        "count": len(datasets.get("results", [])),
        "error": datasets.get("error"),
    }

    if os.getenv("PYTHON_SANDBOX_URL"):
        sandbox = await PythonSandboxTool().execute(
            {"code": "print(6 * 7)", "timeout": 10},
            "live-smoke",
        )
        checks["python_sandbox"] = {
            "ok": bool(sandbox.get("success") and "42" in sandbox.get("output", "")),
            "error": sandbox.get("error"),
        }
    else:
        checks["python_sandbox"] = {
            "ok": True,
            "skipped": True,
            "reason": "PYTHON_SANDBOX_URL not configured; planner capability gating must disable code steps.",
        }

    print(json.dumps(checks, indent=2))
    failed = [name for name, result in checks.items() if not result.get("ok")]
    if failed:
        raise SystemExit(f"Live integration smoke failed: {', '.join(failed)}")


if __name__ == "__main__":
    asyncio.run(main())
