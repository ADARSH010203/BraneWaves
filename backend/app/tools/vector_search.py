"""
ARC Platform — Vector Search Tool
Searches the RAG vector store for relevant document chunks.
"""
from __future__ import annotations

from typing import Any

from pydantic import Field

from app.tools.base import BaseTool, ToolInput


class VectorSearchInput(ToolInput):
    """Input schema for vector search."""
    query: str = Field(min_length=1, max_length=1000, description="Search query")
    user_id: str = Field(description="User ID for namespace isolation")
    top_k: int = Field(default=10, ge=1, le=50, description="Number of results")
    min_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Minimum relevance score")


class VectorSearchTool(BaseTool):
    """Searches the RAG vector store for relevant chunks."""

    name = "vector_search"
    description = "Search the knowledge base for relevant document chunks"
    input_schema = VectorSearchInput
    timeout_seconds = 15
    cost_estimate_usd = 0.0002
    permission_scope = "basic"

    async def execute(self, params: dict[str, Any], user_id: str) -> dict[str, Any]:
        from app.rag.retriever import retrieve_chunks

        query = params["query"]
        top_k = params.get("top_k", 10)
        min_score = params.get("min_score", 0.5)

        try:
            chunks = await retrieve_chunks(
                query=query,
                user_id=user_id,
                top_k=top_k,
                min_score=min_score,
            )

            return {
                "success": True,
                "results": chunks,
                "query": query,
                "total_results": len(chunks),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "results": [],
                "query": query,
                "total_results": 0,
            }
