"""
Centralized environment-aware settings.

This is the ONLY module in the project that reads from the process environment
and loads the .env file. It uses a guard so that `load_dotenv` is executed at
most once, even if the module is imported multiple times.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    _dotenv_loaded = False

    def _ensure_dotenv() -> None:
        global _dotenv_loaded
        if not _dotenv_loaded:
            # override=True ensures the .env file is the authoritative source
            # and that updating the file is reflected without restarting the shell.
            load_dotenv(Path(__file__).parent.parent.parent.parent / ".env", override=True)
            _dotenv_loaded = True

    _ensure_dotenv()
except ImportError:
    pass


class Settings:
    """Application settings derived from environment variables."""

    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    RATE_LIMIT_PER_HOUR: int = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))
    RATE_LIMIT_BURST: int = int(os.getenv("RATE_LIMIT_BURST", "10"))
    MEMORY_LIMIT_MB: int = int(os.getenv("MEMORY_LIMIT_MB", "1024"))
    MEMORY_WARNING_MB: int = int(os.getenv("MEMORY_WARNING_MB", "768"))
    REQUEST_TIMEOUT_SECONDS: float = float(
        os.getenv("REQUEST_TIMEOUT_SECONDS", "300.0")
    )
    OPENROUTER_API_KEY: str | None = os.getenv("OPENROUTER_API_KEY")
    PERPLEXITY_API_KEY: str | None = os.getenv("PERPLEXITY_API_KEY")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    SEARXNG_URL: str = os.getenv("SEARXNG_URL", "http://localhost:8888")
    ADMIN_API_KEY: str | None = os.getenv("ADMIN_API_KEY")
    REASONER_DEEP_READ_LLM: bool = os.getenv("REASONER_DEEP_READ_LLM", "1") != "0"

    # ── Cohere Rerank (via OpenRouter) ──
    COHERE_RERANK_ENABLED: bool = os.getenv("COHERE_RERANK_ENABLED", "true").lower() in ("1", "true", "yes")
    COHERE_RERANK_MODEL: str = os.getenv("COHERE_RERANK_MODEL", "cohere/rerank-4-fast")

    # ── Document Semantic Retrieval (Phase 4, opt-in) ──
    DOCUMENT_SEMANTIC_RETRIEVAL_ENABLED: bool = os.getenv("DOCUMENT_SEMANTIC_RETRIEVAL_ENABLED", "false").lower() in ("1", "true", "yes")
    DOCUMENT_CHUNK_SIZE: int = int(os.getenv("DOCUMENT_CHUNK_SIZE", "1000"))
    DOCUMENT_CHUNK_OVERLAP: int = int(os.getenv("DOCUMENT_CHUNK_OVERLAP", "200"))
    DOCUMENT_MAX_CHUNKS_PER_FILE: int = int(os.getenv("DOCUMENT_MAX_CHUNKS_PER_FILE", "500"))

    # ── Server bind configuration ──
    SERVER_HOST: str = os.getenv("SERVER_HOST", "127.0.0.1")
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8000"))
    UVICORN_HOST: str = os.getenv("UVICORN_HOST", "0.0.0.0")

    # ── CORS ──
    CORS_ORIGINS: str = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:8001,http://127.0.0.1:8001"
    )

    # ── OpenRouter analytics headers ──
    OPENROUTER_HTTP_REFERER: str = os.getenv(
        "OPENROUTER_HTTP_REFERER", "https://github.com/Reasoner"
    )
    OPENROUTER_APP_TITLE: str = os.getenv("OPENROUTER_APP_TITLE", "Reasoner")

    @property
    def internal_api_base_url(self) -> str:
        """Base URL for internal self-calls (e.g., Neuro endpoints from streaming)."""
        return f"http://{self.SERVER_HOST}:{self.SERVER_PORT}"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS env var into a list of origin strings."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
