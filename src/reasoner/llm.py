"""
ARA Pipeline — Multi-Provider LLM Abstraction
Supports every major LLM ecosystem (Mar 2026):

Western:     Anthropic Claude, OpenAI GPT, Google Gemini
xAI:         Grok (OpenAI-compatible)
Perplexity:  Sonar, Sonar Pro, Deep Research (search-grounded)
Mistral:     Large 3, Codestral, Ministral (EU-sovereign, Apache 2.0)
Chinese OSS: DeepSeek, Qwen, Kimi, GLM/ZhipuAI, MiniMax
             (all via OpenAI-compatible endpoints)
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


def _patch_openai_platform_detection() -> None:
    """
    Windows WMI can hang indefinitely when the openai library calls
    platform.system() / platform.platform() / platform.machine() to build
    its X-Stainless-* headers. We pre-patch these to safe defaults on Windows
    before openai is imported so that API calls never deadlock.
    """
    import sys
    if sys.platform != "win32":
        return
    import platform
    platform.system = lambda: "Windows"  # type: ignore[method-assign]
    platform.platform = lambda: "Windows"  # type: ignore[method-assign]
    platform.machine = lambda: "AMD64"  # type: ignore[method-assign]


_patch_openai_platform_detection()

import openai

from reasoner.exceptions import (
    ARAError,
    AuthenticationError,
    RateLimitError,
    ModelNotFoundError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    is_retryable,
)
from reasoner.core.constants import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_RETRIES,
    DEFAULT_BACKOFF_BASE,
    OPENROUTER_BASE_URL as _OPENROUTER_BASE_URL,
    DEFAULT_OLLAMA_URL,
    MODEL_CLAUDE_SONNET,
    MODEL_GEMINI_FLASH,
    MODEL_GEMINI_PRO,
    MODEL_GPT4O_MINI,
    TIMEOUTS,
)


class LLMError(ARAError):
    """Raised when an LLM call fails after all retries."""
    retryable = False


def _requests_strict_json(system_prompt: str, user_prompt: str) -> bool:
    """Heuristic: only enable structured outputs for prompts that already demand pure JSON."""
    combined = f"{system_prompt}\n{user_prompt}"
    if "[SOLUTION]" in combined:
        return False
    return (
        "Output ONLY valid JSON" in combined
        or "Output JSON:" in combined
    )


def _perplexity_response_format(
    model: str,
    system_prompt: str,
    user_prompt: str,
) -> dict[str, Any] | None:
    """
    Return a permissive JSON-schema response format for compatible Perplexity models.

    sonar-reasoning-pro is excluded because it may emit <think> sections even when
    response_format is requested.
    sonar-deep-research is excluded because long-form research calls can collapse to
    an empty `{}` under a permissive generic schema.
    """
    if not model.startswith("sonar"):
        return None
    if model in {"sonar-reasoning-pro", "sonar-deep-research"}:
        return None
    if not _requests_strict_json(system_prompt, user_prompt):
        return None
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "ara_pipeline_response",
            "schema": {
                "type": "object",
                "additionalProperties": True,
            },
        },
    }


# ─────────────────────────────────────────────────────────────────────
# BASE
# ─────────────────────────────────────────────────────────────────────

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
        for attempt in range(self.max_retries):
            try:
                return await self.complete(
                    system_prompt, user_prompt, max_tokens, temperature
                )
            except Exception as exc:
                last_error = exc
                # Don't retry non-retryable errors
                if not is_retryable(exc):
                    raise
                await asyncio.sleep(2 ** attempt)
        raise LLMError(
            f"{self.__class__.__name__}({self.model}) failed "
            f"after {self.max_retries} retries: {last_error}"
        ) from last_error


# ─────────────────────────────────────────────────────────────────────
# OPENAI-COMPATIBLE
# Used for: OpenAI, xAI/Grok, DeepSeek, Qwen, Kimi, GLM, MiniMax, Perplexity
# ─────────────────────────────────────────────────────────────────────

class OpenAICompatibleProvider(BaseLLMProvider):
    # Shared connection pool (httpx client) across all instances for performance
    _shared_pool: "httpx.AsyncClient | None" = None
    _pool_lock: "asyncio.Lock | None" = None
    _pool_init_lock: threading.Lock | None = None
    _pool_closed: bool = False

    @classmethod
    async def close_shared_pool(cls) -> None:
        """
        Close the shared HTTP connection pool.
        Should be called during application shutdown to prevent resource leaks.
        Thread-safe: uses lock to prevent concurrent close attempts.
        """
        if cls._pool_lock is None:
            cls._pool_lock = asyncio.Lock()
        
        async with cls._pool_lock:
            if cls._pool_closed:
                return  # Already closed
            if cls._shared_pool is not None:
                try:
                    await cls._shared_pool.aclose()
                    logger.info("Shared HTTP connection pool closed successfully")
                except Exception as e:
                    logger.error(f"Error closing shared HTTP pool: {e}")
                finally:
                    cls._shared_pool = None
            cls._pool_closed = True
            # Don't reset _pool_lock - keep it for potential future use

    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        extra_body: dict[str, Any] | None = None,
        http_client: "openai.AsyncOpenAI | None" = None,
    ) -> None:
        super().__init__(model, max_retries)
        self.extra_body = extra_body or {}

        # If a pre-configured OpenAI client is provided, use it directly
        if http_client is not None:
            self.client = http_client
            return

        # Initialize the shared pool if it doesn't exist (thread-safe)
        if OpenAICompatibleProvider._pool_init_lock is None:
            OpenAICompatibleProvider._pool_init_lock = threading.Lock()
        with OpenAICompatibleProvider._pool_init_lock:
            if OpenAICompatibleProvider._shared_pool is None:
                # Reset closed flag if we're recreating the pool
                OpenAICompatibleProvider._pool_closed = False
                try:
                    import httpx
                    # Create HTTP client with connection pooling
                    OpenAICompatibleProvider._shared_pool = httpx.AsyncClient(
                        limits=httpx.Limits(
                            max_keepalive_connections=20,
                            max_connections=100,
                            keepalive_expiry=30.0,
                        ),
                        timeout=httpx.Timeout(TIMEOUTS.HTTP_TOTAL, connect=TIMEOUTS.HTTP_CONNECT),
                    )
                except ImportError:
                    # Fallback: if httpx is not available, AsyncOpenAI will create its own pool
                    pass

        # Create a dedicated OpenAI wrapper for this specific key/URL, 
        # but share the underlying connection pool.
        self.client = openai.AsyncOpenAI(
            api_key=api_key or "missing",
            base_url=base_url,
            http_client=OpenAICompatibleProvider._shared_pool,
        )

    # Models that support custom temperature values (0.0-2.0 range).
    # Note: OpenAI models (gpt-*, o1, o3) do NOT accept temperature parameters - they use temperature=1.0 fixed.
    _TEMPERATURE_SUPPORTED_MODELS = frozenset({
        # DeepSeek
        'deepseek-v3', 'deepseek-r1', 'deepseek-chat', 'deepseek-coder',
        # Qwen
        'qwen3-max', 'qwen3-plus', 'qwen3-turbo', 'qwen2.5', 'qwen-max',
        # Kimi
        'kimi-k2', 'kimi-k2-5', 'kimi-plus',
        # GLM/ZhipuAI
        'glm-5', 'glm-4-plus', 'glm-4-air', 'glm-4',
        # MiniMax
        'minimax-01', 'minimax-text',
        # Mistral
        'mistral-large-latest', 'mistral-medium', 'mistral-small', 'codestral',
        # Google Gemini
        'gemini-2.0-pro-exp', 'gemini-2.0-flash-exp', MODEL_GEMINI_PRO, MODEL_GEMINI_FLASH,
        # xAI Grok
        'grok-4', 'grok-3', 'grok-3-mini', 'grok-beta',
        # Perplexity (search-grounded, temperature has limited effect)
        'sonar-pro', 'sonar', 'sonar-deep-research',
    })

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> str:
        # Determine which parameter name to use based on model
        if self.model.startswith(('gpt-', 'o3', 'o1')):
            # OpenAI models (GPT, O1, O3) do NOT accept temperature parameters.
            # They use a fixed temperature=1.0 internally.
            # Sending any temperature value will cause an error.
            kwargs: dict[str, Any] = {
                "model": self.model,
                "max_completion_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
            }
            # DO NOT send temperature - OpenAI models don't accept it
        elif self.model.startswith(('claude-',)):
            # Anthropic models via OpenAI-compatible endpoint
            kwargs: dict[str, Any] = {
                "model": self.model,
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
            }
            # Anthropic Claude models support temperature (0.0-1.0)
            # Only send if not default to avoid "unsupported value" errors
            if temperature != 1.0:
                kwargs["temperature"] = temperature
        else:
            # Other models: check if temperature is supported
            kwargs: dict[str, Any] = {
                "model": self.model,
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
            }
            # Only send temperature for models known to support it
            # This prevents "unsupported value" errors for models that only accept default temperature
            if any(supported in self.model.lower() for supported in self._TEMPERATURE_SUPPORTED_MODELS):
                if temperature != 1.0:  # Omit default to reduce token usage and avoid errors
                    kwargs["temperature"] = temperature

        if self.extra_body:
            kwargs["extra_body"] = self.extra_body
        response_format = _perplexity_response_format(self.model, system_prompt, user_prompt)
        if response_format is not None:
            kwargs["response_format"] = response_format

        try:
            response = await self.client.chat.completions.create(**kwargs)
        except Exception as exc:
            # Safe fallback: if Perplexity rejects the structured output envelope, retry once
            # without response_format instead of failing the whole phase.
            if response_format is not None:
                message = str(exc).lower()
                if (
                    getattr(exc, "status_code", None) == 400
                    or "response_format" in message
                    or "json_schema" in message
                ):
                    logger.warning(
                        "Structured outputs rejected by model '%s' — retrying without response_format",
                        self.model,
                    )
                    kwargs.pop("response_format", None)
                    response = await self.client.chat.completions.create(**kwargs)
                else:
                    raise
            else:
                raise
        if not response.choices:
            raise ProviderUnavailableError(
                f"Provider returned empty choices (model={self.model}; possible content filtering)"
            )
        # Track token usage when available (OpenRouter, OpenAI, etc.)
        usage = getattr(response, "usage", None)
        if usage is not None:
            if hasattr(self, "last_input_tokens"):
                self.last_input_tokens = getattr(usage, "prompt_tokens", 0) or 0
            if hasattr(self, "last_output_tokens"):
                self.last_output_tokens = getattr(usage, "completion_tokens", 0) or 0
            # Cost is not consistently available in the SDK response object;
            # leave last_cost_usd untouched so callers can estimate via pricing.py.
        return response.choices[0].message.content or ""




# ─────────────────────────────────────────────────────────────────────
# OPENROUTER (unified access to 346+ models via single API key)
# ─────────────────────────────────────────────────────────────────────

class OpenRouterProvider(OpenAICompatibleProvider):
    """
    OpenRouter provider — unified access to 346+ models through single API key.
    https://openrouter.ai/docs

    OpenRouter's API is OpenAI-compatible, so we extend OpenAICompatibleProvider
    with OpenRouter-specific base URL and optional features.
    
    Includes cost tracking based on actual token usage.
    """

    OPENROUTER_BASE_URL = _OPENROUTER_BASE_URL

    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        extra_body: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            model=model,
            api_key=api_key or os.environ.get("OPENROUTER_API_KEY", ""),
            base_url=self.OPENROUTER_BASE_URL,
            max_retries=max_retries,
            extra_body=extra_body,
        )
        # Cost tracking
        self.last_input_tokens: int = 0
        self.last_output_tokens: int = 0
        self.last_cost_usd: float = 0.0





# ─────────────────────────────────────────────────────────────────────
# MODEL REGISTRY
# Every supported model with API base URL and env key name
# ─────────────────────────────────────────────────────────────────────

# Whitelist of supported models.  Everything except Ollama routes through OpenRouter.
_MODEL_WHITELIST: dict[str, dict[str, Any]] = {
    # Anthropic
    "claude-opus":      {"model": "anthropic/claude-opus-4.6"},
    MODEL_CLAUDE_SONNET: {"model": "anthropic/claude-sonnet-4.6"},
    "claude-haiku":     {"model": "anthropic/claude-haiku-4.5"},
    # OpenAI
    "gpt-5":            {"model": "openai/gpt-5"},
    "gpt-5-mini":       {"model": "openai/gpt-5-mini"},
    "gpt-4o":           {"model": "openai/gpt-4o"},
    MODEL_GPT4O_MINI:   {"model": "openai/gpt-4o-mini"},
    "o3":               {"model": "openai/o3"},
    "o3-mini":          {"model": "openai/o3-mini"},
    # Google
    MODEL_GEMINI_PRO:   {"model": "google/gemini-2.5-pro"},
    MODEL_GEMINI_FLASH: {"model": "google/gemini-2.5-flash"},
    # xAI
    "grok-4":           {"model": "x-ai/grok-4"},
    "grok-3":           {"model": "x-ai/grok-3"},
    "grok-3-mini":      {"model": "x-ai/grok-3-mini"},
    # Perplexity
    "sonar-pro":        {"model": "perplexity/sonar-pro",      "extra_body": {"web_search_options": {"search_context_size": "medium"}}},
    "sonar":            {"model": "perplexity/sonar",          "extra_body": {"web_search_options": {"search_context_size": "low"}}},
    "sonar-reasoning-pro": {"model": "perplexity/sonar-reasoning-pro", "extra_body": {"web_search_options": {"search_context_size": "medium"}}},
    "sonar-deep-research": {"model": "perplexity/sonar-deep-research", "extra_body": {"reasoning_effort": "low"}},
    # Mistral
    "mistral-large-3":  {"model": "mistralai/mistral-large-2411"},
    "mistral-medium":   {"model": "mistralai/mistral-medium-3.1"},
    "codestral":        {"model": "mistralai/codestral-2501"},
    "ministral-8b":     {"model": "mistralai/ministral-8b"},
    "ministral-3b":     {"model": "mistralai/ministral-3b"},
    # DeepSeek
    "deepseek-v3":      {"model": "deepseek/deepseek-chat-v3-0324"},
    "deepseek-r1":      {"model": "deepseek/deepseek-r1-0528"},
    # Qwen
    "qwen3-max":        {"model": "qwen/qwen3-max"},
    "qwen3-plus":       {"model": "qwen/qwen-plus"},
    "qwen3-turbo":      {"model": "qwen/qwen-turbo"},
    "qwen3-coder":      {"model": "qwen/qwen-coder-plus"},
    # Kimi
    "kimi-k2":          {"model": "moonshotai/kimi-k2"},
    "kimi-k2-5":        {"model": "moonshotai/kimi-k2.5"},
    "kimi-k2-thinking": {"model": "moonshotai/kimi-k2-thinking"},
    # GLM
    "glm-5":            {"model": "z-ai/glm-5"},
    "glm-4-plus":       {"model": "z-ai/glm-4.5"},
    "glm-4-air":        {"model": "z-ai/glm-4.5-air"},
    "glm-4-airx":       {"model": "z-ai/glm-4.6"},
    "glm-4-long":       {"model": "z-ai/glm-4-32b"},
    # MiniMax
    "minimax-m2":       {"model": "minimax/minimax-01"},
    "minimax-m2-5":     {"model": "minimax/abab6.5s-chat"},
    # Ollama (local)
    "ollama-llama3":    {"cls": "compat", "model": "llama3",    "base": f"{DEFAULT_OLLAMA_URL}/v1", "env": "OLLAMA_API_KEY", "is_local": True},
    "ollama-llama3.1":  {"cls": "compat", "model": "llama3.1",  "base": f"{DEFAULT_OLLAMA_URL}/v1", "env": "OLLAMA_API_KEY", "is_local": True},
    "ollama-llama3.2":  {"cls": "compat", "model": "llama3.2",  "base": f"{DEFAULT_OLLAMA_URL}/v1", "env": "OLLAMA_API_KEY", "is_local": True},
    "ollama-mistral":   {"cls": "compat", "model": "mistral",   "base": f"{DEFAULT_OLLAMA_URL}/v1", "env": "OLLAMA_API_KEY", "is_local": True},
    "ollama-codellama": {"cls": "compat", "model": "codellama", "base": f"{DEFAULT_OLLAMA_URL}/v1", "env": "OLLAMA_API_KEY", "is_local": True},
    "ollama-qwen2":     {"cls": "compat", "model": "qwen2",     "base": f"{DEFAULT_OLLAMA_URL}/v1", "env": "OLLAMA_API_KEY", "is_local": True},
    "ollama-gemma2":    {"cls": "compat", "model": "gemma2",    "base": f"{DEFAULT_OLLAMA_URL}/v1", "env": "OLLAMA_API_KEY", "is_local": True},
    "ollama-phi3":      {"cls": "compat", "model": "phi3",      "base": f"{DEFAULT_OLLAMA_URL}/v1", "env": "OLLAMA_API_KEY", "is_local": True},
}

# Build _REGISTRY from whitelist so every non-local model routes through OpenRouter.
_REGISTRY: dict[str, dict[str, Any]] = {}
for _mid, _cfg in _MODEL_WHITELIST.items():
    _entry: dict[str, Any] = dict(_cfg)
    if not _entry.get("is_local"):
        _entry["cls"] = "openrouter"
        _entry["env"] = "OPENROUTER_API_KEY"
    _REGISTRY[_mid] = _entry


def build_provider(model_id: str, api_key: str | None = None) -> BaseLLMProvider:
    """Build a provider instance from a model ID string."""
    if model_id not in _REGISTRY:
        available = "\n  ".join(sorted(_REGISTRY.keys()))
        raise ValueError(
            f"Unknown model ID: {model_id!r}\n"
            f"Available models:\n  {available}"
        )
    cfg = _REGISTRY[model_id]
    key = api_key or os.environ.get(cfg["env"], "")
    if not key and not cfg.get("is_local"):
        raise ValueError(
            f"API key for '{model_id}' is not set. "
            f"Set the {cfg['env']} environment variable."
        )

    match cfg["cls"]:
        case "openrouter":
            return OpenRouterProvider(
                model=cfg["model"],
                api_key=key,
                extra_body=cfg.get("extra_body"),
            )
        case "compat":
            # Handle Ollama base URL from environment
            base_url = cfg.get("base")
            if cfg.get("is_local") and os.environ.get("OLLAMA_BASE_URL"):
                base_url = os.environ.get("OLLAMA_BASE_URL")
            # For Ollama, api_key is optional (can be any dummy value)
            ollama_key = key if key else "ollama"
            return OpenAICompatibleProvider(
                model=cfg["model"],
                api_key=ollama_key,
                base_url=base_url,
                extra_body=cfg.get("extra_body"),
            )
        case _:
            raise ValueError(f"Unknown cls: {cfg['cls']!r}")


def list_models() -> dict[str, list[str]]:
    """Return all model IDs grouped by ecosystem."""
    groups: dict[str, list[str]] = {"openrouter": [], "ollama": []}
    for mid in sorted(_REGISTRY):
        if _REGISTRY[mid].get("is_local"):
            groups["ollama"].append(mid)
        else:
            groups["openrouter"].append(mid)
    return groups


# ─────────────────────────────────────────────────────────────────────
# PROVIDER ROUTER
# ─────────────────────────────────────────────────────────────────────

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


