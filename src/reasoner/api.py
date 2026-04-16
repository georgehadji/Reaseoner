from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, Request, WebSocket, Depends, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from reasoner.core.settings import settings
from reasoner.core.constants import (
    DEFAULT_PRESET,
    DEFAULT_SEQUENTIAL,
    DEFAULT_TOP_K,
    DEFAULT_SOURCE_TYPE,
    DEFAULT_SEARCH_RESULTS,
    CORS_MAX_AGE_SECONDS,
    TRUNCATION,
    SSE_FLUSH_INTERVAL,
    TIMEOUTS,
    VALIDATION_TEST_MAX_TOKENS,
    DEFAULT_SANITIZER_MAX_LENGTH,
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, field_validator
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse
import time
import logging

# Setup logger
logger = logging.getLogger(__name__)

# Security dependencies
security = HTTPBearer(auto_error=False)

# Import rate limiter and auth
from reasoner.rate_limiter import get_rate_limiter, RateLimitConfig
from reasoner.auth import get_auth_manager, AuthenticationError

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
    max_age=CORS_MAX_AGE_SECONDS,  # Cache preflight for 1 day
)

# Initialize rate limiter
rate_limiter = get_rate_limiter(RateLimitConfig(
    requests_per_minute=settings.RATE_LIMIT_PER_MINUTE,
    requests_per_hour=settings.RATE_LIMIT_PER_HOUR,
    burst_size=settings.RATE_LIMIT_BURST,
))

# Initialize auth manager
auth_manager = get_auth_manager()

from reasoner.models import PipelineState
from reasoner.pipeline import ARAPipeline
from reasoner.llm import _REGISTRY, ProviderRouter, list_models
from reasoner.presets import PRESETS, build_custom_router, get_preset, is_valid_preset_name, resolve_preset_name

# Neuro Integration
from reasoner.neuro.server import create_neuro_router
app.include_router(create_neuro_router())

# New Architecture Integration
from reasoner.infrastructure.persistence import get_event_store
from reasoner.application.handlers import get_handler_registry
from reasoner.application.commands import (
    RunPipelineCommand,
    ExecuteWidgetCommand,
)
from reasoner.application.queries import (
    GetPipelineStatusQuery,
    GetHistoryQuery,
    ListPresetsQuery,
)

# Widget Integrations (legacy fallback)
from reasoner.suggestions import generate_suggestions_async, SuggestionRequest

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
        from reasoner.llm import build_provider, _REGISTRY
        
        # Try to get a primary provider (use first available OpenRouter model)
        primary_provider = None
        for model_id in sorted(_REGISTRY):
            if _REGISTRY[model_id].get("is_local"):
                continue
            try:
                primary_provider = build_provider(model_id)
                break
            except Exception:
                continue
        
        # If no provider available, create a dummy one
        if primary_provider is None:
            from reasoner.infrastructure.llm.ports import BaseLLMProvider, LLMResponse, LLMConfig, Message
            from reasoner.infrastructure.llm.exceptions import LLMError
            
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
        
        from reasoner.infrastructure.llm.new_pipeline import NewARAPipeline
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
_active_runs: set[str] = set()  # IDs of currently streaming runs

# ─────────────────────────────────────────────────────────────────────
# CACHE
# ─────────────────────────────────────────────────────────────────────

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)


def _cache_key(req: "RunRequest") -> str:
    # v=2 invalidates old caches that lack per-phase tokens/models in phase_complete events
    payload = json.dumps({
        "problem": req.problem,
        "preset":  req.preset,
        "top_k":   req.top_k,
        "routing": req.routing,
        "v": 2,
    }, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def _load_cache(key: str) -> list[dict] | None:
    path = CACHE_DIR / f"{key}.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            # Treat a corrupt or unreadable cache file as a cache miss and
            # remove it so the next run can write a clean file.
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
    return None


_MAX_CACHE_FILES: int = 1000


def _prune_cache() -> None:
    """Remove oldest cache files if the directory exceeds the max size."""
    files = sorted(CACHE_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime)
    excess = len(files) - _MAX_CACHE_FILES
    for f in files[:excess]:
        try:
            f.unlink(missing_ok=True)
        except OSError:
            pass


def _save_cache(key: str, events: list[dict]) -> None:
    # Write to a sibling temp file then rename so that a crash during the
    # write never leaves a corrupt (partial) JSON file at the target path.
    # FIX BUG-007: Use unique temp filename per writer to prevent race conditions
    # on Windows where os.replace() is not atomic. Include PID and timestamp for uniqueness.
    import time
    path = CACHE_DIR / f"{key}.json"
    # Unique temp file: key.{pid}.{timestamp}.tmp
    tmp = CACHE_DIR / f"{key}.{os.getpid()}.{int(time.time() * 1000)}.tmp"
    try:
        tmp.write_text(json.dumps(events), encoding="utf-8")
        # On Windows, os.replace() may not be atomic, but with unique temp filenames
        # we avoid overwriting another writer's temp file. The last writer wins,
        # but data is never corrupted from interleaved writes.
        tmp.replace(path)
        # Clean up any old temp files for this key (from crashed writers)
        for old_tmp in CACHE_DIR.glob(f"{key}.*.tmp"):
            try:
                old_tmp.unlink(missing_ok=True)
            except OSError:
                pass
        _prune_cache()
    except OSError:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


from reasoner.presets import get_method_from_preset


class SearchRequest(BaseModel):
    query: str
    source_type: str = DEFAULT_SOURCE_TYPE
    num_results: int = DEFAULT_SEARCH_RESULTS
    smart: bool = False

    @field_validator('query')
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError('Query cannot be empty')
        if len(v) > TRUNCATION.PROBLEM:
            raise ValueError(f'Query too long (max {TRUNCATION.PROBLEM} characters)')
        return v.strip()

    @field_validator('num_results')
    @classmethod
    def validate_num_results(cls, v: int) -> int:
        return max(1, min(v, 20))

    model_config = {"extra": "forbid"}


class RunRequest(BaseModel):
    problem: str
    preset: str = DEFAULT_PRESET
    routing: dict[str, str] | None = None
    top_k: int = DEFAULT_TOP_K
    sequential: bool = DEFAULT_SEQUENTIAL  # Cost-effective: sequential by default in UI
    no_cache: bool = False
    enhance_prompt: bool = False
    source_type: str = DEFAULT_SOURCE_TYPE  # For iterative RAG: general, academic, social, news, code
    domain: str | None = None  # For domain-specific search

    @field_validator('problem')
    @classmethod
    def validate_problem(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError('Problem cannot be empty')
        if len(v) > DEFAULT_SANITIZER_MAX_LENGTH:  # Limit problem length
            raise ValueError(f'Problem too long (max {DEFAULT_SANITIZER_MAX_LENGTH} characters)')
        
        # ═══════════════════════════════════════════════════════════════════
        # SECURITY: Comprehensive input sanitization
        # ═══════════════════════════════════════════════════════════════════
        
        # Remove null bytes and control characters (except newlines/tabs)
        import re
        v = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', v)
        
        # Check for remaining null bytes after cleaning
        if '\x00' in v:
            raise ValueError('Invalid characters in problem')
        
        # Strip HTML/script tags (prevent XSS in logs/UI)
        v = re.sub(r'<script[^>]*>.*?</script>', '', v, flags=re.IGNORECASE | re.DOTALL)
        v = re.sub(r'<[^>]+>', '', v)  # Remove all HTML tags
        
        # Normalize unicode to prevent unicode-based attacks
        try:
            import unicodedata
            v = unicodedata.normalize('NFKC', v)
        except ImportError:
            pass
        
        # Check for potential injection patterns
        dangerous_patterns = [
            r'\{\{.*\}\}',           # Template injection
            r'<%.*%>',               # ERB-style injection
            r'\$\{.*\}',             # Shell variable expansion
            r'eval\s*\(',            # Code injection
            r'exec\s*\(',            # Code injection
            r'__import__',           # Python import
            r'subprocess',           # Shell execution
            r'os\.system',           # System calls
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError('Problem contains disallowed content')
        
        # Limit consecutive special characters (prevent DoS)
        if re.search(r'[^\w\s]{100,}', v):
            raise ValueError('Problem contains too many special characters')
        
        # Final whitespace normalization
        v = v.strip()
        
        if not v:
            raise ValueError('Problem cannot be empty after sanitization')
        
        return v

    @field_validator('preset')
    @classmethod
    def validate_preset(cls, v: str) -> str:
        if not is_valid_preset_name(v):
            raise ValueError(f'Invalid preset: {v}')
        return resolve_preset_name(v)
    
    @field_validator('source_type')
    @classmethod
    def validate_source_type(cls, v: str) -> str:
        allowed = {'general', 'academic', 'social', 'news', 'code'}
        if v not in allowed:
            raise ValueError(f'Invalid source_type: {v}. Allowed: {allowed}')
        return v
    
    @field_validator('domain')
    @classmethod
    def validate_domain(cls, v: str | None) -> str | None:
        if v is None:
            return None
        # Validate domain format (basic check)
        import re
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9\-.]*[a-zA-Z0-9]$', v):
            raise ValueError(f'Invalid domain format: {v}')
        if len(v) > 253:
            raise ValueError('Domain too long')
        return v.lower()


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
    if isinstance(obj, dict):
        val = obj.get(key, default)
        return default if val is None else val
    val = getattr(obj, key, default)
    return default if val is None else val

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

def _ser_1_5(state: PipelineState) -> dict:
    """Deep Read serializer."""
    return {
        "web_discovery_results": _get_v(state, 'web_discovery_results', []),
        "vetted_context": _get_v(state, 'vetted_context', []),
        "tokens": state.phase_tokens.get("Phase 1.5: Deep Read", {"input": 0, "output": 0}),
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
        "tokens": {"input": 0, "output": 0},
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

    # Fallback for debate rebuttals when scores are empty
    if not result["scores"]:
        debate_rounds = _get_v(state, 'debate_rounds', [])
        rebuttals = [r for r in debate_rounds if isinstance(r, dict) and r.get('type') == 'rebuttal']
        if rebuttals:
            result["debate_rebuttals"] = rebuttals

        # Fallback for scientific falsification tests
        scientific_state = _get_v(state, 'scientific_state')
        if scientific_state and isinstance(scientific_state, dict):
            result["scientific_state"] = scientific_state

        # Fallback for socratic dialectic answers
        socratic_state = _get_v(state, 'socratic_state')
        if socratic_state and isinstance(socratic_state, dict):
            result["socratic_state"] = socratic_state

    return result

def _ser_4(state: PipelineState) -> dict:
    stress = _get_v(state, 'stress_results', [])
    verif = _get_v(state, 'verification_results', [])
    meta = _get_v(state, 'meta_evaluation')
    scores = _get_v(state, 'scores', [])

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

    # Fallback for debate judge / jury verification when primary fields are empty
    if not stress and not verif and scores:
        result["scores"] = [
            {
                "perspective": (lambda x: x.value if hasattr(x, 'value') else str(x))(_get_v(s, 'perspective', '')),
                "total": round(_get_v(s, 'total', 0), 2),
                "steel_man": _get_v(s, 'steel_man', ''),
            } for s in sorted(scores, key=lambda x: _get_v(x, 'total', 0), reverse=True)
        ]

    return result

def _ser_5(state: PipelineState) -> dict:
    fs = _get_v(state, 'final_solution')
    if fs is None:
        return {}

    meta = _get_v(fs, 'meta_audit', {})

    # Action blueprint handling
    raw_bp = _get_v(fs, 'action_blueprint', [])
    clean_bp = []
    for step in (raw_bp if isinstance(raw_bp, list) else []):
        if isinstance(step, dict):
            # Only accept dicts that have at least one expected key or a non-empty action
            if not any(k in step for k in ("step", "action", "time_horizon", "go_criteria", "fallback")):
                continue
            entry = {
                "step": _get_v(step, 'step', ''),
                "action": _get_v(step, 'action', ''),
                "time_horizon": _get_v(step, 'time_horizon', ''),
                "go_criteria": _get_v(step, 'go_criteria', ''),
                "fallback": _get_v(step, 'fallback', '')
            }
            if entry["step"] or entry["action"]:
                clean_bp.append(entry)
        elif step is not None and str(step).strip():
            clean_bp.append({"step": "", "action": str(step).strip(), "time_horizon": "", "go_criteria": "", "fallback": ""})

    # Claim labels handling
    raw_labels = _get_v(fs, 'claim_labels', {})
    clean_labels = {k: (v.value if hasattr(v, 'value') else str(v)) for k, v in (raw_labels.items() if isinstance(raw_labels, dict) else {})}

    # Aggregate tokens across all phases
    total_input = sum(t.get("input", 0) for t in state.phase_tokens.values())
    total_output = sum(t.get("output", 0) for t in state.phase_tokens.values())

    # Build meta_audit only when source data exists
    meta_audit: dict[str, Any] = {}
    if meta:
        meta_audit = {
            "most_dangerous_assumption": _get_v(meta, 'most_dangerous_assumption', ''),
            "dominant_bias": _get_v(meta, 'dominant_bias', ''),
            "remaining_uncertainty": _get_v(meta, 'remaining_uncertainty', ''),
            "assumption_failure_impact": _get_v(meta, 'assumption_failure_impact', ''),
            "non_obvious_insight": _get_v(meta, 'non_obvious_insight', ''),
        }

    return {
        "core_solution": _get_v(fs, 'core_solution', ''),
        "critical_insights": _get_v(fs, 'critical_insights', []),
        "action_blueprint": clean_bp,
        "open_questions": _get_v(fs, 'open_questions', []),
        "claim_labels": clean_labels,
        "meta_audit": meta_audit,
        "tokens": {"input": total_input, "output": total_output}
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
    # Assign a unique ID to this run so stop requests can target it precisely.
    run_id = str(uuid.uuid4())
    _active_runs.add(run_id)
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
            parallel_perspectives=(not req.sequential) if not (req.preset and "multi-perspective" in req.preset) else True,
            verbose=False,
            preset_name=req.preset,
            source_type=req.source_type,
            domain=req.domain,
            enhance_prompt=req.enhance_prompt,
        )
        state = PipelineState(problem=req.problem, preset_name=req.preset)

        yield _event({"type": "start", "routing": router.describe()})

        # Optional prompt enhancement pre-phase
        if req.enhance_prompt and not state.enhanced_problem:
            try:
                await pipeline._phase_enhance_prompt(state)
                if state.enhanced_problem and state.enhanced_problem != state.problem:
                    yield _event({"type": "prompt_enhanced", "original": state.problem, "enhanced": state.enhanced_problem})
            except Exception:
                state.enhanced_problem = state.problem
                pass  # Fail silently and proceed with original prompt

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
            (1.5, "Deep Read",        pipeline._phase_deep_read,    _ser_1_5),
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

        CRITICAL_PHASES = {
            "Decomposition", "Perspectives", "Opening Statements",
            "Hypotheses", "Maieutic Questions", "Generation Pool",
            "Deep Research",
        }
        for num, name, fn, serializer in phases:
            # Check only this run's cancellation flag, not a shared global.
            # This prevents a stop request for one tab from killing another tab's run.
            if _cancelled_runs.pop(run_id, False):
                yield _event({"type": "cancelled", "message": "Pipeline stopped by user"})
                return

            phase_key = f"Phase {num}: {name}"
            state._current_phase_key = phase_key
            yield _event({"type": "phase_start", "phase": num, "name": name})
            try:
                await fn(state)
            except Exception as exc:
                import traceback
                print(f"Phase {num} error: {str(exc)}\n{traceback.format_exc()}")
                err_msg = f"Processing error in {name.lower()} phase: {str(exc)}"
                state.errors.append(err_msg)
                yield _event({"type": "phase_error", "phase": num, "error": err_msg})
                # Halt pipeline on critical phase failures to prevent synthesis on corrupted state
                if name in CRITICAL_PHASES or name.startswith("Round "):
                    break
                continue
            data = serializer(state)
            if isinstance(data, dict):
                data["tokens"] = state.phase_tokens.get(phase_key, {"input": 0, "output": 0})
                phase_models = getattr(state, '_phase_models_by_key', {}).get(phase_key, [])
                if phase_models:
                    data["models"] = phase_models
            yield _event({
                "type": "phase_complete",
                "phase": num,
                "name": name,
                "data": data,
            })

        # Calculate total tokens
        # FIX: read from detailed_token_usage (populated by _call_llm_cached) instead of phase_tokens
        token_source = state.detailed_token_usage if state.detailed_token_usage else state.phase_tokens
        total_input = sum(t.get("input", 0) for t in token_source.values())
        total_output = sum(t.get("output", 0) for t in token_source.values())
        total_tokens = total_input + total_output

        # Save to history
        try:
            from datetime import datetime
            entry = HistoryEntry(
                id=hashlib.sha256(f"{req.problem}{datetime.now().isoformat()}".encode()).hexdigest()[:16],
                problem=req.problem[:TRUNCATION.API_STORAGE],  # Truncate for storage
                preset=req.preset,
                method=_get_method_from_preset(req.preset),
                timestamp=datetime.now().isoformat(),
                tokens={"input": total_input, "output": total_output, "total": total_tokens},
                status="completed" if not state.errors else "error",
            )
            _save_history_entry(entry)

            # TaggedMemory: index by method and preset for fast retrieval
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
        _active_runs.discard(run_id)
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


# ─────────────────────────────────────────────────────────────────────
# Authentication & Rate Limiting Dependencies
# ─────────────────────────────────────────────────────────────────────

async def get_client_id(request: Request) -> str:
    """Extract client ID from request (IP + User-Agent)."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("User-Agent", "")
    return f"{ip}:{hashlib.md5(user_agent.encode()).hexdigest()[:8]}"


async def check_rate_limit(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """
    Check rate limit for request.
    Raises HTTPException if rate limit exceeded.
    """
    client_id = await get_client_id(request)
    allowed, info = await rate_limiter.is_allowed(client_id)
    
    # Add rate limit headers to response
    request.state.rate_limit_info = info
    
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "retry_after": int(info.get("retry_after", 60)),
                "limit_minute": info.get("limit_minute"),
                "remaining_minute": info.get("remaining_minute", 0),
            },
            headers={
                "Retry-After": str(int(info.get("retry_after", 60))),
                "X-RateLimit-Limit": str(info.get("limit_minute")),
                "X-RateLimit-Remaining": str(info.get("remaining_minute", 0)),
            }
        )
    
    return True


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """
    Require valid API key authentication.
    Raises HTTPException if authentication fails.
    """
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        api_key = await auth_manager.authenticate(credentials.credentials)
        return api_key
    except AuthenticationError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"} if e.status_code == 401 else None,
        )


async def optional_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False))
):
    """
    Optional authentication - returns API key if provided, None otherwise.
    """
    if not credentials:
        return None

    try:
        return await auth_manager.authenticate(credentials.credentials)
    except AuthenticationError:
        return None


# ─────────────────────────────────────────────────────────────────────
# API Endpoints
# ─────────────────────────────────────────────────────────────────────

@app.post("/api/run")
async def run_pipeline(
    request: Request,
    req: RunRequest,
    authenticated = Depends(optional_auth),
    rate_limit_checked = Depends(check_rate_limit)
):
    """
    Run pipeline with optional authentication and rate limiting.
    
    Authenticated users get higher rate limits and priority processing.
    """
    return StreamingResponse(
        run_stream_cached(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-RateLimit-Limit": str(request.state.rate_limit_info.get("limit_minute")),
            "X-RateLimit-Remaining": str(request.state.rate_limit_info.get("remaining_minute")),
        },
    )


@app.post("/api/search")
async def search_web(
    req: SearchRequest,
    rate_limit_checked = Depends(check_rate_limit)
):
    """
    Advanced web search via SearXNG.
    Returns raw discovery results. When smart=True, the query is decomposed
    into focused sub-queries via a lightweight LLM, searched in parallel,
    deduplicated, and grouped.
    """
    try:
        from reasoner.core.search import get_discovery_client, smart_search
        if req.smart:
            results = await smart_search(
                req.query,
                source_type=req.source_type,
                num_results=req.num_results,
            )
        else:
            client, _ = await get_discovery_client(source_type=req.source_type)
            results = await client.search(
                req.query,
                num_results=req.num_results,
                source_type=req.source_type,
            )
        return {
            "query": req.query,
            "source_type": req.source_type,
            "results": results,
        }
    except Exception as exc:
        logger.warning(f"Web search failed: {exc}")
        raise HTTPException(status_code=503, detail=f"Search unavailable: {str(exc)}")


@app.delete("/api/cache")
async def clear_cache():
    cleared = 0
    for f in CACHE_DIR.glob("*.json"):
        try:
            f.unlink(missing_ok=True)
            cleared += 1
        except OSError:
            pass
    return {"cleared": cleared}


@app.post("/api/stop")
async def stop_pipeline():
    # Mark all active runs as cancelled.
    # Each run checks its own flag, so concurrent runs remain isolated.
    for run_id in list(_active_runs):
        _cancelled_runs[run_id] = True
    return {"status": "stop requested"}


# ─────────────────────────────────────────────────────────────────────
# FILE UPLOADS
# ─────────────────────────────────────────────────────────────────────

from reasoner.uploader import save_uploaded_file, get_file_text, delete_file, list_uploads


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
        from reasoner.infrastructure.widgets import get_widget_registry
        
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
        from reasoner.infrastructure.widgets import get_widget_registry
        
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
        # get_weather_data is async; the former sync wrapper was removed because
        # it caused RuntimeError ("event loop already running") inside FastAPI.
        from reasoner.widgets import get_weather_data
        weather_data = await get_weather_data(location)
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
        from reasoner.widgets import get_stock_data
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
        from reasoner.widgets import calculate_expression
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
        from reasoner.widgets import get_discover_content
        content = await get_discover_content(topic, mode)
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


@app.get("/api/history/tagged")
async def get_tagged_history(tag: str, limit: int = 20):
    """Get history entries by tag (e.g. method:multi-perspective or preset:research-budget)."""
    from reasoner.core.memory import TaggedMemory
    tagged = TaggedMemory(HISTORY_DIR)
    entries = tagged.get_by_tag(tag, limit=limit)
    return {
        "tag": tag,
        "total": tagged.count(tag),
        "entries": entries,
    }


@app.get("/api/history/{entry_id}")
async def get_history_entry(entry_id: str):
    """Get a specific history entry."""
    safe_id = Path(entry_id).name
    path = HISTORY_DIR / f"{safe_id}.json"
    if not path.exists() or not str(path.resolve()).startswith(str(HISTORY_DIR.resolve())):
        return {"error": "Entry not found"}, 404
    return json.loads(path.read_text(encoding="utf-8"))


@app.delete("/api/history/{entry_id}")
async def delete_history_entry(entry_id: str):
    """Delete a history entry."""
    safe_id = Path(entry_id).name
    path = HISTORY_DIR / f"{safe_id}.json"
    try:
        if not path.exists() or not str(path.resolve()).startswith(str(HISTORY_DIR.resolve())):
            return {"error": "Entry not found"}, 404
        path.unlink(missing_ok=True)
        return {"status": "deleted"}
    except OSError as e:
        logger.error(f"Failed to delete history entry {entry_id}: {e}")
        return {"error": "Failed to delete entry"}, 500


@app.delete("/api/history")
async def clear_history():
    """Clear all history."""
    cleared = 0
    failed = 0
    for f in HISTORY_DIR.glob("*.json"):
        try:
            f.unlink(missing_ok=True)
            cleared += 1
        except OSError as e:
            logger.warning(f"Failed to delete history file {f}: {e}")
            failed += 1
    return {"cleared": cleared, "failed": failed}


def _save_history_entry(entry: HistoryEntry) -> None:
    """Save a history entry to disk."""
    path = HISTORY_DIR / f"{entry.id}.json"
    path.write_text(json.dumps(entry.model_dump(), ensure_ascii=False), encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────
# WEBSOCKET ENDPOINTS
# ─────────────────────────────────────────────────────────────────────

from reasoner.infrastructure.websocket import (
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
# API KEY VALIDATION ENDPOINT
# ─────────────────────────────────────────────────────────────────────

@app.get("/api/keys/status")
async def get_api_keys_status():
    """
    Get status of all configured LLM provider API keys.
    
    Returns which keys are set (without revealing values) and which
    providers are available for use.
    """
    from reasoner.llm import _REGISTRY
    
    # Group by environment variable
    env_status: dict[str, dict] = {}
    
    for model_id, cfg in _REGISTRY.items():
        env_var = cfg.get("env", "")
        if not env_var:
            continue
            
        if env_var not in env_status:
            key_value = os.environ.get(env_var, "")
            env_status[env_var] = {
                "is_set": bool(key_value),
                "key_length": len(key_value) if key_value else 0,
                "models": [],
                "is_local": cfg.get("is_local", False),
            }
        
        env_status[env_var]["models"].append(model_id)
    
    # Summary
    total_providers = len(env_status)
    configured = sum(1 for s in env_status.values() if s["is_set"])
    
    return {
        "summary": {
            "total_providers": total_providers,
            "configured": configured,
            "missing": total_providers - configured,
        },
        "providers": env_status,
    }


@app.post("/api/keys/validate")
async def validate_api_keys(request: Request):
    """
    Pre-flight validation of API keys.
    
    Tests each configured provider with a minimal request to verify
    the API key is valid and the service is accessible.
    
    This prevents mid-pipeline failures due to invalid keys.
    """
    from reasoner.llm import _REGISTRY, build_provider
    
    results = {}
    tested_envs = set()
    
    for model_id, cfg in _REGISTRY.items():
        env_var = cfg.get("env", "")
        if not env_var or env_var in tested_envs:
            continue
        tested_envs.add(env_var)
        
        # Skip local providers (Ollama)
        if cfg.get("is_local"):
            results[env_var] = {
                "status": "skipped",
                "reason": "Local provider - no API key needed",
            }
            continue
        
        key = os.environ.get(env_var, "")
        if not key:
            results[env_var] = {
                "status": "missing",
                "reason": f"Environment variable {env_var} not set",
            }
            continue
        
        # Attempt to build provider and make minimal test call
        try:
            provider = build_provider(model_id)
            # Make a minimal test call (just 1 token)
            await asyncio.wait_for(
                provider.complete(
                    system_prompt="Reply with: ok",
                    user_prompt="test",
                    max_tokens=VALIDATION_TEST_MAX_TOKENS,
                ),
                timeout=TIMEOUTS.MODEL_VALIDATION,  # 10 second timeout for validation
            )
            results[env_var] = {
                "status": "valid",
                "model_tested": model_id,
            }
        except asyncio.TimeoutError:
            results[env_var] = {
                "status": "timeout",
                "reason": "Provider did not respond within 10 seconds",
            }
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)[:200]  # Truncate long error messages
            results[env_var] = {
                "status": "error",
                "error_type": error_type,
                "reason": error_msg,
            }
    
    # Summary
    valid_count = sum(1 for r in results.values() if r["status"] == "valid")
    total_count = len(results)
    
    return {
        "summary": {
            "valid": valid_count,
            "total": total_count,
            "all_valid": valid_count == total_count,
        },
        "results": results,
    }


# ─────────────────────────────────────────────────────────────────────
# MEMORY LIMITS & REQUEST TIMEOUT MIDDLEWARE
# ─────────────────────────────────────────────────────────────────────

import traceback

# Note: 'resource' module is Unix-only, not available on Windows
# Memory limits use psutil instead


class MemoryLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce memory limits and prevent OOM.
    
    Configured via environment variables:
    - MEMORY_LIMIT_MB: Maximum memory in MB (default: 1024)
    - MEMORY_WARNING_MB: Warning threshold (default: 768)
    """
    
    def __init__(self, app, memory_limit_mb: int = 1024, warning_mb: int = 768):
        super().__init__(app)
        self.memory_limit_mb = memory_limit_mb
        self.warning_mb = warning_mb
        self._warning_logged = False
    
    async def dispatch(self, request: Request, call_next):
        # Check memory before processing
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            if memory_mb > self.memory_limit_mb:
                logger.error(
                    f"Memory limit exceeded: {memory_mb:.1f}MB > {self.memory_limit_mb}MB"
                )
                return JSONResponse(
                    {"error": "Server memory limit exceeded. Please try again later."},
                    status_code=503,
                )
            
            if memory_mb > self.warning_mb and not self._warning_logged:
                logger.warning(
                    f"Memory usage high: {memory_mb:.1f}MB (limit: {self.memory_limit_mb}MB)"
                )
                self._warning_logged = True
            elif memory_mb < self.warning_mb * 0.8:
                self._warning_logged = False
                
        except ImportError:
            # psutil not available, skip memory check
            pass
        
        return await call_next(request)


class RequestTimeoutMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce request timeouts.
    
    Prevents long-running requests from blocking the server indefinitely.
    """
    
    def __init__(self, app, timeout_seconds: float = 300.0):
        super().__init__(app)
        self.timeout_seconds = timeout_seconds
    
    async def dispatch(self, request: Request, call_next):
        # Skip timeout for SSE endpoints (they're long-running by design)
        if request.url.path.startswith("/api/run"):
            return await call_next(request)
        
        try:
            return await asyncio.wait_for(
                call_next(request),
                timeout=self.timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.warning(f"Request timeout: {request.url.path}")
            return JSONResponse(
                {"error": "Request timeout"},
                status_code=504,
            )


# Add memory and timeout middleware
MEMORY_LIMIT_MB = int(os.environ.get("MEMORY_LIMIT_MB", "1024"))
MEMORY_WARNING_MB = int(os.environ.get("MEMORY_WARNING_MB", "768"))
REQUEST_TIMEOUT_SECONDS = float(os.environ.get("REQUEST_TIMEOUT_SECONDS", "300"))

app.add_middleware(
    MemoryLimitMiddleware,
    memory_limit_mb=MEMORY_LIMIT_MB,
    warning_mb=MEMORY_WARNING_MB,
)
app.add_middleware(
    RequestTimeoutMiddleware,
    timeout_seconds=REQUEST_TIMEOUT_SECONDS,
)


# ─────────────────────────────────────────────────────────────────────
# HEALTH CHECK ENDPOINT
# ─────────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    """
    Comprehensive health check endpoint.
    
    Returns system status, memory usage, and provider availability.
    """
    import sys
    from datetime import datetime
    
    health = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": "2.0",
        "python": sys.version,
        "checks": {},
    }
    
    # Memory check
    try:
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        health["checks"]["memory"] = {
            "status": "ok" if memory_mb < MEMORY_LIMIT_MB else "warning",
            "used_mb": round(memory_mb, 1),
            "limit_mb": MEMORY_LIMIT_MB,
        }
    except ImportError:
        health["checks"]["memory"] = {"status": "unknown", "reason": "psutil not installed"}
    
    # Circuit breaker status
    from reasoner.circuit_breaker import get_all_circuit_breakers
    circuits = get_all_circuit_breakers()
    open_circuits = [name for name, cb in circuits.items() if cb["state"] == "open"]
    health["checks"]["circuit_breakers"] = {
        "status": "ok" if not open_circuits else "degraded",
        "open_circuits": open_circuits,
        "total": len(circuits),
    }
    
    # Cache status
    cache_files = list(CACHE_DIR.glob("*.json"))
    health["checks"]["cache"] = {
        "status": "ok",
        "files": len(cache_files),
    }
    
    # Determine overall status
    if any(c.get("status") == "error" for c in health["checks"].values()):
        health["status"] = "unhealthy"
    elif any(c.get("status") in ("warning", "degraded") for c in health["checks"].values()):
        health["status"] = "degraded"
    
    return health


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
    
    # Log memory limits
    logger.info(f"Memory limit: {MEMORY_LIMIT_MB}MB (warning at {MEMORY_WARNING_MB}MB)")
    logger.info(f"Request timeout: {REQUEST_TIMEOUT_SECONDS}s")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global _event_store
    if _event_store and hasattr(_event_store, 'close'):
        _event_store.close()

    # Close shared HTTP connection pool to prevent resource leaks
    from reasoner.llm import OpenAICompatibleProvider
    await OpenAICompatibleProvider.close_shared_pool()

    logger.info("Reasoner shutdown complete")


