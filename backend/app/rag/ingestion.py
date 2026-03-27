"""
ARC Platform — Document Ingestion
Extracts text from uploaded files for RAG processing.
"""
from __future__ import annotations

import io
import logging
from typing import Any

logger = logging.getLogger("arc.rag.ingestion")

# Supported content types
SUPPORTED_TYPES = {
    "text/plain": "txt",
    "text/markdown": "md",
    "text/csv": "csv",
    "application/json": "json",
    "application/pdf": "pdf",
}


async def extract_text(file_bytes: bytes, content_type: str, filename: str) -> str:
    """
    Extract text content from file bytes based on content type.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    # Plain text formats
    if content_type in ("text/plain", "text/markdown", "text/csv") or ext in ("txt", "md", "csv"):
        return file_bytes.decode("utf-8", errors="replace")

    # JSON
    if content_type == "application/json" or ext == "json":
        import json
        try:
            data = json.loads(file_bytes.decode("utf-8"))
            return json.dumps(data, indent=2)
        except json.JSONDecodeError:
            return file_bytes.decode("utf-8", errors="replace")

    # PDF
    if content_type == "application/pdf" or ext == "pdf":
        return _extract_pdf(file_bytes)

    # Fallback: try as text
    try:
        return file_bytes.decode("utf-8", errors="replace")
    except Exception:
        logger.warning("Could not extract text from %s (%s)", filename, content_type)
        return ""


def _extract_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF bytes using PyPDF2 or pdfplumber."""
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
            return "\n\n".join(pages)
    except ImportError:
        pass

    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(file_bytes))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n\n".join(pages)
    except ImportError:
        logger.warning("No PDF library available. Install pdfplumber or PyPDF2.")
        return "[PDF content - extraction library not available]"
