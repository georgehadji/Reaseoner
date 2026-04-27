"""
LLM Executor — infrastructure concern extracted from ARAPipeline.

Responsible for:
  - Temperature resolution from phase_configs
  - Token-aware cache lookup and storage
  - Router delegation (ProviderRouter.call)
  - Cost and token accumulation into PipelineState
"""

from __future__ import annotations

import logging
from typing import Any

from reasoner.core.constants import TRUNCATION
from reasoner.infrastructure.llm.router import ProviderRouter
from reasoner.models import PipelineState

logger = logging.getLogger(__name__)


class LLMExecutor:
    """
    Stateless (per-call) infrastructure adapter that wraps ProviderRouter with
    token-aware caching and cost tracking.

    Extracted from ARAPipeline._call_llm_cached to isolate LLM execution
    concerns from phase-sequencing concerns.
    """

    def __init__(
        self,
        router: ProviderRouter,
        phase_configs: dict,
        token_cache: Any | None,
        caching_enabled: bool,
    ) -> None:
        self.router = router
        self.phase_configs = phase_configs
        self._token_cache = token_cache
        self._caching_enabled = caching_enabled

    async def execute(
        self,
        role: str,
        system_prompt: str,
        user_prompt: str,
        state: PipelineState,
        phase_key: str | None = None,
        **kwargs: Any,
    ) -> tuple[str, dict[str, Any]]:
        """
        Call the LLM with token-aware caching and cost tracking.

        - Resolves temperature from phase_configs unless already provided.
        - Checks cache before hitting the router (cache hit = 0 cost).
        - Accumulates token usage and cost into state after every call.
        - Stores the response in cache on a miss.
        """
        # ── Temperature resolution ────────────────────────────────────────
        if "temperature" not in kwargs:
            lookup = phase_key or role
            if lookup in self.phase_configs:
                kwargs["temperature"] = self.phase_configs[lookup].temperature
            else:
                for cfg in self.phase_configs.values():
                    if cfg.role == role:
                        kwargs["temperature"] = cfg.temperature
                        break

        # ── Cache lookup ──────────────────────────────────────────────────
        if self._token_cache and self._caching_enabled:
            model_id = self.router.get(role).model if hasattr(self.router, "get") else "unknown"
            cache_prompt = (
                user_prompt
                if role in ("synthesis", "context_vetting", "primary")
                else user_prompt[: TRUNCATION.PROBLEM]
            )
            cached_response = await self._token_cache.get(
                problem=state.problem,
                phase=role,
                model_id=model_id,
                prompt=cache_prompt,
            )
            if cached_response:
                logger.info(f"[CACHE] HIT for {role} (saved ~{len(cached_response)//4} tokens)")
                estimated_input = len(user_prompt) // 4
                estimated_output = len(cached_response) // 4
                self._accumulate_tokens(state, role, estimated_input, estimated_output, model_id)
                token_meta = {
                    "input": estimated_input,
                    "output": estimated_output,
                    "total": estimated_input + estimated_output,
                }
                return cached_response, {**token_meta, "cost_usd": 0.0, "model": model_id, "cached": True}

        # ── LLM call ──────────────────────────────────────────────────────
        logger.info(f"[CACHE] MISS for {role}")
        raw, metadata = await self.router.call(
            role=role,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            **kwargs,
        )

        from reasoner.infrastructure.llm.ports import DegradedLLMResponse
        if isinstance(raw, DegradedLLMResponse):
            logger.error(f"LLM degraded for role={role}: {raw.error}")
            raise RuntimeError(raw.error)

        if not raw or not raw.strip():
            logger.warning(f"LLM returned empty response for role={role}; possible content filter or API error")

        # ── Cost and token accumulation ───────────────────────────────────
        cost_usd = metadata.get("cost_usd", 0.0)
        input_tokens = metadata.get("input_tokens", 0)
        output_tokens = metadata.get("output_tokens", 0)
        model = metadata.get("model", "unknown")

        if cost_usd > 0:
            state.total_cost_usd += cost_usd
            state.phase_costs[role] = cost_usd

        self._accumulate_tokens(state, role, input_tokens, output_tokens, model)

        # ── Cache store ───────────────────────────────────────────────────
        if self._token_cache and self._caching_enabled:
            model_id = self.router.get(role).model if hasattr(self.router, "get") else "unknown"
            cache_prompt = (
                user_prompt
                if role in ("synthesis", "context_vetting", "primary")
                else user_prompt[: TRUNCATION.PROBLEM]
            )
            await self._token_cache.set(
                problem=state.problem,
                phase=role,
                model_id=model_id,
                prompt=cache_prompt,
                response=raw,
                tokens_used=input_tokens + output_tokens,
            )

        return raw, metadata

    @staticmethod
    def _accumulate_tokens(
        state: PipelineState,
        role: str,
        input_tokens: int,
        output_tokens: int,
        model: str,
    ) -> None:
        """Update all token and model tracking fields on state."""
        state.phase_models[role] = model

        prior = state.detailed_token_usage.get(role, {"input": 0, "output": 0, "total": 0})
        state.detailed_token_usage[role] = {
            "input": prior["input"] + input_tokens,
            "output": prior["output"] + output_tokens,
            "total": prior["total"] + input_tokens + output_tokens,
        }

        tracking_key = getattr(state, "_current_phase_key", None)
        if tracking_key:
            if tracking_key not in state.phase_tokens:
                state.phase_tokens[tracking_key] = {"input": 0, "output": 0}
            state.phase_tokens[tracking_key]["input"] += input_tokens
            state.phase_tokens[tracking_key]["output"] += output_tokens

            if tracking_key not in state.cost_state._phase_models_by_key:
                state.cost_state._phase_models_by_key[tracking_key] = []
            if model not in state.cost_state._phase_models_by_key[tracking_key]:
                state.cost_state._phase_models_by_key[tracking_key].append(model)
