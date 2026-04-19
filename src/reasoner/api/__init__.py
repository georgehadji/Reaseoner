from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from reasoner.core.settings import settings
from reasoner.core.constants import (
    CORS_MAX_AGE_SECONDS,
    TRUNCATION,
)
from fastapi.security import HTTPBearer
import logging

# Setup logger
logger = logging.getLogger(__name__)

# Security dependencies
security = HTTPBearer(auto_error=False)

# Import rate limiter and auth
from reasoner.rate_limiter import get_rate_limiter, RateLimitConfig
from reasoner.auth import get_auth_manager, AuthenticationError

from reasoner.api.middleware import SecurityHeadersMiddleware

app = FastAPI(title="ARA v2.0")

# Add security middleware
app.add_middleware(SecurityHeadersMiddleware)

# Add CORS middleware with restrictive defaults
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000", "http://localhost:8001", "http://127.0.0.1:8001"],  # Restrict to known origins
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

from reasoner.llm import _REGISTRY

# Neuro Integration
from reasoner.neuro.server import create_neuro_router
app.include_router(create_neuro_router())

# New Architecture Integration
from reasoner.infrastructure.persistence import get_event_store
from reasoner.application.handlers import get_handler_registry
from reasoner.application.queries import (
    GetPipelineStatusQuery,
)

# Widget Integrations (legacy fallback)


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
# Encapsulated in RunStateStore for testability and safe async locking.
from .run_state import RunStateStore

_run_store = RunStateStore()

# ─────────────────────────────────────────────────────────────────────
# CACHE
# ─────────────────────────────────────────────────────────────────────

from .cache import (
    CACHE_DIR,
    _MEMORY_CACHE,
    _cache_key,
    _load_cache,
    _save_cache,
)


from reasoner.api.schemas import (
    CalculationRequest,
    ContextAnalysisRequest,
    DiscoverRequest,
    FollowupRequest,
    RunRequest,
    SearchRequest,
    StockRequest,
    SuggestionRequestModel,
    WeatherRequest,
)


# ─────────────────────────────────────────────────────────────────────
# SERIALIZERS — one per phase
# ─────────────────────────────────────────────────────────────────────

from .serializers import (
    _event,
    _is_debate,
    _is_orchestrated,
    _is_scientific,
    _is_socratic,
    _ser_0,
    _ser_1,
    _ser_1_5,
    _ser_2,
    _ser_3,
    _ser_4,
    _ser_5,
)


from reasoner.api.streaming import (
    _run_store,
    run_followup_stream,
    run_stream,
    run_stream_cached,
)

from reasoner.api.auth_deps import check_rate_limit, optional_auth


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


@app.post("/api/run-followup")
async def run_followup_pipeline(
    request: Request,
    req: FollowupRequest,
    rate_limit_checked = Depends(check_rate_limit)
):
    """
    Run the ARA pipeline for a follow-up question with full conversation context.
    """
    return StreamingResponse(
        run_followup_stream(req),
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
        from reasoner.application.services.search_service import SearchService
        from reasoner.core.search import smart_search

        if req.smart:
            results = await smart_search(
                req.query,
                source_type=req.source_type,
                num_results=req.num_results,
            )
        else:
            search_service = SearchService()
            results = await search_service.search(
                req.query,
                source_type=req.source_type,
                num_results=req.num_results,
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
    _MEMORY_CACHE.clear()
    return {"cleared": cleared}


@app.post("/api/stop")
async def stop_pipeline(run_id: str | None = None):
    # If a specific run_id is provided, cancel only that run.
    # Otherwise cancel all active runs (global stop, e.g. from the UI stop button).
    if run_id:
        targets = [run_id] if _run_store.is_active(run_id) else []
    else:
        targets = list(_run_store.active_runs)

    for rid in targets:
        await _run_store.request_cancel(rid)

    return {"status": "stop requested", "cancelled": targets}


# ─────────────────────────────────────────────────────────────────────
# FILE UPLOADS
# ─────────────────────────────────────────────────────────────────────

from reasoner.api.routes.uploads import router as uploads_router
app.include_router(uploads_router)


@app.get("/api/presets")
async def api_presets():
    # SECURITY: Do not expose preset names, descriptions, or key requirements
    return {}


@app.get("/api/models")
async def api_models():
    # SECURITY: Do not expose available models or provider configuration
    return []


# ─────────────────────────────────────────────────────────────────────
# EXTERNAL CONTEXT INTEGRATION
# ─────────────────────────────────────────────────────────────────────

# ContextAnalysisRequest imported from .schemas


from reasoner.api.routes.context import router as context_router
app.include_router(context_router)

from reasoner.api.routes.widgets import router as widgets_router
app.include_router(widgets_router)

from reasoner.api.routes.pipelines import router as pipelines_router
app.include_router(pipelines_router)


# ─────────────────────────────────────────────────────────────────────
# LEGACY WIDGET ENDPOINTS (Fallback)
# ─────────────────────────────────────────────────────────────────────

from reasoner.api.routes.legacy_widgets import router as legacy_widgets_router
app.include_router(legacy_widgets_router)


# ─────────────────────────────────────────────────────────────────────
# SEARCH HISTORY
# ─────────────────────────────────────────────────────────────────────

from reasoner.api.routes.history import router as history_router
app.include_router(history_router)


from reasoner.api.routes.websocket import router as websocket_router
app.include_router(websocket_router)


# ─────────────────────────────────────────────────────────────────────
# API KEY VALIDATION ENDPOINT
# ─────────────────────────────────────────────────────────────────────

from reasoner.api.routes.keys import router as keys_router
app.include_router(keys_router)


# ─────────────────────────────────────────────────────────────────────
# MEMORY LIMITS & REQUEST TIMEOUT MIDDLEWARE
# ─────────────────────────────────────────────────────────────────────



# Note: 'resource' module is Unix-only, not available on Windows
# Memory limits use psutil instead


from reasoner.api.middleware import MemoryLimitMiddleware, RequestTimeoutMiddleware

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
# ROOT ENDPOINT
# ─────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "message": "ARA v2.0 API",
        "docs": "/docs",
        "health": "/api/health",
        "api": "/api/run",
    }


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
    from datetime import datetime, timezone
    
    health = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
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
    # Initialize event bus subscribers
    from reasoner.application.event_bus.bus import init_default_subscribers
    init_default_subscribers()

    # Lazy initialization - components will be initialized on first use
    # This prevents startup failures due to missing dependencies
    logger.info("Reasoner startup complete")
    logger.info("Web UI: http://localhost:8001")
    logger.info("API Docs: http://localhost:8001/docs")
    logger.info("WebSocket: ws://localhost:8001/ws")
    
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


