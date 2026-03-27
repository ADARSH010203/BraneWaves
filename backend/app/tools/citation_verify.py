"""
ARC Platform — Citation Verification Tool
Verifies citations by checking URL accessibility and content matching.
"""
from __future__ import annotations

from typing import Any

import httpx
from pydantic import Field

from app.tools.base import BaseTool, ToolInput


class CitationVerifyInput(ToolInput):
    """Input schema for citation verification."""
    url: str = Field(description="URL to verify")
    expected_title: str = Field(default="", description="Expected page title")
    expected_content: str = Field(default="", description="Expected content snippet")


class CitationVerifyTool(BaseTool):
    """Verifies that a citation URL is accessible and content matches."""

    name = "citation_verify"
    description = "Verify that a citation URL is valid and content matches"
    input_schema = CitationVerifyInput
    timeout_seconds = 20
    cost_estimate_usd = 0.0001
    permission_scope = "basic"

    async def execute(self, params: dict[str, Any], user_id: str) -> dict[str, Any]:
        url = params["url"]
        expected_title = params.get("expected_title", "")
        expected_content = params.get("expected_content", "")

        try:
            async with httpx.AsyncClient(
                timeout=15,
                follow_redirects=True,
                headers={"User-Agent": "ARC-CitationBot/1.0"},
            ) as client:
                resp = await client.get(url)

            accessible = resp.status_code < 400
            content = resp.text[:5000] if accessible else ""

            # Check title match
            title_match = False
            if expected_title and accessible:
                title_match = expected_title.lower() in content.lower()

            # Check content match
            content_match = False
            if expected_content and accessible:
                content_match = expected_content.lower() in content.lower()

            verification_score = 0.0
            if accessible:
                verification_score += 0.5
            if title_match:
                verification_score += 0.25
            if content_match:
                verification_score += 0.25

            return {
                "success": True,
                "url": url,
                "accessible": accessible,
                "status_code": resp.status_code,
                "title_match": title_match,
                "content_match": content_match,
                "verification_score": verification_score,
                "verified": verification_score >= 0.5,
            }

        except Exception as e:
            return {
                "success": False,
                "url": url,
                "accessible": False,
                "error": str(e),
                "verification_score": 0.0,
                "verified": False,
            }
