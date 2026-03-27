"""Tests for RAG — chunker, ingestion."""
import pytest
from app.rag.chunker import chunk_text
from app.rag.ingestion import extract_text


class TestChunker:
    def test_basic_chunking(self):
        text = "Hello world. " * 200
        chunks = chunk_text(text, chunk_size=100, chunk_overlap=20)
        assert len(chunks) > 1
        assert all(c["text"] for c in chunks)
        assert all(c["id"] for c in chunks)

    def test_empty_text(self):
        chunks = chunk_text("")
        assert len(chunks) == 0

    def test_metadata_propagation(self):
        chunks = chunk_text("Short text", metadata={"file_id": "f1"})
        if chunks:
            assert chunks[0]["metadata"]["file_id"] == "f1"


class TestIngestion:
    @pytest.mark.asyncio
    async def test_extract_plain_text(self):
        text = await extract_text(b"Hello World", "text/plain", "test.txt")
        assert text == "Hello World"

    @pytest.mark.asyncio
    async def test_extract_json(self):
        text = await extract_text(b'{"key": "value"}', "application/json", "test.json")
        assert "key" in text
