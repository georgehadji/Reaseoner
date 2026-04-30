"""
LLM Executor — infrastructure concern extracted from ReasonerPipeline.

Responsible for:
  - Temperature resolution from phase_configs
  - Token-aware cache lookup and storage
  - Router delegation (ProviderRouter.call)
  - Cost and token accumulation into PipelineState
"""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator

from reasoner.core.constants import (
    DEFAULT_MAX_TOKENS,
    PHASE_TOKEN_BUDGETS,
    TRUNCATION,
)
from reasoner.infrastructure.llm.router import ProviderRouter
from reasoner.models import PipelineState

logger = logging.getLogger(__name__)


class LLMExecutor:
    """
    Stateless (per-call) infrastructure adapter that wraps ProviderRouter with
    token-aware caching and cost tracking.

    Extracted from ReasonerPipeline._call_llm_cached to isolate LLM execution
    concerns from phase-sequencing concerns.
    """

    def __init__(
        self,
        router: ProviderRouter,
        phase_configs: dict,
        token_cache: Any | None,
        caching_enabled: bool,
        cascading_routing: dict[str, list[str]] | None = None,
    ) -> None:
        self.router = router
        self.phase_configs = phase_configs
        self._token_cache = token_cache
        self._caching_enabled = caching_enabled
        self.cascading_routing = cascading_routing or {}

    async def execute(
        self,
        role: str,
        system_prompt: str,
        user_prompt: str,
        state: PipelineState,
        phase_key: str | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> tuple[str, dict[str, Any]] | AsyncIterator[str | DegradedLLMResponse]:
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
        # Caching for streaming is complex. For now, disable caching for streaming calls.
        # A robust streaming cache would need to store/retrieve partial streams.
        if stream and self._caching_enabled:
            logger.warning("Caching is currently not supported for streaming LLM calls.")

        if self._token_cache and self._caching_enabled and not stream:
            # For caching, we need a specific model_id. If cascading, we'll cache against the first model.
            # This is a simplification; a more robust cache would handle model cascades explicitly.
            model_id_for_cache = self.cascading_routing.get(role, [self.router.get(role).model])[0]
            cache_prompt = (
                user_prompt
                if role in ("synthesis", "context_vetting", "primary")
                else user_prompt[: TRUNCATION.PROBLEM]
            )
            cached_response = await self._token_cache.get(
                problem=state.problem,
                phase=role,
                model_id=model_id_for_cache,
                prompt=cache_prompt,
            )
            if cached_response:
                logger.info(f"[CACHE] HIT for {role} (saved ~{len(cached_response)//4} tokens)")
                estimated_input = len(user_prompt) // 4
                estimated_output = len(cached_response) // 4
                self._accumulate_tokens(state, role, estimated_input, estimated_output, model_id_for_cache)
                token_meta = {
                    "input": estimated_input,
                    "output": estimated_output,
                    "total": estimated_input + estimated_output,
                }
                return cached_response, {**token_meta, "cost_usd": 0.0, "model": model_id_for_cache, "cached": True}

        # ── LLM call (with cascading logic if configured) ──────────────────────
        # Defensive: ensure max_tokens is always set before reaching the provider.
        if "max_tokens" not in kwargs:
            kwargs["max_tokens"] = PHASE_TOKEN_BUDGETS.get(role, DEFAULT_MAX_TOKENS)
            logger.debug(f"[EXECUTOR] defaulted max_tokens={kwargs['max_tokens']} for role={role}")

        cascading_models = self.cascading_routing.get(role)

        if cascading_models:
            last_error: Exception | None = None
            for model_id in cascading_models:
                try:
                    logger.info(f"[CASCADING] Trying model '{model_id}' for role '{role}'...")
                    from reasoner.infrastructure.llm.registry import build_provider
                    temp_router = ProviderRouter(primary=build_provider(model_id), verbose=False)

                    raw, metadata = await temp_router.call(
                        role="primary",
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        **kwargs,
                    )
                    from reasoner.infrastructure.llm.ports import DegradedLLMResponse
                    if isinstance(raw, DegradedLLMResponse):
                        raise RuntimeError(f"Degraded response from {model_id}: {raw.error}")

                    if not raw or not raw.strip():
                        raise RuntimeError(f"Empty response from {model_id} for role={role}")

                    if role in ("fusion", "classification", "decomposition", "scoring", "meta_evaluator"):
                        try:
                            import json
                            json.loads(raw)
                        except json.JSONDecodeError:
                            raise RuntimeError(f"Malformed JSON from {model_id} for role={role}")

                    logger.info(f"[CASCADING] Model '{model_id}' succeeded for role '{role}'.")
                    if self._token_cache and self._caching_enabled:
                        await self._token_cache.set(
                            problem=state.problem,
                            phase=role,
                            model_id=model_id,
                            prompt=cache_prompt,
                            response=raw,
                            tokens_used=metadata.get("input_tokens", 0) + metadata.get("output_tokens", 0),
                        )
                    self._accumulate_tokens(state, role, metadata.get("input_tokens", 0), metadata.get("output_tokens", 0), model_id)
                    return raw, metadata

                except Exception as exc:
                    last_error = exc
                    logger.warning(f"[CASCADING] Model '{model_id}' failed for role '{role}': {exc}")
            
            if last_error:
                logger.error(f"All cascading models failed for role={role}: {last_error}")
                return DegradedLLMResponse(
                    text="",
                    error=f"All cascading models failed for role={role}: {last_error}",
                    metadata={},
                ), {}
            else:
                logger.error(f"Unknown error in cascading for role={role}")
                return DegradedLLMResponse(
                    text="",
                    error=f"Unknown error in cascading for role={role}",
                    metadata={},
                ), {}

        else: # No cascading routing, use standard routing
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

            cost_usd = metadata.get("cost_usd", 0.0)
            input_tokens = metadata.get("input_tokens", 0)
            output_tokens = metadata.get("output_tokens", 0)
            model = metadata.get("model", "unknown")

            if cost_usd > 0:
                state.total_cost_usd += cost_usd
                state.phase_costs[role] = cost_usd

            self._accumulate_tokens(state, role, input_tokens, output_tokens, model)

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

    async def execute_stream(
        self,
        role: str,
        system_prompt: str,
        user_prompt: str,
        state: PipelineState,
        phase_key: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str | DegradedLLMResponse]:
        """Streaming variant of execute. Yields chunks as they arrive.

        NOTE: Caching, token accumulation, and cascading are not yet fully
        implemented for streaming.
        """
        if "max_tokens" not in kwargs:
            kwargs["max_tokens"] = PHASE_TOKEN_BUDGETS.get(role, DEFAULT_MAX_TOKENS)

        if self._caching_enabled:
            logger.warning("Caching is currently not supported for streaming LLM calls.")

        cascading_models = self.cascading_routing.get(role)
        if cascading_models:
            last_error: Exception | None = None
            for model_id in cascading_models:
                try:
                    from reasoner.infrastructure.llm.registry import build_provider
                    temp_router = ProviderRouter(primary=build_provider(model_id), verbose=False)
                    full_response_content = []
                    async for chunk_or_degraded in temp_router.call(
                        role="primary",
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        stream=True,
                        **kwargs,
                    ):
                        if isinstance(chunk_or_degraded, DegradedLLMResponse):
                            raise RuntimeError(f"Degraded streaming response from {model_id}: {chunk_or_degraded.error}")
                        full_response_content.append(chunk_or_degraded)
                        yield chunk_or_degraded

                    final_response_str = "".join(full_response_content)
                    if not final_response_str or not final_response_str.strip():
                        raise RuntimeError(f"Empty streaming response from {model_id} for role={role}")
                    return
                except Exception as exc:
                    last_error = exc
                    logger.warning(f"[CASCADING STREAM] Model '{model_id}' failed for role '{role}': {exc}")
            if last_error:
                yield DegradedLLMResponse(
                    text="",
                    error=f"All cascading streaming models failed for role={role}: {last_error}",
                    metadata={},
                )
            else:
                yield DegradedLLMResponse(
                    text="",
                    error=f"Unknown error in streaming cascading for role={role}",
                    metadata={},
                )
            return

        async for chunk_or_degraded in self.router.call(
            role=role,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            stream=True,
            **kwargs,
        ):
            if isinstance(chunk_or_degraded, DegradedLLMResponse):
                yield chunk_or_degraded
                return
            yield chunk_or_degraded

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
