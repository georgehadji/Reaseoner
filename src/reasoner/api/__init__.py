from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from contextlib import asynccontextmanager

import asyncio
from fastapi import FastAPI, Request, Depends, HTTPException, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from reasoner.core.settings import settings
from reasoner.core.constants import (
    CORS_MAX_AGE_SECONDS,
    TRUNCATION,
)
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from datetime import datetime, timezone
import logging

# Setup logger
logger = logging.getLogger(__name__)

# Initialize Sentry (Critical Enhancement 7.2)
from reasoner.api.sentry import init_sentry
init_sentry()

# Security dependencies
security = HTTPBearer(auto_error=False)

# Import rate limiter and auth
from reasoner.rate_limiter import get_rate_limiter, RateLimitConfig
from reasoner.auth import get_auth_manager, AuthenticationError

from reasoner.api.middleware import SecurityHeadersMiddleware

# Module-level singleton for health-check Postgres pool (Critical Enhancement 5.6)
_health_postgres_pool = None


async def _update_active_users_loop() -> None:
    """Background task to update active users gauge every 60s (Critical Enhancement 7.3)."""
    from reasoner.api.metrics import REASONER_ACTIVE_USERS
    while True:
        try:
            await asyncio.sleep(60)
            if _health_postgres_pool is not None:
                row = await _health_postgres_pool.fetchval(
                    "SELECT COUNT(DISTINCT user_id) FROM query_audit_logs WHERE timestamp > NOW() - INTERVAL '24 hours'"
                )
                REASONER_ACTIVE_USERS.set(row or 0)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Active users update failed: %s", exc)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown orchestration."""
    # ── Startup ──
    from reasoner.application.event_bus.bus import init_default_subscribers
    init_default_subscribers()

    from reasoner.infrastructure.websocket import setup_event_bus_integration
    await setup_event_bus_integration()

    from reasoner.core.health_validator import validate_all
    await validate_all()

    # Warn if running in multi-worker mode with in-memory rate limiting / circuit breaker
    uvicorn_workers = int(os.environ.get("UVICORN_WORKERS", "1"))
    if uvicorn_workers > 1:
        if settings.RATE_LIMITER_MODE == "memory":
            logger.warning(
                "Rate limiter is in 'memory' mode but UVICORN_WORKERS=%d. "
                "Each worker maintains its own token bucket, allowing rate-limit bypass. "
                "Set RATE_LIMITER_MODE to a shared backend (e.g., 'redis') for production.",
                uvicorn_workers,
            )
        if settings.CIRCUIT_BREAKER_MODE == "memory":
            logger.warning(
                "Circuit breaker is in 'memory' mode but UVICORN_WORKERS=%d. "
                "Circuit state is not shared across workers. "
                "Set CIRCUIT_BREAKER_MODE to a shared backend (e.g., 'redis') for production.",
                uvicorn_workers,
            )

    logger.info("Reasoner startup complete")
    logger.info(f"Web UI: http://{settings.SERVER_HOST}:{settings.SERVER_PORT}")
    logger.info(f"API Docs: http://{settings.SERVER_HOST}:{settings.SERVER_PORT}/docs")
    logger.info(f"WebSocket: ws://{settings.SERVER_HOST}:{settings.SERVER_PORT}/ws")
    logger.info(f"Memory limit: {MEMORY_LIMIT_MB}MB (warning at {MEMORY_WARNING_MB}MB)")
    logger.info(f"Request timeout: {REQUEST_TIMEOUT_SECONDS}s")

    # Background task: update active users gauge (Critical Enhancement 7.3)
    _active_users_task = asyncio.create_task(_update_active_users_loop())

    yield

    # Cancel background task on shutdown
    _active_users_task.cancel()
    try:
        await _active_users_task
    except asyncio.CancelledError:
        pass

    # ── Shutdown ──
    global _event_store, _health_postgres_pool
    if _event_store and hasattr(_event_store, 'close'):
        _event_store.close()

    from reasoner.llm import OpenAICompatibleProvider
    await OpenAICompatibleProvider.close_shared_pool()

    from reasoner.scraper import close_scraper_client
    await close_scraper_client()

    # Close Redis connection (Critical Enhancement 5.5.2)
    from reasoner.infrastructure.redis.client import close_redis
    await close_redis()

    # Close health-check Postgres pool
    if _health_postgres_pool is not None:
        await _health_postgres_pool.close()
        _health_postgres_pool = None

    logger.info("Reasoner shutdown complete")


app = FastAPI(title="ARA v2.0", lifespan=lifespan)

# Add security middleware
app.add_middleware(SecurityHeadersMiddleware)

# Add audit middleware (Critical Enhancement 6.3)
from reasoner.api.middleware import AuditMiddleware
app.add_middleware(AuditMiddleware)

# Add CORS middleware — production-aware (Critical Enhancement 6.1.2)
_env = os.environ.get("ENVIRONMENT", "development")
if _env == "production":
    _app_url = os.environ.get("APP_URL", "")
    _allowed_origins = [_app_url] if _app_url else []
else:
    _allowed_origins = settings.cors_origins_list

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=[
        "authorization",
        "content-type",
        "accept",
        "accept-language",
        "x-csrf-token",
        "x-requested-with",
    ],
    max_age=CORS_MAX_AGE_SECONDS,
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
from .run_state import _run_store

# ─────────────────────────────────────────────────────────────────────
# CACHE
# ─────────────────────────────────────────────────────────────────────

from .cache import (
    CACHE_DIR,
    _MEMORY_CACHE,
    _cache_key,
    clear_memory_cache,
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
    run_followup_stream,
    run_stream,
    run_stream_cached,
)

from reasoner.api.auth_deps import optional_auth, require_csrf
from reasoner.api.dependencies import check_rate_limit, get_current_user, get_optional_user, check_quota_if_authenticated
from reasoner.domain.saas import User, QuotaResult


# ─────────────────────────────────────────────────────────────────────
# API Endpoints
# ─────────────────────────────────────────────────────────────────────

@app.post("/api/csrf")
async def get_csrf_token():
    """Generate a signed CSRF token for frontend use."""
    from reasoner.api.csrf import generate_signed_csrf_token
    return {"token": generate_signed_csrf_token()}


async def _run_stream_with_metrics(req: RunRequest, user: User | None):
    """Wrap run_stream_cached with Prometheus metrics (Critical Enhancement 7.1)."""
    from reasoner.api.metrics import REASONER_QUERIES_TOTAL, QueryTimer
    from reasoner.logging_utils import set_log_context

    tier = "anonymous" if user is None else "free"  # TODO Phase 4: actual tier
    preset = req.preset or "auto-budget"
    set_log_context(user_id=str(user.id) if user else None, tier=tier, preset=preset)

    timer = QueryTimer(preset=preset)
    timer.start()

    has_error = False
    try:
        async for chunk in run_stream_cached(req):
            yield chunk
    except Exception:
        has_error = True
        raise
    finally:
        timer.observe()
        REASONER_QUERIES_TOTAL.labels(
            tier=tier,
            preset=preset,
            status="error" if has_error else "success",
        ).inc()


@app.post("/api/run")
async def run_pipeline(
    request: Request,
    req: RunRequest,
    user: User | None = Depends(get_optional_user),
    authenticated = Depends(optional_auth),
    rate_limit_checked = Depends(check_rate_limit),
    quota: QuotaResult | None = Depends(check_quota_if_authenticated),
    csrf_checked = Depends(require_csrf),
):
    """
    Run pipeline with optional authentication and rate limiting.

    Authenticated users get higher rate limits and priority processing.
    """
    # TODO Phase 3: if user is None and ENABLE_LEGACY_API_KEY=false → 401
    # TODO Phase 4: use actual user tier from subscription DB
    return StreamingResponse(
        _run_stream_with_metrics(req, user),
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
    rate_limit_checked = Depends(check_rate_limit),
    csrf_checked = Depends(require_csrf),
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
async def clear_cache(
    csrf_checked = Depends(require_csrf),
):
    cleared = 0
    for f in CACHE_DIR.glob("*.json"):
        try:
            f.unlink(missing_ok=True)
            cleared += 1
        except OSError:
            pass
    clear_memory_cache()
    return {"cleared": cleared}


@app.post("/api/stop")
async def stop_pipeline(
    run_id: str | None = None,
    csrf_checked = Depends(require_csrf),
):
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

from reasoner.api.routes.images import router as images_router
app.include_router(images_router)


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

# Mount SaaS router
from reasoner.api import saas_router
app.include_router(saas_router.router)

# Mount Billing router
from reasoner.api import billing_router
app.include_router(billing_router.router)

# Mount Metrics endpoint (Critical Enhancement 6.1: restrict by IP)
from reasoner.api.metrics import metrics_endpoint

async def _metrics_ip_restricted(request: Request):
    allowed = os.environ.get("METRICS_ALLOWED_IPS", "127.0.0.1,::1").split(",")
    client = request.client.host if request.client else ""
    forwarded = request.headers.get("X-Forwarded-For", client).split(",")[0].strip()
    if forwarded not in allowed:
        raise HTTPException(status_code=403, detail="Metrics access denied")

app.add_api_route("/api/metrics", metrics_endpoint, methods=["GET"], dependencies=[Depends(_metrics_ip_restricted)])


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
# COST ESTIMATE ENDPOINT
# ─────────────────────────────────────────────────────────────────────

@app.post("/api/estimate")
async def estimate_cost(
    req: RunRequest,
    csrf_checked = Depends(require_csrf),
):
    """
    Estimate tokens, cost, and duration for a pipeline run without executing it.
    """
    from reasoner.pricing import calculate_model_cost, get_pricing
    from reasoner.presets import get_preset_price_tier
    from reasoner.application.services.preset_service import PresetService

    _preset_service = PresetService()
    raw_preset = req.preset or "auto-budget"
    gate_preset_name, is_auto, auto_tier = _preset_service.resolve(raw_preset)
    tier = get_preset_price_tier(gate_preset_name)

    # Rough token estimation based on prompt length + heuristic overhead
    prompt_tokens = len(req.problem.split()) + 50  # words → tokens approx
    num_phases = 8  # average phases per run
    tokens_per_phase_input = 500
    tokens_per_phase_output = 800

    if tier == "premium":
        tokens_per_phase_input = 1000
        tokens_per_phase_output = 1500

    estimated_input = prompt_tokens + (num_phases * tokens_per_phase_input)
    estimated_output = num_phases * tokens_per_phase_output

    # Get primary model pricing
    primary_id = _REGISTRY.get(gate_preset_name, {}).get("primary", "openrouter/openai/gpt-4o-mini")
    pricing = get_pricing(primary_id)
    estimated_cost = calculate_model_cost(primary_id, estimated_input, estimated_output)

    # Heuristic duration (seconds)
    base_duration = 8 if tier == "budget" else 20
    estimated_duration = base_duration + (len(req.problem.split()) / 50)

    return {
        "estimated_tokens_input": estimated_input,
        "estimated_tokens_output": estimated_output,
        "estimated_cost_usd": round(estimated_cost, 4),
        "estimated_duration_seconds": round(estimated_duration, 1),
        "preset": gate_preset_name,
        "tier": tier,
    }


# ─────────────────────────────────────────────────────────────────────
# FEEDBACK ENDPOINT
# ─────────────────────────────────────────────────────────────────────

from reasoner.infrastructure.persistence.feedback_store import FeedbackStore, FeedbackEntry

_feedback_store = FeedbackStore()


class FeedbackRequest(BaseModel):
    conversation_id: str
    message_id: str
    rating: str  # "up" | "down"
    reason: str | None = None
    comment: str | None = None
    context: dict | None = None


@app.post("/api/feedback")
async def submit_feedback(
    req: FeedbackRequest,
    csrf_checked = Depends(require_csrf),
):
    """
    Submit user feedback for a specific message.
    Persisted to SQLite for durability and queryability.
    """
    row_id = await _feedback_store.insert(
        FeedbackEntry(
            conversation_id=req.conversation_id,
            message_id=req.message_id,
            rating=req.rating,
            reason=req.reason,
            comment=req.comment,
            context=req.context,
        )
    )
    return {"status": "received", "id": row_id}


@app.get("/api/admin/feedback-stats", dependencies=[Depends(check_rate_limit)])
async def feedback_stats(
    days: int = Query(30, ge=1, le=365),
    admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
):
    """
    Admin-only endpoint returning aggregated feedback statistics.
    Requires X-Admin-Key header matching ADMIN_API_KEY.
    Uses constant-time comparison to mitigate timing attacks.
    """
    if not settings.ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not admin_key or not secrets.compare_digest(admin_key, settings.ADMIN_API_KEY):
        raise HTTPException(status_code=401, detail="Unauthorized")
    stats = await _feedback_store.get_stats(days=days)
    return {
        "total_entries": stats.total_entries,
        "upvotes": stats.upvotes,
        "downvotes": stats.downvotes,
        "downvote_reasons": stats.downvote_reasons,
        "avg_comment_length": stats.avg_comment_length,
        "entries_with_context": stats.entries_with_context,
        "period_days": stats.period_days,
    }


# ─────────────────────────────────────────────────────────────────────
# HEALTH CHECK ENDPOINT
# ─────────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    """
    Comprehensive health check endpoint.

    Returns system status, memory usage, and provider availability.
    Uses cached connections for Postgres and Redis (Critical Enhancement 5.6).
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

    # Postgres check — use cached pool (Critical Enhancement 5.6)
    global _health_postgres_pool
    try:
        if _health_postgres_pool is None:
            import asyncpg
            dsn = settings.DATABASE_URL.replace("+asyncpg", "")
            _health_postgres_pool = await asyncpg.create_pool(dsn, min_size=1, max_size=2)
        await _health_postgres_pool.fetchval("SELECT 1")
        health["checks"]["postgres"] = {"status": "ok"}
        # Update pool metrics (Critical Enhancement 7.6)
        from reasoner.api.metrics import REASONER_POSTGRES_POOL_SIZE, REASONER_POSTGRES_POOL_FREE
        REASONER_POSTGRES_POOL_SIZE.set(_health_postgres_pool.get_size())
        REASONER_POSTGRES_POOL_FREE.set(_health_postgres_pool.get_size() - _health_postgres_pool.get_idle_size())
    except Exception as e:
        health["checks"]["postgres"] = {"status": "error", "reason": str(e)}

    # Redis check
    try:
        from reasoner.infrastructure.redis.client import get_redis
        redis = get_redis()
        await redis.ping()
        health["checks"]["redis"] = {"status": "ok"}
        # Update Redis pool metrics (Critical Enhancement 7.6)
        from reasoner.api.metrics import REASONER_REDIS_POOL_SIZE
        pool_info = redis.connection_pool.max_connections
        REASONER_REDIS_POOL_SIZE.set(pool_info or 0)
    except Exception as e:
        health["checks"]["redis"] = {"status": "error", "reason": str(e)}

    # Stripe check (optional — don't fail health if Stripe is down)
    try:
        stripe_key = os.environ.get("STRIPE_SECRET_KEY", "")
        if stripe_key:
            # Lightweight check: key is present (avoid actual API call on every health ping)
            health["checks"]["stripe"] = {"status": "ok"}
        else:
            health["checks"]["stripe"] = {"status": "ok", "reason": "not configured"}
    except Exception as e:
        health["checks"]["stripe"] = {"status": "warning", "reason": str(e)}

    # Determine overall status
    if any(c.get("status") == "error" for c in health["checks"].values()):
        health["status"] = "unhealthy"
    elif any(c.get("status") in ("warning", "degraded") for c in health["checks"].values()):
        health["status"] = "degraded"

    return health


