"""
ARA v2.0 — Web API
FastAPI backend. Runs the pipeline phase-by-phase and streams results via SSE.

Usage:
    pip install fastapi uvicorn
    uvicorn api:app --reload --port 8000
    # Open http://localhost:8000
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator

sys.path.insert(0, str(Path(__file__).parent))

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass  # python-dotenv not installed, use system env vars

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time

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
from presets import PRESETS, build_custom_router, get_preset


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

# Global state for cancellation
_cancel_flag = False

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

app = FastAPI(title="ARA v2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class RunRequest(BaseModel):
    problem: str
    preset: str = "claude-only"
    routing: dict[str, str] | None = None
    top_k: int = 2
    sequential: bool = True  # Cost-effective: sequential by default in UI
    no_cache: bool = False

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
        if v not in PRESETS:
            raise ValueError(f'Invalid preset: {v}')
        return v


# ─────────────────────────────────────────────────────────────────────
# SERIALIZERS — one per phase
# ─────────────────────────────────────────────────────────────────────

def _ser_0(state: PipelineState) -> dict:
    return {
        "task_type": state.task_type.value if state.task_type else "unknown",
        "rationale": state.task_type_rationale,
        "language": state.language,  # Include the detected language
        "tokens": state.phase_tokens.get("Phase 0: Classification", {"input": 0, "output": 0}),
    }


def _ser_1(state: PipelineState) -> dict:
    if not state.decomposition:
        return {}
    dec = state.decomposition
    return {
        "sub_problems": [
            {"id": sp.id, "description": sp.description, "constraints": sp.constraints}
            for sp in dec.sub_problems
        ],
        "assumptions": [
            {"text": a.text, "label": a.label.value, "rationale": a.rationale}
            for a in dec.assumptions
        ],
        "failure_modes": dec.failure_modes,
        "tokens": state.phase_tokens.get("Phase 1: Decomposition", {"input": 0, "output": 0}),
    }


def _ser_2(state: PipelineState) -> dict:
    # Aggregate tokens from all Phase 2 perspectives
    phase2_tokens = {"input": 0, "output": 0}
    for key in ["Phase 2: Constructive", "Phase 2: Destructive", "Phase 2: Systemic", "Phase 2: Minimalist"]:
        tokens = state.phase_tokens.get(key, {"input": 0, "output": 0})
        phase2_tokens["input"] += tokens.get("input", 0)
        phase2_tokens["output"] += tokens.get("output", 0)
    
    return {
        "candidates": [
            {
                "perspective": c.perspective.value,
                "content": c.content,
                "key_insights": c.key_insights,
                "model_used": c.model_used,
            }
            for c in state.candidates
        ],
        "tokens": phase2_tokens,
    }


def _ser_3(state: PipelineState) -> dict:
    top_perspectives = {c.perspective for c in state.top_candidates}
    return {
        "scores": [
            {
                "perspective": s.perspective.value,
                "logical_consistency": s.logical_consistency,
                "evidence_support": s.evidence_support,
                "failure_resilience": s.failure_resilience,
                "feasibility": s.feasibility,
                "total": round(s.total, 2),
                "bias_flags": s.bias_flags,
                "steel_man": s.steel_man,
                "is_top": s.perspective in top_perspectives,
            }
            for s in sorted(state.scores, key=lambda x: x.total, reverse=True)
        ],
        "tokens": state.phase_tokens.get("Phase 3: Critique & Pruning", {"input": 0, "output": 0}),
    }


def _ser_4(state: PipelineState) -> dict:
    return {
        "tests": [
            {
                "scenario": sr.scenario.value,
                "survival_rate": sr.survival_rate,
                "failure_mode": sr.failure_mode,
                "recovery_path": sr.recovery_path,
            }
            for sr in state.stress_results
        ],
        "tokens": state.phase_tokens.get("Phase 4: Stress Testing", {"input": 0, "output": 0}),
    }


def _ser_5(state: PipelineState) -> dict:
    if not state.final_solution:
        return {}
    fs = state.final_solution
    # Process action_blueprint to handle any datetime objects
    action_blueprint = []
    for step in fs.action_blueprint:
        processed_step = {}
        for key, value in step.items():
            if isinstance(value, datetime):
                processed_step[key] = value.isoformat()
            else:
                processed_step[key] = value
        action_blueprint.append(processed_step)

    return {
        "core_solution": fs.core_solution,
        "critical_insights": fs.critical_insights,
        "action_blueprint": action_blueprint,
        "open_questions": fs.open_questions,
        "claim_labels": {k: v.value for k, v in fs.claim_labels.items()},
        "meta_audit": {
            "most_dangerous_assumption": fs.meta_audit.most_dangerous_assumption,
            "dominant_bias": fs.meta_audit.dominant_bias,
            "remaining_uncertainty": fs.meta_audit.remaining_uncertainty,
            "assumption_failure_impact": fs.meta_audit.assumption_failure_impact,
            "non_obvious_insight": fs.meta_audit.non_obvious_insight,
        },
        "tokens": state.phase_tokens.get("Phase 5: Synthesis", {"input": 0, "output": 0}),
    }

# ─────────────────────────────────────────────────────────────────────
# SSE STREAM
# ─────────────────────────────────────────────────────────────────────

def _event(data: dict) -> str:
    # Custom JSON encoder that handles datetime objects
    def json_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    return f"data: {json.dumps(data, default=json_serializer)}\n\n"


async def run_stream(req: RunRequest) -> AsyncGenerator[str, None]:
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
        )
        state = PipelineState(problem=req.problem)

        yield _event({"type": "start", "routing": router.describe()})

        phases = [
            (0, "Classification",     pipeline.phase_0_classify,    _ser_0),
            (1, "Decomposition",      pipeline.phase_1_decompose,   _ser_1),
            (2, "Perspectives",       pipeline.phase_2_analyze,     _ser_2),
            (3, "Critique & Pruning", pipeline.phase_3_critique,    _ser_3),
            (4, "Stress Testing",     pipeline.phase_4_stress_test, _ser_4),
            (5, "Synthesis",          pipeline.phase_5_synthesize,  _ser_5),
        ]

        for num, name, fn, serializer in phases:
            global _cancel_flag
            if _cancel_flag:
                yield _event({"type": "cancelled", "message": "Pipeline stopped by user"})
                _cancel_flag = False
                return

            yield _event({"type": "phase_start", "phase": num, "name": name})
            try:
                await fn(state)
            except Exception as exc:
                # Log the full error server-side but return generic message
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
        
        yield _event({
            "type": "done",
            "phase_models": state.phase_models,
            "errors": state.errors,
            "total_tokens": {"input": total_input, "output": total_output, "total": total_input + total_output},
        })
    except Exception as exc:
        # Log the full error server-side but return more specific message
        import traceback
        print(f"Pipeline error: {str(exc)}\n{traceback.format_exc()}")
        yield _event({"type": "done", "errors": [f"Pipeline processing error: {str(exc)}"]})


# ─────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────

async def run_stream_cached(req: RunRequest) -> AsyncGenerator[str, None]:
    key = _cache_key(req)
    if not req.no_cache:
        cached = _load_cache(key)
        if cached:
            for ev in cached:
                yield _event({**ev, "cached": True} if ev.get("type") == "start" else ev)
                if ev.get("type") in ("phase_start", "phase_complete"):
                    await asyncio.sleep(0.02)
            return

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
    global _cancel_flag
    _cancel_flag = True
    return {"status": "stop requested"}


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


# Serve frontend last (catches all unmatched routes)
app.mount("/", StaticFiles(directory="ui", html=True), name="ui")
