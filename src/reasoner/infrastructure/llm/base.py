"""Base LLM provider abstraction and exceptions."""

from __future__ import annotations

import asyncio
import logging
import random
from abc import ABC, abstractmethod

from reasoner.exceptions import (
    ARAError,
    is_retryable,
)
from reasoner.core.constants import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
)

logger = logging.getLogger(__name__)


class LLMError(ARAError):
    """Raised when an LLM call fails after all retries."""
    retryable = False


class BaseLLMProvider(ABC):
    def __init__(self, model: str, max_retries: int = 3) -> None:
        self.model = model
        self.max_retries = max_retries

    @abstractmethod
    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
    ) -> str: ...

    async def complete_with_retry(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> str:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return await self.complete(
                    system_prompt, user_prompt, max_tokens, temperature
                )
            except Exception as exc:
                last_error = exc
                # Don't retry non-retryable errors
                if not is_retryable(exc):
                    raise
                if attempt < self.max_retries:
                    await asyncio.sleep(min(2 ** attempt, 4) + random.uniform(0, 0.5))
        raise LLMError(
            f"{self.__class__.__name__}({self.model}) failed "
            f"after {self.max_retries} retries: {last_error}"
        ) from last_error
