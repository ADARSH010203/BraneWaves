"""
ARC Platform — Configuration
Pydantic-settings based config with env var support.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from pydantic import Field, MongoDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────
    APP_NAME: str = "ARC — Agentic Research & Work Copilot"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    LOG_LEVEL: str = "INFO"
    ALLOWED_ORIGINS: list[str] = Field(default=["http://localhost:3000"])

    # ── MongoDB ──────────────────────────────────────────────────────────
    MONGO_URI: MongoDsn = Field(default="mongodb://localhost:27017")  # type: ignore[assignment]
    MONGO_DB_NAME: str = "arc_db"

    # ── Redis ────────────────────────────────────────────────────────────
    REDIS_URL: RedisDsn = Field(default="redis://localhost:6379/0")  # type: ignore[assignment]

    # ── JWT / Auth ───────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: Literal["HS256"] = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Groq / LLM (Groq-only — no other provider keys needed) ─────────
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-20b"
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    LLM_FALLBACK_ROUTING: list[str] = Field(
        default=[
            "groq/openai/gpt-oss-20b",
            "groq/openai/gpt-oss-120b",
        ]
    )
    FALLBACK_LLM_PROVIDER: str = "groq"
    FALLBACK_LLM_MODEL: str = "openai/gpt-oss-120b"
    EVAL_LLM_PROVIDER: str = "groq"
    EVAL_LLM_MODEL: str = "openai/gpt-oss-20b"

    # ── Critic Settings ────────────────────────────────────────────────────────
    CRITIC_CONFIDENCE_THRESHOLD: float = 0.45


    # ── Embeddings (local sentence-transformers, Groq has no embedding API)
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSIONS: int = 384

    # ── Cost & Limits ────────────────────────────────────────────────────
    MAX_TASK_BUDGET_USD: float = 5.00
    MAX_AGENT_BUDGET_USD: float = 1.00
    MAX_STEPS_PER_TASK: int = 50
    MAX_RETRIES_PER_STEP: int = 3
    MAX_FILE_SIZE_MB: int = 50
    RATE_LIMIT_PER_MINUTE: int = 60

    # ── RAG ──────────────────────────────────────────────────────────────
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64
    RAG_TOP_K: int = 10

    # ── Caching ──────────────────────────────────────────────────────────
    CACHE_TTL_SECONDS: int = 3600
    ENABLE_AGENT_CACHE: bool = True

    # ── Tool Timeouts (seconds) ──────────────────────────────────────────
    TOOL_TIMEOUT_WEB_SEARCH: int = 30
    TOOL_TIMEOUT_PAPER_SEARCH: int = 30
    TOOL_TIMEOUT_DATASET_SEARCH: int = 30
    TOOL_TIMEOUT_PYTHON_SANDBOX: int = 60
    TOOL_TIMEOUT_VECTOR_SEARCH: int = 15
    TOOL_TIMEOUT_CITATION_VERIFY: int = 20

    # ── Isolated code execution ─────────────────────────────────────────
    # Point this at a separately isolated sandbox service. Local host subprocess
    # execution is intentionally disabled because it is not a security boundary.
    PYTHON_SANDBOX_URL: str | None = None
    PYTHON_SANDBOX_API_KEY: str | None = None

    # ── OAuth ────────────────────────────────────────────────────────────
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GITHUB_CLIENT_ID: str | None = None
    GITHUB_CLIENT_SECRET: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    s = Settings()
    if s.GROQ_API_KEY:
        os.environ["GROQ_API_KEY"] = s.GROQ_API_KEY
    if s.GROQ_BASE_URL:
        os.environ["GROQ_BASE_URL"] = s.GROQ_BASE_URL
    return s
