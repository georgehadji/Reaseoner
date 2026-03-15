from __future__ import annotations

import asyncio
import hashlib
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator

sys.path.insert(0, str(Path(__file__).parent))

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass  # python-dotenv not installed, use system env vars

from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time
import logging

# Setup logger
logger = logging.getLogger(__name__)

# Initialize rate limiter (commented out since slowapi not available)
# limiter = Limiter(key_func=get_remote_address)

# Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response


app = FastAPI(title="ARA v2.0")

# Add security middleware
app.add_middleware(SecurityHeadersMiddleware)

# Add CORS middleware with restrictive defaults
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],  # Restrict to known origins
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    max_age=86400,  # Cache preflight for 1 day
)

from models import PipelineState
from pipeline import ARAPipeline
from llm import _REGISTRY, ProviderRouter, list_models
from presets import PRESETS, build_custom_router, get_preset, is_valid_preset_name, resolve_preset_name

# Neuro Integration
from neuro.server import create_neuro_router
app.include_router(create_neuro_router())

# New Architecture Integration
from infrastructure.persistence import get_event_store
from application.handlers import get_handler_registry
from application.commands import (
    RunPipelineCommand,
    ExecuteWidgetCommand,
)
from application.queries import (
    GetPipelineStatusQuery,
    GetHistoryQuery,
    ListPresetsQuery,
)

# Widget Integrations (legacy fallback)
from suggestions import generate_suggestions_async, SuggestionRequest

# Initialize new architecture components
_event_store = None
_handler_registry = None

def get_architecture_components():
    """Lazy initialization of new architecture components."""
    global _event_store, _handler_registry
    
    if _event_store is None:
        _event_store = get_event_store()
    
    if _handler_registry is None:
        # Create a simple router for new architecture components
        # Uses Claude as primary by default, falls back to legacy router for actual LLM calls
        from llm import build_provider, _REGISTRY
        
        # Try to get a primary provider (use first available)
        primary_provider = None
        for model_id in ["claude-sonnet-4-20250514", "gpt-4o", "gemini-2.0-flash"]:
            if model_id in _REGISTRY:
                try:
                    primary_provider = build_provider(model_id)
                    break
                except Exception:
                    continue
        
        # If no provider available, create a dummy one
        if primary_provider is None:
            from infrastructure.llm.ports import BaseLLMProvider, LLMResponse, LLMConfig, Message
            from infrastructure.llm.exceptions import LLMError
            
            class DummyProvider(BaseLLMProvider):
                async def _complete_impl(self, messages, config):
                    return LLMResponse(
                        content="Dummy provider - configure API keys",
                        model_used="dummy",
                        tokens_prompt=0,
                        tokens_completion=0,
                    )
                
                async def _complete_stream_impl(self, messages, config):
                    yield "Dummy provider"
                
                @property
                def provider_name(self):
                    return "dummy"
            
            primary_provider = DummyProvider(model="dummy")
        
        from infrastructure.llm.new_pipeline import NewARAPipeline
        _handler_registry = get_handler_registry(primary_provider, _event_store)
    
    return _event_store, _handler_registry


def _filter_routing(routing: dict[str, str], primary_id: str) -> dict[str, str]:
    """Drop routing entries whose API key is missing; fall back to primary."""
    import os
    filtered = {}
    for role, model_id in routing.items():
        entry = _REGISTRY.get(model_id, {})
        env = entry.get("env")
        if env and not os.environ.get(env):
            continue  # no key → omit, ProviderRouter falls back to primary
        filtered[role] = model_id
    return filtered

# Per-run cancellation tracking.
# Maps run_id → True when that run has been asked to stop.
# Using a dict (not a bool) isolates concurrent requests so that
# stopping one run cannot accidentally cancel another.
_cancelled_runs: dict[str, bool] = {}
_active_run_id: str | None = None  # ID of the currently streaming run

# ─────────────────────────────────────────────────────────────────────
# CACHE
# ─────────────────────────────────────────────────────────────────────

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)


def _cache_key(req: "RunRequest") -> str:
    payload = json.dumps({
        "problem": req.problem,
        "preset":  req.preset,
        "top_k":   req.top_k,
        "routing": req.routing,
    }, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:20]


def _load_cache(key: str) -> list[dict] | None:
    path = CACHE_DIR / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def _save_cache(key: str, events: list[dict]) -> None:
    path = CACHE_DIR / f"{key}.json"
    path.write_text(json.dumps(events), encoding="utf-8")


def _get_method_from_preset(preset: str) -> str:
    """Extract method name from preset."""
    if "debate" in preset: return "debate"
    if "iterative" in preset: return "iterative"
    if "jury" in preset or "orchestrated" in preset: return "jury"
    if "research" in preset: return "research"
    if "scientific" in preset: return "scientific"
    if "socratic" in preset: return "socratic"
    return "multi-perspective"


class RunRequest(BaseModel):
    problem: str
    preset: str = "claude-only"
    routing: dict[str, str] | None = None
    top_k: int = 2
    sequential: bool = True  # Cost-effective: sequential by default in UI
    no_cache: bool = False
    source_type: str = "general"  # For iterative RAG: general, academic, social, news, code
    domain: str | None = None  # For domain-specific search

    @field_validator('problem')
    @classmethod
    def validate_problem(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError('Problem cannot be empty')
        if len(v) > 10000:  # Limit problem length
            raise ValueError('Problem too long (max 10000 characters)')
        # Basic sanitization - remove potential injection characters
        # Note: This is basic; real implementation would be more comprehensive
        if '\x00' in v:  # Null byte
            raise ValueError('Invalid characters in problem')
        return v

    @field_validator('preset')
    @classmethod
    def validate_preset(cls, v: str) -> str:
        if not is_valid_preset_name(v):
            raise ValueError(f'Invalid preset: {v}')
        return resolve_preset_name(v)


# ─────────────────────────────────────────────────────────────────────
# SERIALIZERS — one per phase
# ─────────────────────────────────────────────────────────────────────

def _is_orchestrated(preset: str) -> bool:
    return preset in ("jury", "jury-budget", "jury-balanced", "jury-premium", "orchestrated")

def _is_debate(preset: str) -> bool:
    return "debate" in preset

def _is_scientific(preset: str) -> bool:
    return "scientific" in preset

def _is_socratic(preset: str) -> bool:
    return "socratic" in preset

def _is_iterative(preset: str) -> bool:
    return "iterative" in preset

def _get_v(obj, key, default=None):
    if obj is None: return default
    if isinstance(obj, dict): return obj.get(key, default)
    return getattr(obj, key, default)

def _ser_0(state: PipelineState) -> dict:
    tt = _get_v(state, 'task_type')
    return {
        "task_type": tt.value if hasattr(tt, 'value') else str(tt or "unknown"),
        "rationale": _get_v(state, 'task_type_rationale', ''),
        "language": _get_v(state, 'language', 'English'),
        "tokens": state.phase_tokens.get("Phase 0: Classification", {"input": 0, "output": 0}),
    }

def _ser_1(state: PipelineState) -> dict:
    dec = _get_v(state, 'decomposition')
    if not dec: return {}

    # Handle both object and dict formats
    sub_problems = _get_v(dec, 'sub_problems', [])
    assumptions = _get_v(dec, 'assumptions', [])

    return {
        "sub_problems": [
            {
                "id": _get_v(sp, 'id', ''),
                "description": _get_v(sp, 'description', ''),
                "constraints": _get_v(sp, 'constraints', [])
            } for sp in sub_problems
        ],
        "assumptions": [
            {
                "text": _get_v(a, 'text', ''),
                "label": (lambda x: x.value if hasattr(x, 'value') else str(x))(_get_v(a, 'label', 'UNKNOWN')),
                "rationale": _get_v(a, 'rationale', '')
            } for a in assumptions
        ],
        "failure_modes": _get_v(dec, 'failure_modes', []),
        "tokens": state.phase_tokens.get("Phase 1: Decomposition", {"input": 0, "output": 0}),
    }

def _ser_2(state: PipelineState) -> dict:
    candidates = _get_v(state, 'candidates', [])
    gen_candidates = _get_v(state, 'generation_candidates', [])

    result = {
        "candidates": [
            {
                "perspective": (lambda x: x.value if hasattr(x, 'value') else str(x))(_get_v(c, 'perspective', '')),
                "content": _get_v(c, 'content', ''),
                "key_insights": _get_v(c, 'key_insights', []),
                "model_used": _get_v(c, 'model_used', ''),
            } for c in candidates
        ],
        "tokens": {"input": 0, "output": 0}, # Placeholder
    }

    if gen_candidates:
        result["generation_candidates"] = [
            {
                "generator_id": _get_v(gc, 'generator_id', ''),
                "model_used": _get_v(gc, 'model_used', ''),
                "solution": _get_v(gc, 'solution', ''),
                "confidence": _get_v(gc, 'confidence', 0),
                "key_claims": _get_v(gc, 'key_claims', []),
                "approach_summary": _get_v(gc, 'approach_summary', ''),
            } for gc in gen_candidates
        ]

    # Add other states safely
    for field in ['scientific_state', 'socratic_state', 'debate_rounds', 'web_discovery_results']:
        val = _get_v(state, field)
        if val: result[field] = val

    return result

def _ser_3(state: PipelineState) -> dict:
    scores = _get_v(state, 'scores', [])
    top_candidates = _get_v(state, 'top_candidates', [])
    top_perspectives = {(_get_v(c, 'perspective').value if hasattr(_get_v(c, 'perspective'), 'value') else str(_get_v(c, 'perspective'))) for c in top_candidates}

    result = {
        "scores": [
            {
                "perspective": (lambda x: x.value if hasattr(x, 'value') else str(x))(_get_v(s, 'perspective', '')),
                "logical_consistency": _get_v(s, 'logical_consistency', 0),
                "evidence_support": _get_v(s, 'evidence_support', 0),
                "failure_resilience": _get_v(s, 'failure_resilience', 0),
                "feasibility": _get_v(s, 'feasibility', 0),
                "total": round(_get_v(s, 'total', 0), 2),
                "bias_flags": _get_v(s, 'bias_flags', []),
                "steel_man": _get_v(s, 'steel_man', ''),
                "is_top": (lambda x: x.value if hasattr(x, 'value') else str(x))(_get_v(s, 'perspective')) in top_perspectives,
            } for s in sorted(scores, key=lambda x: _get_v(x, 'total', 0), reverse=True)
        ],
        "tokens": state.phase_tokens.get("Phase 3: Critique & Pruning", {"input": 0, "output": 0}),
    }

    return result

def _ser_4(state: PipelineState) -> dict:
    stress = _get_v(state, 'stress_results', [])
    verif = _get_v(state, 'verification_results', [])
    meta = _get_v(state, 'meta_evaluation')

    result = {
        "tests": [
            {
                "scenario": (lambda x: x.value if hasattr(x, 'value') else str(x))(_get_v(sr, 'scenario', '')),
                "survival_rate": _get_v(sr, 'survival_rate', 0),
                "failure_mode": _get_v(sr, 'failure_mode', ''),
                "recovery_path": _get_v(sr, 'recovery_path', ''),
            } for sr in stress
        ],
        "tokens": state.phase_tokens.get("Phase 4: Stress Testing", {"input": 0, "output": 0}),
    }

    if verif:
        result["verification_results"] = [
            {
                "claim": _get_v(vr, 'claim', ''),
                "source_generator": _get_v(vr, 'source_generator', ''),
                "verdict": (lambda x: x.value if hasattr(x, 'value') else str(x))(_get_v(vr, 'verdict', '')),
                "evidence": _get_v(vr, 'evidence', ''),
                "confidence": _get_v(vr, 'confidence', 0),
            } for vr in verif
        ]

    if meta:
        result["meta_evaluation"] = {
            "critic_reliability": _get_v(meta, 'critic_reliability', {}),
            "bias_analysis": _get_v(meta, 'bias_analysis', {}),
            "agreement_rate": _get_v(meta, 'agreement_rate', 0),
            "most_reliable_critic": _get_v(meta, 'most_reliable_critic', ''),
            "least_reliable_critic": _get_v(meta, 'least_reliable_critic', ''),
            "meta_insight": _get_v(meta, 'meta_insight', ''),
        }

    return result

def _ser_5(state: PipelineState) -> dict:
    fs = _get_v(state, 'final_solution')
    if not fs: return {}

    meta = _get_v(fs, 'meta_audit', {})

    # Action blueprint handling
    raw_bp = _get_v(fs, 'action_blueprint', [])
    clean_bp = []
    for step in (raw_bp if isinstance(raw_bp, list) else []):
        clean_bp.append({
            "step": _get_v(step, 'step', '?'),
            "action": _get_v(step, 'action', ''),
            "time_horizon": _get_v(step, 'time_horizon', ''),
            "go_criteria": _get_v(step, 'go_criteria', ''),
            "fallback": _get_v(step, 'fallback', '')
        })

    # Claim labels handling
    raw_labels = _get_v(fs, 'claim_labels', {})
    clean_labels = {k: (v.value if hasattr(v, 'value') else str(v)) for k, v in (raw_labels.items() if isinstance(raw_labels, dict) else {})}

    return {
        "core_solution": _get_v(fs, 'core_solution', ''),
        "critical_insights": _get_v(fs, 'critical_insights', []),
        "action_blueprint": clean_bp,
        "open_questions": _get_v(fs, 'open_questions', []),
        "claim_labels": clean_labels,
        "meta_audit": {
            "most_dangerous_assumption": _get_v(meta, 'most_dangerous_assumption', ''),
            "dominant_bias": _get_v(meta, 'dominant_bias', ''),
            "remaining_uncertainty": _get_v(meta, 'remaining_uncertainty', ''),
            "assumption_failure_impact": _get_v(meta, 'assumption_failure_impact', ''),
            "non_obvious_insight": _get_v(meta, 'non_obvious_insight', ''),
        },
        "tokens": {"input": 0, "output": 0}
    }# ─────────────────────────────────────────────────────────────────────
# SSE STREAM
# ─────────────────────────────────────────────────────────────────────

def _event(data: dict) -> str:
    def json_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    return f"data: {json.dumps(data, default=json_serializer)}\n\n"


async def run_stream(req: RunRequest) -> AsyncGenerator[str, None]:
    global _active_run_id
    # Assign a unique ID to this run so stop requests can target it precisely.
    run_id = str(uuid.uuid4())
    _active_run_id = run_id
    try:
        if req.routing:
            filtered = _filter_routing(req.routing, "claude-sonnet")
            router = build_custom_router(filtered)
        else:
            preset = get_preset(req.preset or "claude-only")
            filtered_routing = _filter_routing(preset.routing, preset.primary_id)
            router = ProviderRouter.from_model_ids(
                primary_id=preset.primary_id,
                routing=filtered_routing,
            )

        pipeline = ARAPipeline(
            router=router,
            top_k=req.top_k,
            parallel_perspectives=not req.sequential,
            verbose=False,
            preset_name=req.preset,
            source_type=req.source_type,
            domain=req.domain,
        )
        state = PipelineState(problem=req.problem, preset_name=req.preset)

        yield _event({"type": "start", "routing": router.describe()})

        async def decompose_and_vet(state: PipelineState):
            await pipeline._phase_1_decompose(state)
            await pipeline._phase_context_vetting(state, source_type=req.source_type)

        # Iterative method wrapper functions with reflexion memory
        async def iterative_round_1_generate(state: PipelineState):
            await pipeline._phase_2_perspectives(state, use_reflexion=True)

        async def iterative_round_1_critique(state: PipelineState):
            await pipeline._phase_3_critique(state)
            # Store insights for next round
            new_memories = [s.steel_man for s in state.scores if s.steel_man]
            state.reflexion_memory.extend(new_memories)

        async def iterative_round_2_generate(state: PipelineState):
            state.candidates, state.scores, state.top_candidates = [], [], []
            await pipeline._phase_2_perspectives(state, use_reflexion=True)

        async def iterative_round_2_critique(state: PipelineState):
            await pipeline._phase_3_critique(state)
            # Store insights for next round
            new_memories = [s.steel_man for s in state.scores if s.steel_man]
            state.reflexion_memory.extend(new_memories)

        async def iterative_round_3_generate(state: PipelineState):
            state.candidates, state.scores, state.top_candidates = [], [], []
            await pipeline._phase_2_perspectives(state, use_reflexion=True)

        async def iterative_round_3_critique(state: PipelineState):
            await pipeline._phase_3_critique(state)
            # Final round - keep the results for synthesis

        # Define phase sequence based on method
        phases = [
            (0, "Classification",     pipeline._phase_0_classify,    _ser_0),
            (1, "Decomposition",      decompose_and_vet,             _ser_1),
            (1.5, "Deep Read",        pipeline._phase_deep_read,    _ser_1),
        ]

        if _is_debate(req.preset):
            phases += [
                (2, "Opening Statements",  pipeline._phase_debate_opening,    _ser_2),
                (3, "Rebuttals",           pipeline._phase_debate_rebuttal,   _ser_3),
                (4, "Cross-Examination",   pipeline._phase_debate_judge,      _ser_4),
            ]
        elif _is_scientific(req.preset):
            phases += [
                (2, "Hypotheses",          pipeline._phase_scientific_hypothesize,  _ser_2),
                (3, "Falsification Tests", pipeline._phase_scientific_test,         _ser_3),
                (4, "Stress Testing",      pipeline._phase_4_stress_test,           _ser_4),
            ]
        elif _is_socratic(req.preset):
            phases += [
                (2, "Maieutic Questions",  pipeline._phase_socratic_question,    _ser_2),
                (3, "Dialectic Answers",   pipeline._phase_socratic_answer,      _ser_3),
            ]
        elif _is_orchestrated(req.preset):
            phases += [
                (2, "Generation Pool",    pipeline._phase_jury_generate,             _ser_2),
                (3, "Critic Pool",        pipeline._phase_jury_critique,             _ser_3),
                (4, "Verification & Meta", pipeline._phase_jury_verify_and_meta_eval, _ser_4),
            ]
        elif req.preset and "research" in req.preset:
            phases += [
                (2, "Deep Research",      pipeline._phase_research_web_search,   _ser_2),
                (3, "Perspectives",       pipeline._phase_2_perspectives,        _ser_2), # Using _ser_2 for both to output their respective states. Wait, _ser_2 doesn't output web discovery results. Let's use _ser_1 for Deep Research as it outputs web discovery results. Wait, _ser_1 outputs decomposition. We'll need a custom serializer or just use _ser_2.
                (4, "Critique & Pruning", pipeline._phase_3_critique,            _ser_3),
            ]
        elif req.preset and "iterative" in req.preset:
            # Iterative method: 3 rounds of generate -> critique with reflexion memory
            phases += [
                (2, "Round 1: Generate",  iterative_round_1_generate,     _ser_2),
                (3, "Round 1: Critique",  iterative_round_1_critique,     _ser_3),
                (4, "Round 2: Refine",    iterative_round_2_generate,     _ser_2),
                (5, "Round 2: Critique",  iterative_round_2_critique,     _ser_3),
                (6, "Round 3: Final",     iterative_round_3_generate,     _ser_2),
                (7, "Round 3: Critique",  iterative_round_3_critique,     _ser_3),
            ]
        else:
            # Standard flow (Multi-Perspective)
            phases += [
                (2, "Perspectives",       pipeline._phase_2_perspectives,     _ser_2),
                (3, "Critique & Pruning", pipeline._phase_3_critique,    _ser_3),
                (4, "Stress Testing",     pipeline._phase_4_stress_test, _ser_4),
            ]
        
        # All methods end with Synthesis
        # Determine the next phase number after the last phase
        last_phase_num = max(p[0] for p in phases) if phases else 5
        synthesis_phase_num = last_phase_num + 1
        phases += [(synthesis_phase_num, "Synthesis", pipeline._phase_synthesis, _ser_5)]

        for num, name, fn, serializer in phases:
            # Check only this run's cancellation flag, not a shared global.
            # This prevents a stop request for one tab from killing another tab's run.
            if _cancelled_runs.pop(run_id, False):
                yield _event({"type": "cancelled", "message": "Pipeline stopped by user"})
                return

            yield _event({"type": "phase_start", "phase": num, "name": name})
            try:
                await fn(state)
            except Exception as exc:
                import traceback
                print(f"Phase {num} error: {str(exc)}\n{traceback.format_exc()}")
                yield _event({"type": "phase_error", "phase": num, "error": f"Processing error in {name.lower()} phase: {str(exc)}"})
                continue
            yield _event({
                "type": "phase_complete",
                "phase": num,
                "name": name,
                "data": serializer(state),
            })

        # Calculate total tokens
        total_input = sum(t.get("input", 0) for t in state.phase_tokens.values())
        total_output = sum(t.get("output", 0) for t in state.phase_tokens.values())
        total_tokens = total_input + total_output

        # Save to history
        try:
            from datetime import datetime
            entry = HistoryEntry(
                id=hashlib.sha256(f"{req.problem}{datetime.now().isoformat()}".encode()).hexdigest()[:16],
                problem=req.problem[:200],  # Truncate for storage
                preset=req.preset,
                method=_get_method_from_preset(req.preset),
                timestamp=datetime.now().isoformat(),
                tokens={"input": total_input, "output": total_output, "total": total_tokens},
                status="completed" if not state.errors else "error",
            )
            _save_history_entry(entry)
        except Exception as e:
            logger.warning(f"Failed to save history: {e}")

        yield _event({
            "type": "done",
            "phase_models": state.phase_models,
            "errors": state.errors,
            "total_tokens": {"input": total_input, "output": total_output, "total": total_tokens},
        })
    except Exception as exc:
        # Log the full error server-side but return more specific message
        import traceback
        print(f"Pipeline error: {str(exc)}\n{traceback.format_exc()}")
        yield _event({"type": "done", "errors": [f"Pipeline processing error: {str(exc)}"]})
    finally:
        # Clean up this run's cancel entry regardless of how the generator exits.
        _cancelled_runs.pop(run_id, None)


# ─────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────

async def run_stream_cached(req: RunRequest) -> AsyncGenerator[str, None]:
    key = _cache_key(req)
    if not req.no_cache:
        cached = _load_cache(key)
        if cached:
            # Check if cached results contain critical errors
            has_fatal_error = any(ev.get("type") == "done" and ev.get("errors") for ev in cached)
            if not has_fatal_error:
                for ev in cached:
                    yield _event({**ev, "cached": True} if ev.get("type") == "start" else ev)
                    if ev.get("type") in ("phase_start", "phase_complete"):
                        await asyncio.sleep(0.02)
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


@app.post("/api/run")
async def run_pipeline(request: Request, req: RunRequest):
    return StreamingResponse(
        run_stream_cached(req),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.delete("/api/cache")
async def clear_cache():
    cleared = sum(1 for f in CACHE_DIR.glob("*.json") if f.unlink() or True)
    return {"cleared": cleared}


@app.post("/api/stop")
async def stop_pipeline():
    # Mark the currently active run (if any) as cancelled.
    # Only affects that specific run — other concurrent runs are unaffected.
    if _active_run_id is not None:
        _cancelled_runs[_active_run_id] = True
    return {"status": "stop requested"}


# ─────────────────────────────────────────────────────────────────────
# FILE UPLOADS
# ─────────────────────────────────────────────────────────────────────

from uploader import save_uploaded_file, get_file_text, delete_file, list_uploads


@app.post("/api/upload")
async def upload_file(request: Request):
    """Upload a file and extract its text content."""
    try:
        form = await request.form()
        file = form.get("file")
        if not file:
            return {"success": False, "error": "No file provided"}
        
        content = await file.read()
        result = await save_uploaded_file(content, file.filename)
        return result
        
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return {"success": False, "error": str(e)}


@app.get("/api/uploads")
async def get_uploads():
    """List all uploaded files."""
    return {"files": list_uploads()}


@app.get("/api/upload/{file_id}")
async def get_uploaded_file(file_id: str):
    """Get text content of an uploaded file."""
    text = get_file_text(file_id)
    if text is None:
        return {"error": "File not found"}, 404
    return {"file_id": file_id, "text": text}


@app.delete("/api/upload/{file_id}")
async def delete_uploaded_file(file_id: str):
    """Delete an uploaded file."""
    success = delete_file(file_id)
    if not success:
        return {"error": "File not found"}, 404
    return {"status": "deleted"}


@app.get("/api/presets")
async def api_presets():
    return {
        name: {
            "name": p.name,
            "description": p.description,
            "available": not p.missing_keys(),
            "missing_keys": p.missing_keys(),
        }
        for name, p in PRESETS.items()
    }


@app.get("/api/models")
async def api_models():
    return list_models()


# ─────────────────────────────────────────────────────────────────────
# EXTERNAL CONTEXT INTEGRATION
# ─────────────────────────────────────────────────────────────────────

class ContextAnalysisRequest(BaseModel):
    """Request model for running pipeline with external context."""
    problem: str
    context: list[dict[str, Any]]  # List of {url, title, content, facts}
    method: str = "jury"  # jury or multi-perspective
    preset: str = "jury-premium"
    top_k: int = 2
    domain: str | None = None  # For domain-specific search

    @field_validator('problem')
    @classmethod
    def validate_problem(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError('Problem cannot be empty')
        return v

    @field_validator('method')
    @classmethod
    def validate_method(cls, v: str) -> str:
        if v not in ("jury", "multi-perspective"):
            raise ValueError('Method must be "jury" or "multi-perspective"')
        return v


@app.post("/api/run-with-context")
async def run_with_context(req: ContextAnalysisRequest):
    """
    Run the Reasoner pipeline with external context.
    
    This endpoint accepts collected research context
    (facts, URLs, summaries) and runs deep, validated analysis.
    """
    try:
        # Get preset
        preset = get_preset(req.preset)
        
        # Build router from preset
        filtered_routing = _filter_routing(preset.routing, preset.primary_id)
        router = ProviderRouter.from_model_ids(
            primary_id=preset.primary_id,
            routing=filtered_routing,
        )
        
        # Create pipeline
        pipeline = ARAPipeline(
            router=router,
            top_k=req.top_k,
            parallel_perspectives=True,
            verbose=False,
            preset_name=req.preset,
            domain=req.domain if hasattr(req, 'domain') else None,
        )
        
        # Create state with the external context
        state = PipelineState(problem=req.problem, preset_name=req.preset)
        
        # Inject external context directly into the state
        # This bypasses the normal search/vetting phases
        state.web_discovery_results = req.context
        state.vetted_context = req.context
        
        # Run the appropriate method pipeline
        if req.method == "jury":
            await pipeline._phase_jury_generate(state)
            await pipeline._phase_jury_critique(state)
            await pipeline._phase_jury_verify_and_meta_eval(state)
        else:
            # Multi-perspective
            await pipeline._phase_2_perspectives(state)
            await pipeline._phase_3_critique(state)
            await pipeline._phase_4_stress_test(state)
        
        # Run synthesis
        await pipeline._phase_synthesis(state)
        
        # Return the final solution
        if state.final_solution:
            return {
                "success": True,
                "solution": state.final_solution,
                "method": req.method,
                "preset": req.preset,
            }
        else:
            return {"success": False, "error": "Failed to generate solution",}
            
    except Exception as exc:
        import traceback
        logger.error(f"Context analysis failed: {exc}\n{traceback.format_exc()}")
        return {"success": False, "error": str(exc),}


@app.get("/api/ui/status")
async def ui_status():
    """Check if UI integration is available."""
    return {
        "available": True,
        "endpoints": {
            "run_with_context": "/api/run-with-context",
        },
        "supported_methods": ["jury", "multi-perspective"],
        "supported_presets": list(PRESETS.keys()),
    }


# ─────────────────────────────────────────────────────────────────────
# WIDGETS & SMART FEATURES
# ─────────────────────────────────────────────────────────────────────

class SuggestionRequestModel(BaseModel):
    query: str
    chat_history: list[list[str]] | None = None
    max_suggestions: int = 5


@app.post("/api/suggestions")
async def get_suggestions(req: SuggestionRequestModel):
    """Get smart search suggestions based on query."""
    try:
        request = SuggestionRequest(
            query=req.query,
            chat_history=req.chat_history,
            max_suggestions=req.max_suggestions,
        )
        response = await generate_suggestions_async(request)
        return {"suggestions": response.suggestions, "query": response.query}
    except Exception as e:
        logger.error(f"Suggestions error: {e}")
        return {"suggestions": [], "query": req.query}


# ─────────────────────────────────────────────────────────────────────
# NEW ARCHITECTURE WIDGET ENDPOINTS
# ─────────────────────────────────────────────────────────────────────

@app.post("/api/widget/execute")
async def execute_widget(req: ExecuteWidgetCommand):
    """
    Execute widget using new architecture.
    
    Supports auto-detection from query or explicit widget execution.
    """
    try:
        _, handler_registry = get_architecture_components()
        
        result = await handler_registry.handle_command(req)
        
        return result
    except Exception as e:
        logger.error(f"Widget execution error: {e}")
        return {"error": str(e), "detected": False}


@app.get("/api/widgets/list")
async def list_widgets():
    """List all available widgets."""
    try:
        from infrastructure.widgets import get_widget_registry
        
        registry = get_widget_registry()
        widgets = registry.list_widgets()
        
        return {"widgets": widgets, "total": len(widgets)}
    except Exception as e:
        logger.error(f"List widgets error: {e}")
        return {"error": str(e), "widgets": []}


@app.get("/api/widgets/detect")
async def detect_widgets(query: str = ""):
    """Detect widgets for a query."""
    try:
        from infrastructure.widgets import get_widget_registry
        
        registry = get_widget_registry()
        detections = await registry.detect_widgets(query)
        
        return {
            "detected": len(detections) > 0,
            "widgets": [d.to_dict() for d in detections],
        }
    except Exception as e:
        logger.error(f"Widget detection error: {e}")
        return {"detected": False, "widgets": []}


# ─────────────────────────────────────────────────────────────────────
# EVENT STORE ENDPOINTS
# ─────────────────────────────────────────────────────────────────────

@app.get("/api/events/stats")
async def get_event_stats():
    """Get event store statistics."""
    try:
        event_store, _ = get_architecture_components()
        stats = await event_store.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Event stats error: {e}")
        return {"error": str(e)}


@app.get("/api/pipelines")
async def list_pipelines(
    limit: int = 50,
    offset: int = 0,
    status: str | None = None,
):
    """List pipelines from event store."""
    try:
        event_store, _ = get_architecture_components()
        pipelines = await event_store.list_pipelines(
            limit=limit,
            offset=offset,
            status=status,
        )
        return {"pipelines": pipelines, "total": len(pipelines)}
    except Exception as e:
        logger.error(f"List pipelines error: {e}")
        return {"error": str(e), "pipelines": []}


@app.get("/api/pipelines/{pipeline_id}")
async def get_pipeline_status(pipeline_id: str):
    """Get pipeline status from event store."""
    try:
        event_store, handler_registry = get_architecture_components()
        
        query = GetPipelineStatusQuery(
            query_id=f"status-{pipeline_id}",
            timestamp=time.time(),
            pipeline_id=pipeline_id,
        )
        
        result = await handler_registry.handle_query(query)
        return result
    except Exception as e:
        logger.error(f"Get pipeline error: {e}")
        return {"error": str(e)}


@app.delete("/api/pipelines/{pipeline_id}")
async def delete_pipeline(pipeline_id: str):
    """Delete pipeline and all events (GDPR compliance)."""
    try:
        event_store, _ = get_architecture_components()
        await event_store.delete_aggregate(pipeline_id)
        return {"status": "deleted", "pipeline_id": pipeline_id}
    except Exception as e:
        logger.error(f"Delete pipeline error: {e}")
        return {"error": str(e)}


# ─────────────────────────────────────────────────────────────────────
# LEGACY WIDGET ENDPOINTS (Fallback)
# ─────────────────────────────────────────────────────────────────────

class WeatherRequest(BaseModel):
    location: str


@app.get("/api/weather")
async def get_weather(location: str = ""):
    """Get weather data for a location (legacy endpoint)."""
    try:
        if not location:
            return {"error": "Location parameter required"}, 400
        from widgets import get_weather_data
        weather_data = get_weather_data(location)
        return weather_data
    except Exception as e:
        logger.error(f"Weather error: {e}")
        return {"error": str(e)}, 500


class StockRequest(BaseModel):
    symbol: str


@app.get("/api/stocks")
async def get_stock(symbol: str = ""):
    """Get stock data for a symbol (legacy endpoint)."""
    try:
        if not symbol:
            return {"error": "Symbol parameter required"}, 400
        from widgets import get_stock_data
        stock_data = get_stock_data(symbol.upper())
        return stock_data
    except Exception as e:
        logger.error(f"Stock error: {e}")
        return {"error": str(e)}, 500


class CalculationRequest(BaseModel):
    expression: str


@app.post("/api/calculate")
async def calculate(req: CalculationRequest):
    """Evaluate a mathematical expression (legacy endpoint)."""
    try:
        from widgets import calculate_expression
        result = calculate_expression(req.expression)
        return result
    except Exception as e:
        logger.error(f"Calculation error: {e}")
        return {"error": str(e), "valid": False}


class DiscoverRequest(BaseModel):
    topic: str = "tech"
    mode: str = "normal"


@app.get("/api/discover")
async def discover(topic: str = "tech", mode: str = "normal"):
    """Get trending content for a topic (legacy endpoint)."""
    try:
        from widgets import get_discover_content
        content = get_discover_content(topic, mode)
        return content
    except Exception as e:
        logger.error(f"Discover error: {e}")
        return {"error": str(e), "results": []}


# ─────────────────────────────────────────────────────────────────────
# SEARCH HISTORY
# ─────────────────────────────────────────────────────────────────────

HISTORY_DIR = Path(__file__).parent / "history"
HISTORY_DIR.mkdir(exist_ok=True)


class HistoryEntry(BaseModel):
    id: str
    problem: str
    preset: str
    method: str
    timestamp: str
    tokens: dict[str, int]
    status: str  # "completed", "error", "cancelled"


def _list_history() -> list[HistoryEntry]:
    """List all history entries, sorted by timestamp descending."""
    entries = []
    for f in HISTORY_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            entries.append(HistoryEntry(**data))
        except Exception:
            pass
    return sorted(entries, key=lambda x: x.timestamp, reverse=True)


@app.get("/api/history")
async def get_history(limit: int = 50, offset: int = 0):
    """Get search history."""
    all_history = _list_history()
    return {
        "total": len(all_history),
        "entries": all_history[offset:offset + limit],
    }


@app.get("/api/history/{entry_id}")
async def get_history_entry(entry_id: str):
    """Get a specific history entry."""
    path = HISTORY_DIR / f"{entry_id}.json"
    if not path.exists():
        return {"error": "Entry not found"}, 404
    return json.loads(path.read_text(encoding="utf-8"))


@app.delete("/api/history/{entry_id}")
async def delete_history_entry(entry_id: str):
    """Delete a history entry."""
    path = HISTORY_DIR / f"{entry_id}.json"
    if not path.exists():
        return {"error": "Entry not found"}, 404
    path.unlink()
    return {"status": "deleted"}


@app.delete("/api/history")
async def clear_history():
    """Clear all history."""
    cleared = sum(1 for f in HISTORY_DIR.glob("*.json") if f.unlink() or True)
    return {"cleared": cleared}


def _save_history_entry(entry: HistoryEntry) -> None:
    """Save a history entry to disk."""
    path = HISTORY_DIR / f"{entry.id}.json"
    path.write_text(json.dumps(entry.model_dump(), ensure_ascii=False), encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────
# WEBSOCKET ENDPOINTS
# ─────────────────────────────────────────────────────────────────────

from infrastructure.websocket import (
    get_websocket_manager,
    websocket_endpoint,
    setup_event_bus_integration,
)


@app.websocket("/ws")
async def websocket_connect(
    websocket: WebSocket,
    pipeline_id: str | None = None,
):
    """
    WebSocket endpoint for real-time pipeline updates.
    
    Usage:
        ws://localhost:8000/ws
        ws://localhost:8000/ws?pipeline_id=xxx
    
    Messages:
        - subscribe: {"type": "subscribe", "pipeline_id": "xxx"}
        - unsubscribe: {"type": "unsubscribe", "pipeline_id": "xxx"}
        - ping: {"type": "ping"}
    
    Responses:
        - event: Pipeline domain events
        - progress: Phase progress updates
        - complete: Pipeline completion
        - error: Error notifications
    """
    await websocket_endpoint(websocket, pipeline_id)


@app.websocket("/ws/pipeline/{pipeline_id}")
async def pipeline_websocket(
    websocket: WebSocket,
    pipeline_id: str,
):
    """
    WebSocket endpoint for specific pipeline.
    
    Automatically subscribes to pipeline updates.
    """
    await websocket_endpoint(websocket, pipeline_id)


@app.get("/api/websocket/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics."""
    manager = get_websocket_manager()
    return {
        "active_connections": manager.get_connection_count(),
        "subscriptions": {
            pipeline_id: manager.get_subscriber_count(pipeline_id)
            for pipeline_id in manager.subscriptions.keys()
        },
    }


# ─────────────────────────────────────────────────────────────────────
# STARTUP EVENTS
# ─────────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    """Initialize components on startup."""
    # Lazy initialization - components will be initialized on first use
    # This prevents startup failures due to missing dependencies
    logger.info("Reasoner startup complete")
    logger.info("Web UI: http://localhost:8000")
    logger.info("API Docs: http://localhost:8000/docs")
    logger.info("WebSocket: ws://localhost:8000/ws")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global _event_store
    if _event_store and hasattr(_event_store, 'close'):
        _event_store.close()
    
    logger.info("Reasoner shutdown complete")


# Serve frontend last (catches all unmatched routes)
app.mount("/", StaticFiles(directory="ui", html=True), name="ui")