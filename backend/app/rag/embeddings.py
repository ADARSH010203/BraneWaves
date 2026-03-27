"""
ARC Platform — Embeddings
Generate embeddings using sentence-transformers (local) and store in MongoDB.
Groq does not provide an embedding API, so we use local models.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.config import get_settings
from app.database import get_db

logger = logging.getLogger("arc.rag.embeddings")
settings = get_settings()

_model = None


def _get_model():
    """Lazy-load the sentence-transformers model."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
        logger.info("Loaded embedding model: %s", settings.EMBEDDING_MODEL)
    return _model


async def generate_embedding(text: str) -> list[float]:
    """Generate an embedding vector for a single text (runs model in thread pool)."""
    model = _get_model()
    loop = asyncio.get_event_loop()
    embedding = await loop.run_in_executor(None, lambda: model.encode(text).tolist())
    return embedding


async def generate_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a batch of texts."""
    model = _get_model()
    loop = asyncio.get_event_loop()
    embeddings = await loop.run_in_executor(None, lambda: model.encode(texts).tolist())
    return embeddings


async def store_chunks_with_embeddings(
    chunks: list[dict[str, Any]],
    user_id: str,
    file_id: str,
) -> list[str]:
    """
    Generate embeddings for chunks and store in MongoDB.
    Returns list of stored chunk IDs.
    """
    db = get_db()
    texts = [c["text"] for c in chunks]

    # Generate embeddings in batches of 100
    all_embeddings = []
    for i in range(0, len(texts), 100):
        batch = texts[i:i+100]
        embeddings = await generate_embeddings_batch(batch)
        all_embeddings.extend(embeddings)

    # Store in MongoDB with embeddings
    chunk_ids = []
    docs = []
    for chunk, embedding in zip(chunks, all_embeddings):
        doc = {
            "_id": chunk["id"],
            "user_id": user_id,
            "file_id": file_id,
            "text": chunk["text"],
            "embedding": embedding,
            "index": chunk["index"],
            "char_count": chunk["char_count"],
            "word_count": chunk["word_count"],
            "metadata": chunk.get("metadata", {}),
        }
        docs.append(doc)
        chunk_ids.append(chunk["id"])

    if docs:
        await db.chunks.insert_many(docs)
        logger.info("Stored %d chunks with embeddings for file %s", len(docs), file_id)

    return chunk_ids
