"""
ARC Platform — Vector Search Tool
Searches the authenticated knowledge-base namespace.
"""
from __future__ import annotations

from typing import Any

from pydantic import Field

from app.tools.base import BaseTool, ToolInput


class VectorSearchInput(ToolInput):
    """Input schema for vector search."""
    query: str = Field(min_length=1, max_length=1000, description="Search query")
    file_ids: list[str] = Field(default_factory=list, max_length=50, description="Optional allowed knowledge-base file IDs")
    top_k: int = Field(default=10, ge=1, le=50, description="Number of results")
    min_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Minimum relevance score")


class VectorSearchTool(BaseTool):
    """Searches indexed knowledge-base chunks for the authenticated user."""

    name = "vector_search"
    description = "Search the authenticated knowledge base for relevant document chunks"
    input_schema = VectorSearchInput
    timeout_seconds = 15
    cost_estimate_usd = 0.0002
    permission_scope = "basic"

    async def execute(self, params: dict[str, Any], user_id: str) -> dict[str, Any]:
        from app.database import get_db
        from app.rag.retriever import retrieve_chunks

        query = params["query"]
        top_k = params.get("top_k", 10)
        min_score = params.get("min_score", 0.5)
        requested_file_ids = [str(v) for v in params.get("file_ids", []) if v]

        db = get_db()
        file_query: dict[str, Any] = {
            "user_id": user_id,
            "task_id": "KNOWLEDGE_BASE",
            "is_indexed": True,
        }
        if requested_file_ids:
            file_query["_id"] = {"$in": requested_file_ids}

        docs = await db.files.find(file_query, {"_id": 1}).to_list(length=50)
        allowed_file_ids = [str(doc["_id"]) for doc in docs]

        if requested_file_ids and set(allowed_file_ids) != set(requested_file_ids):
            return {
                "success": False,
                "error": "One or more requested files are unavailable or not owned by the authenticated user",
                "results": [],
                "query": query,
                "total_results": 0,
            }

        if not allowed_file_ids:
            return {"success": True, "results": [], "query": query, "total_results": 0}

        try:
            chunks = await retrieve_chunks(
                query=query,
                user_id=user_id,
                top_k=top_k,
                min_score=min_score,
                file_ids=allowed_file_ids,
            )
            return {
                "success": True,
                "results": chunks,
                "query": query,
                "total_results": len(chunks),
            }
        except Exception as exc:
            return {
                "success": False,
                "error": str(exc),
                "results": [],
                "query": query,
                "total_results": 0,
            }
