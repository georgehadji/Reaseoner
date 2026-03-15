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
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)

import anthropic
import openai

from exceptions import (
    ARAError,
    AuthenticationError,
    RateLimitError,
    ModelNotFoundError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    is_retryable,
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
        max_tokens: int = 2048,
        temperature: float = 0.7,
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

    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
        max_retries: int = 3,
        extra_body: dict[str, Any] | None = None,
        http_client: "openai.AsyncOpenAI | None" = None,
    ) -> None:
        super().__init__(model, max_retries)
        self.extra_body = extra_body or {}

        # If a pre-configured OpenAI client is provided, use it directly
        if http_client is not None:
            self.client = http_client
            return

        # Initialize the shared pool if it doesn't exist
        if OpenAICompatibleProvider._shared_pool is None:
            try:
                import httpx
                # Create HTTP client with connection pooling
                OpenAICompatibleProvider._shared_pool = httpx.AsyncClient(
                    limits=httpx.Limits(
                        max_keepalive_connections=20,
                        max_connections=100,
                        keepalive_expiry=30.0,
                    ),
                    timeout=httpx.Timeout(60.0, connect=10.0),
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

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> str:
        # Determine which parameter name to use based on model
        if self.model.startswith(('gpt-', 'o3', 'o1')):
            # OpenAI models use max_completion_tokens
            kwargs: dict[str, Any] = {
                "model": self.model,
                "max_completion_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
            }
            # DO NOT send temperature parameter at all for OpenAI models that may not support it
            # Some models only support the default temperature and don't accept ANY temperature parameter
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
            # DO NOT send temperature parameter - let model use its default
        else:
            # Other models use max_tokens
            kwargs: dict[str, Any] = {
                "model": self.model,
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
            }
            # DO NOT send temperature parameter - let model use its default
            # This prevents "unsupported value" errors for models that only accept default temperature

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
        return response.choices[0].message.content or ""


# ─────────────────────────────────────────────────────────────────────
# ANTHROPIC (native SDK)
# ─────────────────────────────────────────────────────────────────────

class AnthropicProvider(BaseLLMProvider):
    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        api_key: str | None = None,
        max_retries: int = 3,
    ) -> None:
        super().__init__(model, max_retries)
        self.client = anthropic.AsyncAnthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        )

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> str:
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        if not response.content:
            raise ProviderUnavailableError(
                f"Anthropic returned empty content (model={self.model}; possible content filtering)"
            )
        return response.content[0].text or ""


# ─────────────────────────────────────────────────────────────────────
# GOOGLE GEMINI (native SDK)
# ─────────────────────────────────────────────────────────────────────

class GoogleProvider(BaseLLMProvider):
    def __init__(
        self,
        model: str = "gemini-2.0-pro-exp",
        api_key: str | None = None,
        max_retries: int = 3,
    ) -> None:
        super().__init__(model, max_retries)
        try:
            import google.generativeai as genai  # type: ignore[import]
            genai.configure(api_key=api_key or os.environ.get("GOOGLE_API_KEY", ""))
            self._genai = genai
        except ImportError as exc:
            raise ImportError("pip install google-generativeai") from exc

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> str:
        model = self._genai.GenerativeModel(
            self.model, system_instruction=system_prompt
        )
        config = self._genai.GenerationConfig(
            max_output_tokens=max_tokens, temperature=temperature
        )
        response = await asyncio.to_thread(
            model.generate_content, user_prompt, generation_config=config
        )
        return response.text


# ─────────────────────────────────────────────────────────────────────
# MISTRAL (native SDK — required for EU sovereign on-prem)
# ─────────────────────────────────────────────────────────────────────

class MistralProvider(BaseLLMProvider):
    def __init__(
        self,
        model: str = "mistral-large-latest",
        api_key: str | None = None,
        max_retries: int = 3,
    ) -> None:
        super().__init__(model, max_retries)
        try:
            from mistralai import Mistral  # type: ignore[import]
            self.client = Mistral(
                api_key=api_key or os.environ.get("MISTRAL_API_KEY", "")
            )
        except ImportError as exc:
            raise ImportError("pip install mistralai") from exc

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> str:
        response = await asyncio.to_thread(
            self.client.chat.complete,
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
        )
        if not response.choices:
            raise ProviderUnavailableError(
                f"Mistral returned empty choices (model={self.model}; possible content filtering)"
            )
        return response.choices[0].message.content or ""


# ─────────────────────────────────────────────────────────────────────
# MODEL REGISTRY
# Every supported model with API base URL and env key name
# ─────────────────────────────────────────────────────────────────────

_REGISTRY: dict[str, dict[str, Any]] = {

    # ── ANTHROPIC ───────────────────────────────────────────────────
    "claude-opus":   {"cls": "anthropic", "model": "claude-opus-4-6",           "env": "ANTHROPIC_API_KEY"},
    "claude-sonnet": {"cls": "anthropic", "model": "claude-sonnet-4-6",         "env": "ANTHROPIC_API_KEY"},
    "claude-haiku":  {"cls": "anthropic", "model": "claude-haiku-4-5-20251001", "env": "ANTHROPIC_API_KEY"},

    # ── OPENAI ──────────────────────────────────────────────────────
    "gpt-5":         {"cls": "openai", "model": "gpt-5",       "env": "OPENAI_API_KEY"},
    "gpt-5-mini":    {"cls": "openai", "model": "gpt-5-mini",  "env": "OPENAI_API_KEY"},
    "gpt-4o":        {"cls": "openai", "model": "gpt-4o",      "env": "OPENAI_API_KEY"},
    "gpt-4o-mini":   {"cls": "openai", "model": "gpt-4o-mini", "env": "OPENAI_API_KEY"},
    "o3":            {"cls": "openai", "model": "o3",           "env": "OPENAI_API_KEY"},
    "o3-mini":       {"cls": "openai", "model": "o3-mini",      "env": "OPENAI_API_KEY"},

    # ── GOOGLE GEMINI ───────────────────────────────────────────────
    "gemini-pro":    {"cls": "google", "model": "gemini-2.5-pro",   "env": "GOOGLE_API_KEY"},
    "gemini-flash":  {"cls": "google", "model": "gemini-2.5-flash", "env": "GOOGLE_API_KEY"},

    # ── XAI / GROK (real-time X data) ───────────────────────────────
    "grok-4-heavy": {"cls": "compat", "model": "grok-4-heavy", "base": "https://api.x.ai/v1", "env": "XAI_API_KEY"},
    "grok-4":       {"cls": "compat", "model": "grok-4",        "base": "https://api.x.ai/v1", "env": "XAI_API_KEY"},
    "grok-3":       {"cls": "compat", "model": "grok-3",        "base": "https://api.x.ai/v1", "env": "XAI_API_KEY"},
    "grok-3-mini":  {"cls": "compat", "model": "grok-3-mini",   "base": "https://api.x.ai/v1", "env": "XAI_API_KEY"},

    # ── PERPLEXITY SONAR (web-grounded — unique for Phase 3 critique) ─
    "sonar-pro": {
        "cls": "compat",
        "model": "sonar-pro",
        "base": "https://api.perplexity.ai",
        "env": "PERPLEXITY_API_KEY",
        # Balanced default for grounded scoring / verification.
        "extra_body": {"web_search_options": {"search_context_size": "medium"}},
    },
    "sonar": {
        "cls": "compat",
        "model": "sonar",
        "base": "https://api.perplexity.ai",
        "env": "PERPLEXITY_API_KEY",
        # Cheapest Perplexity tier for lightweight classification / retrieval.
        "extra_body": {"web_search_options": {"search_context_size": "low"}},
    },
    "sonar-reasoning-pro": {
        "cls": "compat",
        "model": "sonar-reasoning-pro",
        "base": "https://api.perplexity.ai",
        "env": "PERPLEXITY_API_KEY",
        "extra_body": {"web_search_options": {"search_context_size": "medium"}},
    },
    "sonar-deep-research": {
        "cls": "compat",
        "model": "sonar-deep-research",
        "base": "https://api.perplexity.ai",
        "env": "PERPLEXITY_API_KEY",
        # Keep exhaustive research available, but bias toward lower reasoning cost by default.
        "extra_body": {"reasoning_effort": "low"},
    },

    # ── MISTRAL (EU sovereign, Apache 2.0) ──────────────────────────
    "mistral-large-3": {"cls": "mistral", "model": "mistral-large-latest",  "env": "MISTRAL_API_KEY"},
    "mistral-medium":  {"cls": "mistral", "model": "mistral-medium-latest", "env": "MISTRAL_API_KEY"},
    "codestral":       {"cls": "mistral", "model": "codestral-latest",      "env": "MISTRAL_API_KEY"},
    "ministral-8b":    {"cls": "mistral", "model": "ministral-8b-latest",   "env": "MISTRAL_API_KEY"},
    "ministral-3b":    {"cls": "mistral", "model": "ministral-3b-latest",   "env": "MISTRAL_API_KEY"},

    # ── DEEPSEEK (adversarial RL training) ──────────────────────────
    "deepseek-v3":   {"cls": "compat", "model": "deepseek-chat",     "base": "https://api.deepseek.com/v1", "env": "DEEPSEEK_API_KEY"},
    "deepseek-r1":   {"cls": "compat", "model": "deepseek-reasoner", "base": "https://api.deepseek.com/v1", "env": "DEEPSEEK_API_KEY"},

    # ── QWEN / ALIBABA (multilingual breadth) ───────────────────────
    "qwen3-max":    {"cls": "compat", "model": "qwen-max",        "base": "https://dashscope.aliyuncs.com/compatible-mode/v1", "env": "DASHSCOPE_API_KEY"},
    "qwen3-plus":   {"cls": "compat", "model": "qwen-plus",       "base": "https://dashscope.aliyuncs.com/compatible-mode/v1", "env": "DASHSCOPE_API_KEY"},
    "qwen3-turbo":  {"cls": "compat", "model": "qwen-turbo",      "base": "https://dashscope.aliyuncs.com/compatible-mode/v1", "env": "DASHSCOPE_API_KEY"},
    "qwen3-coder":  {"cls": "compat", "model": "qwen-coder-plus", "base": "https://dashscope.aliyuncs.com/compatible-mode/v1", "env": "DASHSCOPE_API_KEY"},

    # ── KIMI / MOONSHOT (creative breadth, agentic) ─────────────────
    "kimi-k2":         {"cls": "compat", "model": "moonshot-v1-128k", "base": "https://api.moonshot.cn/v1", "env": "MOONSHOT_API_KEY"},
    "kimi-k2-5":       {"cls": "compat", "model": "kimi-k2.5",        "base": "https://api.moonshot.cn/v1", "env": "MOONSHOT_API_KEY"},
    "kimi-k2-thinking":{"cls": "compat", "model": "kimi-k2-thinking", "base": "https://api.moonshot.cn/v1", "env": "MOONSHOT_API_KEY"},

    # ── GLM / ZHIPUAI (#1 Artificial Analysis Intelligence Index) ────
    "glm-5":       {"cls": "compat", "model": "glm-5",        "base": "https://open.bigmodel.cn/api/paas/v4", "env": "ZHIPUAI_API_KEY"},
    "glm-4-plus":  {"cls": "compat", "model": "glm-4-plus",   "base": "https://open.bigmodel.cn/api/paas/v4", "env": "ZHIPUAI_API_KEY"},
    "glm-4-air":   {"cls": "compat", "model": "glm-4-air",    "base": "https://open.bigmodel.cn/api/paas/v4", "env": "ZHIPUAI_API_KEY"},
    "glm-4-airx":  {"cls": "compat", "model": "glm-4-airx",   "base": "https://open.bigmodel.cn/api/paas/v4", "env": "ZHIPUAI_API_KEY"},
    "glm-4-long":  {"cls": "compat", "model": "glm-4-long",   "base": "https://open.bigmodel.cn/api/paas/v4", "env": "ZHIPUAI_API_KEY"},

    # ── MINIMAX (cost-efficient, ~Claude Opus 4.6 quality) ───────────
    "minimax-m2":   {"cls": "compat", "model": "MiniMax-Text-01", "base": "https://api.minimax.chat/v1", "env": "MINIMAX_API_KEY"},
    "minimax-m2-5": {"cls": "compat", "model": "abab6.5s-chat",   "base": "https://api.minimax.chat/v1", "env": "MINIMAX_API_KEY"},

    # ── OLLAMA (local LLMs) ──────────────────────────────────────────
    # Note: Uses OLLAMA_BASE_URL env var, defaults to http://localhost:11434
    # Models are dynamically fetched from the Ollama instance
    "ollama-llama3":   {"cls": "compat", "model": "llama3",        "base": "http://localhost:11434/v1", "env": "OLLAMA_API_KEY", "is_local": True},
    "ollama-llama3.1": {"cls": "compat", "model": "llama3.1",      "base": "http://localhost:11434/v1", "env": "OLLAMA_API_KEY", "is_local": True},
    "ollama-llama3.2": {"cls": "compat", "model": "llama3.2",      "base": "http://localhost:11434/v1", "env": "OLLAMA_API_KEY", "is_local": True},
    "ollama-mistral":  {"cls": "compat", "model": "mistral",       "base": "http://localhost:11434/v1", "env": "OLLAMA_API_KEY", "is_local": True},
    "ollama-codellama":{"cls": "compat", "model": "codellama",      "base": "http://localhost:11434/v1", "env": "OLLAMA_API_KEY", "is_local": True},
    "ollama-qwen2":    {"cls": "compat", "model": "qwen2",          "base": "http://localhost:11434/v1", "env": "OLLAMA_API_KEY", "is_local": True},
    "ollama-gemma2":   {"cls": "compat", "model": "gemma2",         "base": "http://localhost:11434/v1", "env": "OLLAMA_API_KEY", "is_local": True},
    "ollama-phi3":     {"cls": "compat", "model": "phi3",           "base": "http://localhost:11434/v1", "env": "OLLAMA_API_KEY", "is_local": True},
}


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
    # Fail fast: an empty key passes silently to SDK constructors but errors at
    # the first API call, making the root cause hard to trace.  Local providers
    # (Ollama) are exempt — they accept a dummy key.
    if not key and not cfg.get("is_local"):
        raise ValueError(
            f"API key for '{model_id}' is not set. "
            f"Set the {cfg['env']} environment variable."
        )

    match cfg["cls"]:
        case "anthropic":
            return AnthropicProvider(model=cfg["model"], api_key=key)
        case "openai":
            return OpenAICompatibleProvider(model=cfg["model"], api_key=key)
        case "google":
            return GoogleProvider(model=cfg["model"], api_key=key)
        case "mistral":
            return MistralProvider(model=cfg["model"], api_key=key)
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
    prefix_map = {
        "claude": "anthropic", "gpt": "openai", "o3": "openai",
        "gemini": "google", "grok": "xai",
        "sonar": "perplexity",
        "mistral": "mistral", "ministral": "mistral", "codestral": "mistral",
        "deepseek": "deepseek", "qwen": "qwen",
        "kimi": "kimi", "glm": "glm", "minimax": "minimax",
        "ollama": "ollama",
    }
    groups: dict[str, list[str]] = {k: [] for k in set(prefix_map.values())}
    for mid in sorted(_REGISTRY):
        for prefix, group in prefix_map.items():
            if mid.startswith(prefix):
                groups[group].append(mid)
                break
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
        max_tokens: int = 2048,
        temperature: float = 0.7,
        timeout_seconds: float | None = None,
    ) -> tuple[str, dict[str, int]]:
        """
        Call LLM for role. On LLMError or timeout, tries a fallback provider:
          1. Explicit fallback from fallback_table (if defined and different)
          2. Primary (if role was using a non-primary model)
          3. Re-raises original error if no fallback available
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

        input_tokens = len(system_prompt.split()) + len(user_prompt.split())
        output_tokens = len(response.split())
        return response, {"input": input_tokens, "output": output_tokens}

    def describe(self) -> dict[str, str]:
        result = {"[primary]": self.primary.model}
        for role, p in self.routing_table.items():
            explicit_fb = self.fallback_table.get(role)
            auto_fb = self.primary if self.primary is not p else None
            fb = explicit_fb or auto_fb
            suffix = f" → {fb.model}" if fb else ""
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
