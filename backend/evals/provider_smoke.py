"""Live network smoke checks for research providers that do not require Groq."""
from __future__ import annotations

import asyncio
import json

from app.tools.dataset_search import DatasetSearchTool
from app.tools.paper_search import PaperSearchTool
from app.tools.web_search import WebSearchTool


async def main() -> None:
    checks: dict[str, dict] = {}

    web = await WebSearchTool().execute(
        {"query": "OpenAI artificial intelligence research", "num_results": 3, "language": "en"},
        "provider-smoke",
    )
    checks["web_search"] = {
        "ok": bool(web.get("success") and web.get("results")),
        "provider": web.get("provider"),
        "fallback_used": web.get("fallback_used"),
        "count": len(web.get("results", [])),
        "error": web.get("error"),
    }

    papers = await PaperSearchTool().execute(
        {"query": "retrieval augmented generation", "num_results": 3, "year_from": 2023},
        "provider-smoke",
    )
    checks["paper_search"] = {
        "ok": bool(papers.get("success") and papers.get("results")),
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
