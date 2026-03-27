"""
ARC Platform — Prompt Injection Filter
Detects and blocks common prompt injection patterns before sending to LLM.
"""
from __future__ import annotations

import logging
import re

logger = logging.getLogger("arc.prompt_filter")

# ── Suspicious patterns ──────────────────────────────────────────────────────
_INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"ignore\s+(all\s+)?above\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?previous", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(a|an|the)\s+", re.IGNORECASE),
    re.compile(r"new\s+instructions?\s*:", re.IGNORECASE),
    re.compile(r"(?:^|\n)\s*system\s*:\s*", re.IGNORECASE),
    re.compile(r"<\s*system\s*>", re.IGNORECASE),
    re.compile(r"\[INST\]", re.IGNORECASE),
    re.compile(r"```\s*system", re.IGNORECASE),
    re.compile(r"override\s+(safety|instructions|rules)", re.IGNORECASE),
    re.compile(r"act\s+as\s+(if\s+you\s+are|a|an)", re.IGNORECASE),
    re.compile(r"pretend\s+(you\s+are|to\s+be)", re.IGNORECASE),
    re.compile(r"do\s+not\s+follow\s+(your|the)\s+(rules|instructions)", re.IGNORECASE),
    re.compile(r"reveal\s+(your|the)\s+(system|initial)\s+prompt", re.IGNORECASE),
    re.compile(r"output\s+your\s+(system|initial)\s+prompt", re.IGNORECASE),
]

# ── Dangerous content markers ────────────────────────────────────────────────
_DANGEROUS_TOKENS = [
    "os.system(",
    "subprocess.",
    "eval(",
    "exec(",
    "__import__(",
    "shutil.rmtree",
    "rm -rf",
    "format c:",
]


def check_prompt_injection(text: str) -> tuple[bool, str]:
    """
    Scan text for prompt injection patterns.

    Returns:
        (is_safe, reason)  — True if safe, False if injection detected.
    """
    if not text or not text.strip():
        return True, ""

    # Pattern matching
    for pattern in _INJECTION_PATTERNS:
        match = pattern.search(text)
        if match:
            reason = f"Prompt injection detected: matched pattern '{match.group()}'"
            logger.warning(reason)
            return False, reason

    # Token matching
    text_lower = text.lower()
    for token in _DANGEROUS_TOKENS:
        if token.lower() in text_lower:
            reason = f"Dangerous content detected: '{token}'"
            logger.warning(reason)
            return False, reason

    return True, ""


def sanitize_user_input(text: str) -> str:
    """Strip control characters, HTML tags, and normalise whitespace."""
    # Remove null bytes and other control chars (keep newlines/tabs)
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # Strip HTML tags to prevent XSS
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    return cleaned.strip()
