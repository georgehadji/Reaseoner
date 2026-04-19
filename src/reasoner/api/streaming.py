"""Core pipeline streaming logic — SSE generators for run, follow-up, cache, direct answer, and web search."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
import uuid
from typing import Any, AsyncGenerator

from reasoner.core.constants import (
    SSE_FLUSH_INTERVAL,
    TIMEOUTS,
    TRUNCATION,
    VALIDATION_TEST_MAX_TOKENS,
)
from reasoner.hypergate import HyperGateAgent
from reasoner.llm import ProviderRouter, _REGISTRY
from reasoner.models import PipelineState
from reasoner.pipeline import ARAPipeline
from reasoner.application.services.preset_service import PresetService
from reasoner.application.services.search_service import SearchService
from reasoner.presets import (
    build_auto_preset,
    get_method_from_preset,
    get_preset_tier,
)

from .cache import CACHE_DIR, _MEMORY_CACHE, _cache_key, _load_cache, _save_cache
from .history import HISTORY_DIR, HistoryEntry, _save_history_entry
from .run_state import RunStateStore
from .schemas import FollowupRequest, RunRequest
from .serializers import (
    _event,
    _ser_0,
    _ser_1,
    _ser_1_5,
    _ser_5,
)

logger = logging.getLogger(__name__)

_run_store = RunStateStore()
_preset_service = PresetService()


def _get_phase_subagents(state: PipelineState, phase_name: str) -> list[dict[str, Any]]:
    """Return subagent outputs for a given phase name."""
    mapping = {
        "Decomposition": "decomposition_subagent_outputs",
        "Critique & Pruning": "critique_subagent_outputs",
        "Synthesis": "synthesis_subagent_outputs",
        "Deep Research": "search_subagent_outputs",
    }
    attr = mapping.get(phase_name)
    if attr:
        outputs = getattr(state, attr, [])
        if isinstance(outputs, list):
            return outputs
    return []


async def _stream_direct_answer(
    router: ProviderRouter,
    problem: str,
    run_id: str,
    cancel_event: asyncio.Event | None = None,
) -> AsyncGenerator[str, None]:
    """Stream a direct LLM answer as a virtual single-phase pipeline for UI compatibility."""
    yield _event({"type": "start"})

    if cancel_event and cancel_event.is_set():
        yield _event({"type": "cancelled", "message": "Pipeline stopped by user"})
        return

    yield _event({"type": "phase_start", "phase": 0, "name": "Direct Response"})
    phase_start = time.monotonic()
    try:
        response, meta = await router.call(
            role="primary",
            system_prompt="You are an analytical assistant. Provide a clear, concise answer.",
            user_prompt=problem,
            max_tokens=2048,
            temperature=0.7,
        )
    except Exception as exc:
        logger.warning("Direct answer LLM call failed: %s", exc)
        err_msg = f"{type(exc).__name__}: {str(exc)[:120]}"
        yield _event({"type": "phase_error", "phase": 0, "error": err_msg})
        yield _event({
            "type": "done",
            "errors": [err_msg],
            "total_tokens": {"input": 0, "output": 0, "total": 0},
            "duration": time.monotonic() - phase_start,
        })
        return

    duration = time.monotonic() - phase_start
    data = {
        "solution": response,
        "tokens": {
            "input": meta.get("input_tokens", 0),
            "output": meta.get("output_tokens", 0),
        },
        "duration": duration,
    }
    yield _event({
        "type": "phase_complete",
        "phase": 0,
        "name": "Direct Response",
        "data": data,
    })

    total_input = meta.get("input_tokens", 0)
    total_output = meta.get("output_tokens", 0)
    yield _event({
        "type": "done",
        "errors": [],
        "total_tokens": {
            "input": total_input,
            "output": total_output,
            "total": total_input + total_output,
        },
        "duration": duration,
    })


_search_service = SearchService()


async def _stream_web_search_results(
    problem: str,
    run_id: str,
    num_results: int = 10,
    cancel_event: asyncio.Event | None = None,
) -> AsyncGenerator[str, None]:
    """Stream SearXNG web search results as a virtual single-phase pipeline."""
    async for chunk in _search_service.stream_web_search_results(
        problem, run_id, num_results=num_results, cancel_event=cancel_event
    ):
        yield chunk


async def run_stream(req: RunRequest, initial_state: PipelineState | None = None) -> AsyncGenerator[str, None]:
    run_id = str(uuid.uuid4())
    cancel_event = await _run_store.add(run_id)
    try:
        raw_preset = req.preset or "auto-budget"
        gate_preset_name, is_auto, auto_tier = _preset_service.resolve(raw_preset)
        auto_selected_method: str | None = None

        agent_model = initial_state.agent_model if initial_state else None
        effective_preset_name, router = _preset_service.build_router(
            gate_preset_name,
            custom_routing=req.routing,
            agent_model=agent_model,
        )

        if not req.force_pipeline:
            gate = HyperGateAgent(router)
            decision = await gate.decide(req.problem)
            if decision.action == "direct":
                async for chunk in _stream_direct_answer(router, req.problem, run_id, cancel_event):
                    yield chunk
                return
            if decision.action == "web_search":
                async for chunk in _stream_web_search_results(req.problem, run_id, cancel_event=cancel_event):
                    yield chunk
                return

            if is_auto and decision.method and not req.routing:
                effective_preset_name, router = _preset_service.build_auto_router(
                    decision.method,
                    auto_tier,
                    agent_model=agent_model,
                )
                auto_selected_method = decision.method

        pipeline = ARAPipeline(
            router=router,
            top_k=req.top_k,
            parallel_perspectives=(not req.sequential) if "multi-perspective" not in effective_preset_name else True,
            verbose=False,
            preset_name=effective_preset_name,
            source_type=req.source_type,
            domain=req.domain,
            enhance_prompt=req.enhance_prompt,
        )
        state = initial_state or PipelineState(problem=req.problem, preset_name=effective_preset_name)

        logger.info(f"Pipeline start with routing: {router.describe()}")
        start_payload: dict = {"type": "start", "preset": effective_preset_name}
        if auto_selected_method:
            start_payload["auto_selected_method"] = auto_selected_method
        yield _event(start_payload)

        if req.enhance_prompt and not state.enhanced_problem:
            try:
                await pipeline._phase_enhance_prompt(state)
                if state.enhanced_problem and state.enhanced_problem != state.problem:
                    yield _event({"type": "prompt_enhanced", "original": state.problem, "enhanced": state.enhanced_problem})
            except Exception:
                state.enhanced_problem = state.problem
                pass

        async def decompose_and_vet(state: PipelineState):
            await pipeline._phase_1_decompose(state)
            await pipeline._phase_context_vetting(state, source_type=req.source_type)

        from reasoner.application.flows import build_default_flow_registry

        phases = [
            (0, "Classification", pipeline._phase_0_classify, _ser_0),
            (1, "Decomposition", decompose_and_vet, _ser_1),
            (1.5, "Deep Read", pipeline._phase_deep_read, _ser_1_5),
        ]

        flow = build_default_flow_registry(pipeline)
        method = pipeline._get_method_from_preset()
        for step in flow.get_sequence(method):
            phases.append((step.num, step.name, step.fn, step.serializer))

        last_phase_num = max(p[0] for p in phases) if phases else 5
        synthesis_phase_num = last_phase_num + 1
        phases += [(synthesis_phase_num, "Synthesis", pipeline._phase_synthesis, _ser_5)]

        CRITICAL_PHASES = {name for _, name, _, _ in phases}
        _LEGACY_CRITICAL = {
            "Decomposition", "Perspectives", "Opening Statements",
            "Hypotheses", "Maieutic Questions", "Generation Pool",
            "Deep Research",
        }
        CRITICAL_PHASES = CRITICAL_PHASES & _LEGACY_CRITICAL

        _PHASE_ROLE_HINTS: dict[str, list[str]] = {
            "Classification": ["classification"],
            "Decomposition": ["decomposition"],
            "Deep Read": ["primary"],
            "Perspectives": ["constructive", "destructive", "systemic", "minimalist"],
            "Opening Statements": ["constructive", "destructive"],
            "Rebuttals": ["constructive", "destructive"],
            "Cross-Examination": ["systemic"],
            "Hypotheses": ["primary"],
            "Falsification Tests": ["scoring"],
            "Maieutic Questions": ["destructive"],
            "Dialectic Answers": ["constructive"],
            "Generation Pool": ["generator_1", "generator_2", "generator_3"],
            "Critic Pool": ["critic_1", "critic_2", "critic_3"],
            "Verification & Meta": ["verifier", "meta_evaluator"],
            "Deep Research": ["primary"],
            "Critique & Pruning": ["scoring"],
            "Stress Testing": ["stress_testing"],
            "Synthesis": ["synthesis"],
        }

        def _get_phase_start_models(phase_name: str) -> list[str]:
            roles = _PHASE_ROLE_HINTS.get(phase_name, [])
            models: list[str] = []
            for role in roles:
                try:
                    provider = router.get(role)
                    if provider and hasattr(provider, "model") and provider.model and provider.model not in models:
                        models.append(provider.model)
                except Exception:
                    continue
            return models

        run_start = time.monotonic()
        for num, name, fn, serializer in phases:
            if cancel_event.is_set():
                yield _event({"type": "cancelled", "message": "Pipeline stopped by user"})
                return

            phase_key = f"Phase {num}: {name}"
            state._current_phase_key = phase_key
            phase_start_models = _get_phase_start_models(name)
            start_payload: dict[str, Any] = {"type": "phase_start", "phase": num, "name": name}
            if phase_start_models:
                start_payload["models"] = phase_start_models
            yield _event(start_payload)
            phase_start = time.monotonic()
            try:
                await fn(state)
            except Exception as exc:
                import traceback

                tb = traceback.format_exc()
                print(f"Phase {num} error: {str(exc)}\n{tb}")
                logger.error("Phase %s (%s) failed: %s", num, name, exc, exc_info=True)
                err_msg = f"{type(exc).__name__}: {str(exc)[:120]}"
                state.errors.append(err_msg)
                yield _event({"type": "phase_error", "phase": num, "error": err_msg})
                if name in CRITICAL_PHASES:
                    break
                continue
            duration = time.monotonic() - phase_start
            while state.pending_events:
                ev = state.pending_events.pop(0)
                yield _event(ev)
            state.phase_durations[phase_key] = duration
            if name == "Synthesis":
                core = ""
                if state.final_solution and hasattr(state.final_solution, "core_solution"):
                    core = state.final_solution.core_solution or ""
                if core:
                    words = core.split()
                    chunk_size = 2
                    for i in range(0, len(words), chunk_size):
                        chunk = " ".join(words[i:i + chunk_size])
                        if i + chunk_size < len(words):
                            chunk += " "
                        yield _event({"type": "text_chunk", "text": chunk})
                        await asyncio.sleep(0.1)
            data = serializer(state)
            if isinstance(data, dict):
                data["tokens"] = state.phase_tokens.get(phase_key, {"input": 0, "output": 0})
                data["duration"] = duration
                phase_models = getattr(state, "_phase_models_by_key", {}).get(phase_key, [])
                if phase_models:
                    data["models"] = phase_models
                subagent_outputs = _get_phase_subagents(state, name)
                if subagent_outputs:
                    data["subagents"] = [
                        {
                            "name": s.get("agent_name", "unknown"),
                            "model": s.get("model", "unknown"),
                            "tokens_in": s.get("tokens_in", 0),
                            "tokens_out": s.get("tokens_out", 0),
                            "duration_ms": s.get("duration_ms", 0),
                            "error": s.get("error"),
                        }
                        for s in subagent_outputs
                    ]
            yield _event({
                "type": "phase_complete",
                "phase": num,
                "name": name,
                "data": data,
            })

        token_source = state.detailed_token_usage if state.detailed_token_usage else state.phase_tokens
        total_input = sum(t.get("input", 0) for t in token_source.values())
        total_output = sum(t.get("output", 0) for t in token_source.values())
        total_tokens = total_input + total_output

        try:
            from datetime import datetime

            entry = HistoryEntry(
                id=hashlib.sha256(f"{req.problem}{datetime.now().isoformat()}".encode()).hexdigest()[:16],
                problem=req.problem[:TRUNCATION.API_STORAGE],
                preset=req.preset,
                method=get_method_from_preset(req.preset),
                timestamp=datetime.now().isoformat(),
                tokens={"input": total_input, "output": total_output, "total": total_tokens},
                status="completed" if not state.errors else "error",
            )
            _save_history_entry(entry)

            try:
                from reasoner.core.memory import TaggedMemory

                tagged = TaggedMemory(HISTORY_DIR)
                method_tag = f"method:{entry.method}"
                preset_tag = f"preset:{entry.preset}"
                tagged.add(method_tag, entry.model_dump())
                tagged.add(preset_tag, entry.model_dump())
            except Exception as tag_err:
                logger.warning(f"Failed to save tagged history: {tag_err}")
        except Exception as e:
            logger.warning(f"Failed to save history: {e}")

        yield _event({
            "type": "done",
            "errors": state.errors,
            "total_tokens": {"input": total_input, "output": total_output, "total": total_tokens},
            "duration": time.monotonic() - run_start,
        })
    except Exception as exc:
        import traceback

        print(f"Pipeline error: {str(exc)}\n{traceback.format_exc()}")
        yield _event({"type": "done", "errors": [f"Pipeline processing error: {str(exc)}"]})
    finally:
        await _run_store.remove(run_id)


async def run_followup_stream(req: FollowupRequest) -> AsyncGenerator[str, None]:
    """Run the full ARA pipeline for a follow-up question with conversation context."""
    from reasoner.presets import FOLLOWUP_AGENT_MODELS

    tier = get_preset_tier(req.preset)
    agent_model = req.agent_model or FOLLOWUP_AGENT_MODELS.get(tier)
    if agent_model:
        logger.info("Follow-up tier=%s -> agent_model=%s", tier, agent_model)

    state = PipelineState(
        problem=req.question,
        preset_name=req.preset,
        conversation_id=req.conversation_id,
        conversation_history=req.history,
        previous_synthesis=req.previous_synthesis,
        turn_number=(len(req.history) // 2) + 1,
        agent_model=agent_model,
    )
    run_req = RunRequest(
        problem=req.question,
        preset=req.preset,
        top_k=req.top_k,
        sequential=req.sequential,
        enhance_prompt=req.enhance_prompt,
    )
    async for chunk in run_stream(run_req, initial_state=state):
        yield chunk

    try:
        import httpx

        async with httpx.AsyncClient() as client:
            await client.post(
                "http://127.0.0.1:50001/neuro/learn",
                json={
                    "prompt": req.question,
                    "response": (
                        state.final_solution.core_solution
                        if state.final_solution
                        else state.previous_synthesis
                    ),
                    "agent_id": req.conversation_id,
                    "metadata": {
                        "turn_number": state.turn_number,
                        "preset": req.preset,
                        "agent_model": state.agent_model,
                        "type": "followup",
                    },
                },
                timeout=5.0,
            )
    except Exception:
        pass


async def run_stream_cached(req: RunRequest) -> AsyncGenerator[str, None]:
    key = _cache_key(req)
    if not req.no_cache:
        cached = _load_cache(key)
        if cached:
            has_fatal_error = any(ev.get("type") == "done" and ev.get("errors") for ev in cached)
            if not has_fatal_error:
                for ev in cached:
                    yield _event({**ev, "cached": True} if ev.get("type") == "start" else ev)
                    if ev.get("type") in ("phase_start", "phase_complete"):
                        await asyncio.sleep(SSE_FLUSH_INTERVAL)
                return
            else:
                logger.info(f"Ignoring cached result for {key} due to stored errors.")

    collected: list[dict] = []
    async for chunk in run_stream(req):
        yield chunk
        if chunk.startswith("data: "):
            try:
                ev = json.loads(chunk[6:])
                collected.append(ev)
                if ev.get("type") == "done" and not req.no_cache:
                    _save_cache(key, collected)
            except Exception:
                pass
