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
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    SEARXNG_URL: str = os.getenv("SEARXNG_URL", "http://localhost:8888")
    ADMIN_API_KEY: str | None = os.getenv("ADMIN_API_KEY")
    REASONER_DEEP_READ_LLM: bool = os.getenv("REASONER_DEEP_READ_LLM", "1") != "0"


settings = Settings()
