"""Persistent report-chat retrieval and conversation history."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np

from app.rag.chunker import chunk_text
from app.rag.embeddings import generate_embedding, generate_embeddings_batch


async def index_report_for_chat(db, report: dict[str, Any]) -> int:
    """Chunk/embed a report once for semantic follow-up retrieval."""
    report_id = str(report["_id"])
    user_id = str(report["user_id"])
    task_id = str(report["task_id"])
    content = report.get("content", "")
    if not content.strip():
        return 0

    chunks = chunk_text(content, chunk_size=1200, chunk_overlap=160, metadata={"report_id": report_id})
    if not chunks:
        return 0

    embeddings = await generate_embeddings_batch([c["text"] for c in chunks])
    docs = [
        {
            "_id": str(uuid.uuid4()),
            "user_id": user_id,
            "task_id": task_id,
            "report_id": report_id,
            "text": chunk["text"],
            "embedding": embedding,
            "index": chunk["index"],
            "created_at": datetime.now(timezone.utc),
        }
        for chunk, embedding in zip(chunks, embeddings)
    ]
    await db.report_chunks.delete_many({"report_id": report_id, "user_id": user_id})
    if docs:
        await db.report_chunks.insert_many(docs)
    return len(docs)


async def ensure_report_index(db, report: dict[str, Any]) -> None:
    report_id = str(report["_id"])
    exists = await db.report_chunks.find_one({"report_id": report_id}, {"_id": 1})
    if not exists:
        await index_report_for_chat(db, report)


async def retrieve_report_context(
    db,
    report: dict[str, Any],
    query: str,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Retrieve semantically relevant report chunks for a question."""
    await ensure_report_index(db, report)
    candidates = await db.report_chunks.find(
        {"report_id": str(report["_id"]), "user_id": str(report["user_id"])},
        {"_id": 1, "text": 1, "embedding": 1, "index": 1},
    ).to_list(length=None)
    if not candidates:
        return []

    query_vec = np.array(await generate_embedding(query), dtype=np.float32)
    scored: list[tuple[float, dict[str, Any]]] = []
    for chunk in candidates:
        emb = chunk.get("embedding")
        if not emb:
            continue
        vec = np.array(emb, dtype=np.float32)
        score = float(np.dot(query_vec, vec) / (np.linalg.norm(query_vec) * np.linalg.norm(vec) + 1e-10))
        scored.append((score, chunk))
    scored.sort(key=lambda item: item[0], reverse=True)

    return [
        {
            "chunk_id": str(chunk["_id"]),
            "index": int(chunk.get("index", 0)),
            "text": chunk.get("text", ""),
            "score": round(score, 4),
        }
        for score, chunk in scored[:top_k]
    ]


async def get_chat_history(db, user_id: str, task_id: str, limit: int = 30) -> list[dict[str, Any]]:
    rows = await db.report_chats.find(
        {"user_id": user_id, "task_id": task_id},
        {"_id": 0, "role": 1, "content": 1, "created_at": 1},
    ).sort("created_at", -1).limit(limit).to_list(length=limit)
    rows.reverse()
    return rows


async def save_chat_message(db, user_id: str, task_id: str, role: str, content: str) -> None:
    await db.report_chats.insert_one({
        "_id": str(uuid.uuid4()),
        "user_id": user_id,
        "task_id": task_id,
        "role": role,
        "content": content,
        "created_at": datetime.now(timezone.utc),
    })
