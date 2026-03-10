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
    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
        max_retries: int = 3,
        extra_body: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(model, max_retries)
        self.extra_body = extra_body or {}
        self.client = openai.AsyncOpenAI(
            api_key=api_key or "missing",
            base_url=base_url,
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
        response = await self.client.chat.completions.create(**kwargs)
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
        return response.content[0].text


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
    "gemini-pro":    {"cls": "google", "model": "gemini-2.0-pro-exp",   "env": "GOOGLE_API_KEY"},
    "gemini-flash":  {"cls": "google", "model": "gemini-2.0-flash-exp", "env": "GOOGLE_API_KEY"},

    # ── XAI / GROK (real-time X data) ───────────────────────────────
    "grok-4-heavy": {"cls": "compat", "model": "grok-4-heavy", "base": "https://api.x.ai/v1", "env": "XAI_API_KEY"},
    "grok-4":       {"cls": "compat", "model": "grok-4",        "base": "https://api.x.ai/v1", "env": "XAI_API_KEY"},
    "grok-3":       {"cls": "compat", "model": "grok-3",        "base": "https://api.x.ai/v1", "env": "XAI_API_KEY"},
    "grok-3-mini":  {"cls": "compat", "model": "grok-3-mini",   "base": "https://api.x.ai/v1", "env": "XAI_API_KEY"},

    # ── PERPLEXITY SONAR (web-grounded — unique for Phase 3 critique) ─
    "sonar-pro":           {"cls": "compat", "model": "sonar-pro",           "base": "https://api.perplexity.ai", "env": "PERPLEXITY_API_KEY"},
    "sonar":               {"cls": "compat", "model": "sonar",               "base": "https://api.perplexity.ai", "env": "PERPLEXITY_API_KEY"},
    "sonar-reasoning-pro": {"cls": "compat", "model": "sonar-reasoning-pro", "base": "https://api.perplexity.ai", "env": "PERPLEXITY_API_KEY"},
    "sonar-deep-research": {"cls": "compat", "model": "sonar-deep-research", "base": "https://api.perplexity.ai", "env": "PERPLEXITY_API_KEY"},

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
            return OpenAICompatibleProvider(
                model=cfg["model"], api_key=key, base_url=cfg.get("base")
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
    ) -> None:
        self.primary = primary
        self.routing_table: dict[str, BaseLLMProvider] = routing_table or {}
        # Explicit per-role fallbacks. Roles absent here fall back to primary automatically.
        self.fallback_table: dict[str, BaseLLMProvider] = fallback_table or {}

    def get(self, role: str) -> BaseLLMProvider:
        return self.routing_table.get(role, self.primary)

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
    ) -> "ProviderRouter":
        """Build router from model ID strings."""
        primary = build_provider(primary_id)
        table = {role: build_provider(mid) for role, mid in (routing or {}).items()}
        fallback_table = {role: build_provider(mid) for role, mid in (fallback_routing or {}).items()}
        return cls(primary=primary, routing_table=table, fallback_table=fallback_table)
