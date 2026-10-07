"""
ARC Platform — Citation Verification Tool
Verifies citations by checking URL accessibility and content matching.
"""
from __future__ import annotations

from typing import Any

import ipaddress
import socket
from urllib.parse import urlparse
import httpx
from pydantic import Field

from app.tools.base import BaseTool, ToolInput


def is_safe_url(url: str) -> bool:
    """Validate that URL does not point to internal/private networks or cloud metadata."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        # Block cloud metadata hosts explicitly
        if hostname in ("169.254.169.254", "metadata.google.internal", "localhost", "127.0.0.1"):
            return False
        # Validate every currently resolved address, not only the first A record.
        # Redirects are disabled below, so each verified request has one checked host.
        addresses = {
            item[4][0]
            for item in socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
        }
        if not addresses:
            return False
        for address in addresses:
            ip = ipaddress.ip_address(address)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return False
        return True
    except Exception:
        return False


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

        if not is_safe_url(url):
            return {
                "success": False,
                "url": url,
                "accessible": False,
                "error": "URL blocked: internal, private, or invalid host destination.",
                "verification_score": 0.0,
                "verified": False,
            }

        try:
            async with httpx.AsyncClient(
                timeout=15,
                follow_redirects=False,
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
