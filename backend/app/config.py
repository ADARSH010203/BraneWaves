"""
ARC Platform — Configuration
Pydantic-settings based config with env var support.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, MongoDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
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
    JWT_SECRET_KEY: str = "CHANGE-ME-IN-PRODUCTION-32-byte-min"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Groq / LLM ──────────────────────────────────────────────────────
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"

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

    # ── Tool Timeouts (seconds) ──────────────────────────────────────────
    TOOL_TIMEOUT_WEB_SEARCH: int = 30
    TOOL_TIMEOUT_PAPER_SEARCH: int = 30
    TOOL_TIMEOUT_DATASET_SEARCH: int = 30
    TOOL_TIMEOUT_PYTHON_SANDBOX: int = 60
    TOOL_TIMEOUT_VECTOR_SEARCH: int = 15
    TOOL_TIMEOUT_CITATION_VERIFY: int = 20


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
