"""
ARC Platform — RAG Retriever
Vector search with FAISS indexing, per-user namespace isolation, and citation tracing.
Uses FAISS for ~100x faster similarity search vs naive numpy loops.
Falls back to numpy if FAISS is not available.
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

from app.config import get_settings
from app.database import get_db
from app.rag.embeddings import generate_embedding

logger = logging.getLogger("arc.rag.retriever")
settings = get_settings()

# Try to import FAISS for fast vector search
try:
    import faiss
    _HAS_FAISS = True
    logger.info("FAISS available — using accelerated vector search")
except ImportError:
    _HAS_FAISS = False
    logger.warning("FAISS not installed — falling back to numpy cosine similarity")


async def retrieve_chunks(
    query: str,
    user_id: str,
    top_k: int = 10,
    min_score: float = 0.5,
    file_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Retrieve relevant document chunks using vector similarity search.

    Per-user namespace isolation: only searches chunks belonging to user_id.
    Uses FAISS IndexFlatIP when available (~100x faster), falls back to numpy.
    Returns chunks sorted by relevance score.
    """
    db = get_db()

    # Generate query embedding
    query_embedding = await generate_embedding(query)

    # Build filter
    filter_query: dict[str, Any] = {"user_id": user_id}
    if file_ids:
        filter_query["file_id"] = {"$in": file_ids}

    # Fetch candidate chunks
    cursor = db.chunks.find(
        filter_query,
        {"_id": 1, "text": 1, "file_id": 1, "embedding": 1, "metadata": 1, "index": 1},
    )
    candidates = await cursor.to_list(length=10000)

    if not candidates:
        return []

    # Filter out chunks without embeddings
    valid_candidates = [c for c in candidates if c.get("embedding") and len(c["embedding"]) > 0]
    if not valid_candidates:
        return []

    if _HAS_FAISS:
        results = _search_faiss(query_embedding, valid_candidates, top_k, min_score)
    else:
        results = _search_numpy(query_embedding, valid_candidates, top_k, min_score)

    logger.info(
        "Retrieved %d chunks (from %d candidates) for user %s, query: %s...",
        len(results), len(valid_candidates), user_id, query[:50],
    )
    return results


def _search_faiss(
    query_embedding: list[float],
    candidates: list[dict],
    top_k: int,
    min_score: float,
) -> list[dict[str, Any]]:
    """FAISS-accelerated similarity search using Inner Product (cosine on normalized vectors)."""
    dim = len(query_embedding)

    # Build embedding matrix and normalize
    embeddings = np.array([c["embedding"] for c in candidates], dtype=np.float32)
    faiss.normalize_L2(embeddings)

    query_vec = np.array([query_embedding], dtype=np.float32)
    faiss.normalize_L2(query_vec)

    # Build FAISS index (Inner Product = cosine similarity on normalized vectors)
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    # Search
    k = min(top_k, len(candidates))
    scores, indices = index.search(query_vec, k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0 or score < min_score:
            continue
        chunk = candidates[idx]
        results.append({
            "chunk_id": chunk["_id"],
            "text": chunk["text"],
            "file_id": chunk["file_id"],
            "score": round(float(score), 4),
            "index": chunk.get("index", 0),
            "metadata": chunk.get("metadata", {}),
        })

    return results


def _search_numpy(
    query_embedding: list[float],
    candidates: list[dict],
    top_k: int,
    min_score: float,
) -> list[dict[str, Any]]:
    """Fallback numpy cosine similarity search."""
    query_vec = np.array(query_embedding)
    scored: list[tuple[float, dict]] = []

    for chunk in candidates:
        chunk_vec = np.array(chunk["embedding"])
        similarity = float(np.dot(query_vec, chunk_vec) / (
            np.linalg.norm(query_vec) * np.linalg.norm(chunk_vec) + 1e-10
        ))
        if similarity >= min_score:
            scored.append((similarity, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    for score, chunk in scored[:top_k]:
        results.append({
            "chunk_id": chunk["_id"],
            "text": chunk["text"],
            "file_id": chunk["file_id"],
            "score": round(score, 4),
            "index": chunk.get("index", 0),
            "metadata": chunk.get("metadata", {}),
        })

    return results
