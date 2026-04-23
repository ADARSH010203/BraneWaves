"""
ARC Platform — Text Chunker
Recursive text splitter with configurable size and overlap.
"""
from __future__ import annotations

import uuid
from typing import Any

from app.config import get_settings

settings = get_settings()


def chunk_text(
    text: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Split text into overlapping chunks with metadata.

    Returns list of dicts with: id, text, index, metadata.
    """
    chunk_size = chunk_size or settings.CHUNK_SIZE
    chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
    metadata = metadata or {}

    if not text or not text.strip():
        return []

    # Split by paragraphs first, then by sentences, then by characters
    chunks = []
    separators = ["\n\n", "\n", ". ", " "]

    segments = _recursive_split(text, separators, chunk_size)

    # Create overlapping chunks
    current_chunk = ""
    chunk_list: list[str] = []

    for segment in segments:
        if len(current_chunk) + len(segment) <= chunk_size:
            current_chunk += segment
        else:
            if current_chunk.strip():
                chunk_list.append(current_chunk.strip())
            # Start new chunk with overlap from previous
            overlap_text = current_chunk[-chunk_overlap:] if chunk_overlap else ""
            current_chunk = overlap_text + segment

    if current_chunk.strip():
        chunk_list.append(current_chunk.strip())

    # Build chunk documents
    for i, chunk_str in enumerate(chunk_list):
        chunks.append({
            "id": str(uuid.uuid4()),
            "text": chunk_str,
            "index": i,
            "char_count": len(chunk_str),
            "word_count": len(chunk_str.split()),
            "metadata": {
                **metadata,
                "chunk_index": i,
                "total_chunks": len(chunk_list),
            },
        })

    return chunks


def _recursive_split(text: str, separators: list[str], max_size: int) -> list[str]:
    """Recursively split text using a hierarchy of separators."""
    if len(text) <= max_size:
        return [text]

    if not separators:
        # Last resort: split by character count
        return [text[i:i+max_size] for i in range(0, len(text), max_size)]

    sep = separators[0]
    parts = text.split(sep)

    result = []
    for part in parts:
        if len(part) <= max_size:
            result.append(part + sep)
        else:
            result.extend(_recursive_split(part, separators[1:], max_size))

    return result
