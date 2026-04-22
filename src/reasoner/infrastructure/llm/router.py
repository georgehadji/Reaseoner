"""Provider router with fallback logic."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from reasoner.core.constants import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
)
from reasoner.infrastructure.llm.base import BaseLLMProvider, LLMError
from reasoner.infrastructure.llm.registry import build_provider

logger = logging.getLogger(__name__)


class ProviderRouter:
    """
    Routes pipeline phases to appropriate providers.
    Falls back to primary for any unspecified role.
    """

    def __init__(
        self,
        primary: BaseLLMProvider,
        routing_table: dict[str, BaseLLMProvider] | None = None,
        fallback_table: dict[str, BaseLLMProvider] | None = None,
        verbose: bool = False,
    ) -> None:
        self.primary = primary
        self.routing_table: dict[str, BaseLLMProvider] = routing_table or {}
        # Explicit per-role fallbacks. Roles absent here fall back to primary automatically.
        self.fallback_table: dict[str, BaseLLMProvider] = fallback_table or {}
        self.verbose = verbose

    def get(self, role: str) -> BaseLLMProvider:
        provider = self.routing_table.get(role)
        if provider is None:
            if role != "primary" and self.verbose:
                logger.warning(
                    "Role '%s' not found in routing table — falling back to primary '%s'. "
                    "Check preset routing configuration.",
                    role, self.primary.model
                )
            return self.primary
        return provider

    async def call(
        self,
        role: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        timeout_seconds: float | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """
        Call LLM for role. On LLMError or timeout, tries a fallback provider:
          1. Explicit fallback from fallback_table (if defined and different)
          2. Primary (if role was using a non-primary model)
          3. Re-raises original error if no fallback available

        Returns:
            Tuple of (response_text, metadata_dict)
            metadata includes: input tokens, output tokens, cost (if available)
        """
        assigned = self.get(role)

        async def _call(provider: BaseLLMProvider) -> str:
            coro = provider.complete_with_retry(system_prompt, user_prompt, max_tokens, temperature)
            if timeout_seconds is not None:
                return await asyncio.wait_for(coro, timeout=timeout_seconds)
            return await coro

        # Resolve fallback provider (explicit beats automatic primary fallback)
        explicit = self.fallback_table.get(role)
        if explicit and explicit is not assigned:
            fallback: BaseLLMProvider | None = explicit
        elif self.primary is not assigned:
            fallback = self.primary
        else:
            fallback = None

        actual_provider = assigned
        try:
            response = await _call(assigned)
            if not response or not response.strip():
                raise LLMError(f"Empty response from {assigned.model} for role={role}")
        except (LLMError, asyncio.TimeoutError) as exc:
            if fallback is None:
                raise
            logger.warning(
                "Role '%s' provider '%s' failed (%s) — retrying with fallback '%s'",
                role, assigned.model, type(exc).__name__, fallback.model,
            )
            response = await _call(fallback)
            actual_provider = fallback

        # Build metadata with cost tracking
        metadata: dict[str, Any] = {}

        # Prefer actual token counts from the provider that succeeded
        input_tokens = getattr(actual_provider, 'last_input_tokens', None)
        output_tokens = getattr(actual_provider, 'last_output_tokens', None)
        cost_usd = getattr(actual_provider, 'last_cost_usd', None)

        if input_tokens is not None and input_tokens > 0:
            metadata["input_tokens"] = input_tokens
            metadata["output_tokens"] = output_tokens or 0
            metadata["cost_usd"] = cost_usd or 0.0
        else:
            # Fallback: estimate by word count
            metadata["input_tokens"] = len(system_prompt.split()) + len(user_prompt.split())
            metadata["output_tokens"] = len(response.split())
            metadata["cost_usd"] = 0.0  # Unknown when provider doesn't report usage

        # Include the model that actually produced the response
        metadata["model"] = actual_provider.model

        return response, metadata

    def describe(self) -> dict[str, str]:
        result = {"[primary]": self.primary.model}
        for role, p in self.routing_table.items():
            explicit_fb = self.fallback_table.get(role)
            auto_fb = self.primary if self.primary is not p else None
            fb = explicit_fb or auto_fb
            suffix = f" -> {fb.model}" if fb else ""
            result[role] = f"{p.model}{suffix}"
        return result

    @classmethod
    def from_model_ids(
        cls,
        primary_id: str,
        routing: dict[str, str] | None = None,
        fallback_routing: dict[str, str] | None = None,
        verbose: bool = False,
    ) -> "ProviderRouter":
        """Build router from model ID strings."""
        primary = build_provider(primary_id)
        table = {role: build_provider(mid) for role, mid in (routing or {}).items()}
        fallback_table = {role: build_provider(mid) for role, mid in (fallback_routing or {}).items()}
        return cls(primary=primary, routing_table=table, fallback_table=fallback_table, verbose=verbose)
