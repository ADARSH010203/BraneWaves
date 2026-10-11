"""Live network smoke checks for research providers."""
from __future__ import annotations

import asyncio
import json
import os

from app.tools.dataset_search import DatasetSearchTool
from app.tools.paper_search import PaperSearchTool
from app.tools.web_search import WebSearchTool


async def main() -> None:
    checks: dict[str, dict] = {}

    has_production_search = any(
        os.getenv(name)
        for name in ("BRAVE_SEARCH_API_KEY", "TAVILY_API_KEY", "SERPER_API_KEY")
    )
    if has_production_search:
        web = await WebSearchTool().execute(
            {"query": "OpenAI artificial intelligence research", "num_results": 3, "language": "en"},
            "provider-smoke",
        )
        checks["web_search"] = {
            "ok": bool(
                web.get("success")
                and web.get("results")
                and web.get("provider") != "duckduckgo"
            ),
            "provider": web.get("provider"),
            "fallback_used": web.get("fallback_used"),
            "count": len(web.get("results", [])),
            "error": web.get("error"),
        }
    else:
        checks["web_search"] = {
            "ok": True,
            "skipped": True,
            "reason": (
                "No Brave/Tavily/Serper repository secret configured. "
                "DuckDuckGo remains a development fallback, not the production verification target."
            ),
        }

    papers = await PaperSearchTool().execute(
        {"query": "retrieval augmented generation", "num_results": 3, "year_from": 2023},
        "provider-smoke",
    )
    checks["paper_search"] = {
        "ok": bool(papers.get("success") and papers.get("results")),
        "provider": papers.get("provider"),
        "fallback_used": papers.get("fallback_used"),
        "count": len(papers.get("results", [])),
        "error": papers.get("error"),
    }

    datasets = await DatasetSearchTool().execute(
        {"query": "question answering", "num_results": 3},
        "provider-smoke",
    )
    checks["dataset_search"] = {
        "ok": bool(datasets.get("success") and datasets.get("results")),
        "count": len(datasets.get("results", [])),
        "error": datasets.get("error"),
    }

    print(json.dumps(checks, indent=2))
    failed = [name for name, result in checks.items() if not result.get("ok")]
    if failed:
        raise SystemExit(f"Provider smoke failed: {', '.join(failed)}")


if __name__ == "__main__":
    asyncio.run(main())
