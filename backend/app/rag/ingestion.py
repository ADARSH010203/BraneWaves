"""
ARC Platform — Document Ingestion
Extracts text plus source provenance from uploaded documents.
"""
from __future__ import annotations

import io
import json
import logging
from typing import Any

logger = logging.getLogger("arc.rag.ingestion")

SUPPORTED_TYPES = {
    "text/plain": "txt",
    "text/markdown": "md",
    "text/csv": "csv",
    "application/json": "json",
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}


async def extract_document_segments(
    file_bytes: bytes,
    content_type: str,
    filename: str,
) -> list[dict[str, Any]]:
    """Return document text as provenance-preserving segments.

    Each segment contains text and source metadata. PDFs are segmented by page
    so downstream RAG citations can point to the exact page.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if content_type in ("text/plain", "text/markdown", "text/csv") or ext in ("txt", "md", "csv"):
        text = file_bytes.decode("utf-8", errors="replace")
        return [{"text": text, "segment_index": 1}] if text.strip() else []

    if content_type == "application/json" or ext == "json":
        try:
            data = json.loads(file_bytes.decode("utf-8"))
            text = json.dumps(data, indent=2)
        except json.JSONDecodeError:
            text = file_bytes.decode("utf-8", errors="replace")
        return [{"text": text, "segment_index": 1}] if text.strip() else []

    if content_type == "application/pdf" or ext == "pdf":
        return _extract_pdf_segments(file_bytes)

    if (
        content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        or ext == "docx"
    ):
        return _extract_docx_segments(file_bytes)

    try:
        text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        logger.warning("Could not extract text from %s (%s)", filename, content_type)
        return []
    return [{"text": text, "segment_index": 1}] if text.strip() else []


async def extract_text(file_bytes: bytes, content_type: str, filename: str) -> str:
    """Backward-compatible plain-text extraction used by existing callers/tests."""
    segments = await extract_document_segments(file_bytes, content_type, filename)
    return "\n\n".join(s["text"] for s in segments if s.get("text"))


def _extract_pdf_segments(file_bytes: bytes) -> list[dict[str, Any]]:
    """Extract PDF text page-by-page."""
    try:
        import pdfplumber

        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            segments = []
            for page_number, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                if text.strip():
                    segments.append({
                        "text": text,
                        "page_number": page_number,
                        "segment_index": page_number,
                    })
            return segments
    except ImportError:
        pass
    except Exception as exc:
        logger.warning("pdfplumber extraction failed; trying PyPDF2: %s", exc)

    try:
        from PyPDF2 import PdfReader

        reader = PdfReader(io.BytesIO(file_bytes))
        segments = []
        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                segments.append({
                    "text": text,
                    "page_number": page_number,
                    "segment_index": page_number,
                })
        return segments
    except ImportError:
        logger.warning("No PDF extraction library available")
    except Exception as exc:
        logger.error("PDF extraction failed: %s", exc)
    return []


def _extract_docx_segments(file_bytes: bytes) -> list[dict[str, Any]]:
    """Extract DOCX text without inventing rendered page numbers."""
    try:
        from docx import Document

        doc = Document(io.BytesIO(file_bytes))
        blocks: list[str] = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(c.text.strip() for c in row.cells if c.text.strip())
                if row_text:
                    blocks.append(row_text)
        text = "\n\n".join(blocks)
        return [{"text": text, "segment_index": 1}] if text.strip() else []
    except ImportError:
        logger.warning("python-docx not installed")
    except Exception as exc:
        logger.error("DOCX extraction failed: %s", exc)
    return []
