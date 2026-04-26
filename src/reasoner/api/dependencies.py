"""
FastAPI Dependency Injectors for SaaS Auth.

These functions are used as FastAPI Depends() callables.
They resolve authentication and authorization without
polluting route handlers with auth logic.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from reasoner.api.client_ip import get_client_ip
from reasoner.domain.saas import User, SubscriptionTier, QuotaResult
from reasoner.application.ports.auth_port import AuthPort
from reasoner.application.services.auth_service import AuthService
from reasoner.application.services.quota_service import QuotaService, TIER_LIMITS
from reasoner.infrastructure.auth import get_auth_adapter
from reasoner.auth import AuthenticationError as LegacyAuthError
from reasoner.core.settings import settings
from reasoner.rate_limiter import RateLimitConfig, get_rate_limiter
from reasoner.presets import get_preset_tier

# ── Rate Limiter Singleton ──
_rate_limiter_instance: RateLimiter | None = None

def _get_rate_limiter_instance() -> RateLimiter:
    """Factory for RateLimiter instance."""
    global _rate_limiter_instance
    if _rate_limiter_instance is None:
        _rate_limiter_instance = get_rate_limiter(
            RateLimitConfig(
                requests_per_minute=settings.RATE_LIMIT_PER_MINUTE,
                requests_per_hour=settings.RATE_LIMIT_PER_HOUR,
                burst_size=settings.RATE_LIMIT_BURST,
            )
        )
    return _rate_limiter_instance

def _reset_rate_limiter_instance() -> None:
    """Reset rate limiter singleton (useful for tests)."""
    global _rate_limiter_instance
    _rate_limiter_instance = None

security = HTTPBearer(auto_error=False)


_BASE64URL_RE = re.compile(r'^[A-Za-z0-9_-]+$')


def _looks_like_jwt(token: str) -> bool:
    """Heuristic: JWTs have exactly 2 dots separating 3 base64url segments."""
    if token.count(".") != 2:
        return False
    parts = token.split(".")
    if any(len(p) == 0 for p in parts):
        return False
    if not all(_BASE64URL_RE.match(p) for p in parts):
        return False
    # Additional safety: header should decode to reasonable length
    if len(parts[0]) < 4:
        return False
    return True


async def _resolve_auth_token(token: str) -> User:
    """
    Unified token resolution.

    Strategy:
    1. If token looks like JWT → route to AuthPort (Supabase/Local)
    2. Else if ENABLE_LEGACY_API_KEY=true → route to legacy AuthManager
    3. Else → reject
    """
    if _looks_like_jwt(token):
        adapter: AuthPort = get_auth_adapter()
        service = AuthService(adapter)
        return await service.authenticate(token)

    # Legacy API key path (only if explicitly enabled)
    if os.environ.get("ENABLE_LEGACY_API_KEY", "false").lower() == "true":
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            "Legacy API key authentication is enabled. This is deprecated and will be removed in v2.3. "
            "Migrate to JWT authentication."
        )
        from reasoner.auth import get_auth_manager
        auth_manager = get_auth_manager()
        try:
            api_key = await auth_manager.authenticate(token)
            # Map legacy API key to canonical User
            # Safe deterministic UUID from key hash (SHA-256, take first 16 bytes)
            return User(
                id=UUID(bytes=hashlib.sha256(api_key.key_hash.encode()).digest()[:16]),
                email=f"apikey-{api_key.key_hash[:8]}@internal",
                display_name=api_key.name,
            )
        except LegacyAuthError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.message)

    raise HTTPException(
        status_code=401,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> User:
    """
    Require valid authentication (JWT or legacy API key).

    Raises HTTPException 401 if missing or invalid.
    Stores resolved user in request.state for audit middleware.
    """
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user = await _resolve_auth_token(credentials.credentials)
        request.state.user = user
        return user
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {exc}")


async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[User]:
    """Optional authentication — returns None if no valid credentials."""
    if not credentials:
        return None
    try:
        user = await _resolve_auth_token(credentials.credentials)
        request.state.user = user
        return user
    except Exception:
        return None


def require_tier(min_tier: SubscriptionTier):
    """
    Factory that returns a FastAPI dependency enforcing minimum subscription tier.

    Usage:
        @app.post("/api/premium-only")
        async def premium_route(user: User = Depends(require_tier(SubscriptionTier.PRO))):
            ...
    """
    from fastapi import HTTPException

    async def checker(user: User = Depends(get_current_user)) -> User:
        tier_order = {SubscriptionTier.FREE: 0, SubscriptionTier.PRO: 1, SubscriptionTier.ENTERPRISE: 2}
        # Fetch actual tier from subscription DB if available
        user_tier = SubscriptionTier.FREE
        try:
            from reasoner.infrastructure.persistence.subscription_repo import PostgresSubscriptionRepository
            repo = PostgresSubscriptionRepository(settings.DATABASE_URL)
            sub = await repo.get_subscription_by_user(str(user.id))
            if sub and sub.status.value == "active":
                user_tier = sub.tier
        except Exception:
            # Fallback to FREE if subscription DB is unavailable
            pass
        if tier_order.get(user_tier, 0) < tier_order.get(min_tier, 0):
            raise HTTPException(
                status_code=403,
                detail=f"Tier upgrade required: {min_tier.value} or higher",
            )
        return user

    return checker


async def check_rate_limit(
    request: Request,
    user: User | None = Depends(get_optional_user),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    """
    Check rate limit using user_id if authenticated, otherwise IP.
    """
    rate_limiter = _get_rate_limiter_instance()

    if user is not None:
        # Authenticated user — use user_id as bucket key with tier multiplier
        # TODO(#501): fetch tier from subscription
        client_id = f"user:{user.id}"
        try:
            allowed, info = await rate_limiter.is_allowed_for_user(client_id, tier="default")
        except Exception as exc:
            logger.error("Rate limiter error: %s", exc)
            allowed = True
            info = {"limit_minute": 60, "remaining_minute": 60, "retry_after": None}
    else:
        # Anonymous — use IP + User-Agent hash
        ip = get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "")
        client_id = f"{ip}:{hashlib.sha256(user_agent.encode()).hexdigest()[:8]}"
        try:
            allowed, info = await rate_limiter.is_allowed(client_id)
        except Exception as exc:
            logger.error("Rate limiter error: %s", exc)
            allowed = True
            info = {"limit_minute": 60, "remaining_minute": 60, "retry_after": None}

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
            },
        )
    return True


# ── Quota Service Singleton ──
_quota_service: QuotaService | None = None


def _get_quota_service() -> QuotaService:
    """Factory for QuotaService with cached Postgres repository.

    Caches the service instance to avoid creating new connection pools
    on every request (Critical Enhancement 3.1).
    """
    global _quota_service
    if _quota_service is None:
        # Deferred imports: asyncpg (via PostgresQuotaRepository) hangs on
        # import at startup due to platform.uname() DNS resolution in compat.py.
        from reasoner.infrastructure.persistence.quota_repo_postgres import PostgresQuotaRepository
        from reasoner.infrastructure.persistence.cached_quota_repo import CachedQuotaRepository
        dsn = settings.DATABASE_URL.replace("+asyncpg", "")
        pg_repo = PostgresQuotaRepository(dsn, pool_size=int(os.environ.get("DB_POOL_SIZE", "10")))
        cached_repo = CachedQuotaRepository(pg_repo)
        _quota_service = QuotaService(cached_repo)
    return _quota_service


def _reset_quota_service() -> None:
    """Reset quota service singleton (useful for tests)."""
    global _quota_service
    _quota_service = None


async def check_quota(
    user: User = Depends(get_current_user),
) -> QuotaResult:
    """
    FastAPI dependency: check if user has remaining quota.
    Raises HTTPException 429 if exceeded.
    """
    # TODO(#502): fetch actual subscription tier from DB
    # For now, use free tier as conservative default
    user_tier = SubscriptionTier.FREE

    service = _get_quota_service()
    try:
        result = await service.check(str(user.id), user_tier)
    except Exception:
        # If DB is unavailable, allow the request (fail open) rather than
        # hard-failing every authenticated request.
        logger = logging.getLogger(__name__)
        logger.warning("Quota check failed due to DB error, allowing request")
        return QuotaResult(allowed=True, remaining=-1)

    if not result.allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Quota exceeded",
                "message": result.reason,
                "remaining": result.remaining,
                "retry_after": result.retry_after,
                "upgrade_url": "/pricing",
            },
            headers={
                "Retry-After": str(result.retry_after or 3600),
                "X-RateLimit-Remaining": "0",
            },
        )
    return result


async def check_preset_access(
    preset: str,
    user: User = Depends(get_current_user),
) -> None:
    """
    FastAPI dependency: enforce preset tier requirements.
    Raises HTTPException 403 if preset requires higher tier.
    """
    required = get_preset_tier(preset)
    if required == SubscriptionTier.FREE:
        return

    tier_order = {SubscriptionTier.FREE: 0, SubscriptionTier.PRO: 1, SubscriptionTier.ENTERPRISE: 2}

    # Fetch user's subscription tier from DB
    user_tier = SubscriptionTier.FREE
    try:
        from reasoner.infrastructure.persistence.subscription_repo import PostgresSubscriptionRepository
        dsn = settings.DATABASE_URL.replace("+asyncpg", "")
        repo = PostgresSubscriptionRepository(dsn, pool_size=2)
        sub = await repo.get_subscription_by_user(str(user.id))
        if sub is not None and sub.status.value == "active":
            user_tier = sub.tier
    except Exception:
        # If DB is unavailable, fall back to free tier (conservative)
        pass

    if tier_order[user_tier] < tier_order[required]:
        raise HTTPException(
            status_code=403,
            detail=f"Preset '{preset}' requires {required.value} tier. Upgrade at /pricing.",
        )


async def check_quota_if_authenticated(
    user: User | None = Depends(get_optional_user),
) -> QuotaResult | None:
    """Only check quota if user is authenticated."""
    if user is None:
        return None
    return await check_quota(user)
