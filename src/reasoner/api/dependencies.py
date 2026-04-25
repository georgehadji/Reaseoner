"""
FastAPI Dependency Injectors for SaaS Auth.

These functions are used as FastAPI Depends() callables.
They resolve authentication and authorization without
polluting route handlers with auth logic.
"""

from __future__ import annotations

import hashlib
import os
import re
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from reasoner.domain.saas import User, SubscriptionTier
from reasoner.application.ports.auth_port import AuthPort
from reasoner.application.services.auth_service import AuthService
from reasoner.infrastructure.auth import get_auth_adapter
from reasoner.auth import AuthenticationError as LegacyAuthError
from reasoner.core.settings import settings
from reasoner.rate_limiter import RateLimitConfig, get_rate_limiter

security = HTTPBearer(auto_error=False)
rate_limiter = get_rate_limiter(
    RateLimitConfig(
        requests_per_minute=settings.RATE_LIMIT_PER_MINUTE,
        requests_per_hour=settings.RATE_LIMIT_PER_HOUR,
        burst_size=settings.RATE_LIMIT_BURST,
    )
)


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
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> User:
    """
    Require valid authentication (JWT or legacy API key).

    Raises HTTPException 401 if missing or invalid.
    """
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return await _resolve_auth_token(credentials.credentials)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {exc}")


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[User]:
    """Optional authentication — returns None if no valid credentials."""
    if not credentials:
        return None
    try:
        return await _resolve_auth_token(credentials.credentials)
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
    async def checker(user: User = Depends(get_current_user)) -> User:
        # TODO: In Phase 3, fetch subscription from DB and compare tiers.
        # For Phase 2, all authenticated users pass (auth gate only).
        # Placeholder logic:
        tier_order = {SubscriptionTier.FREE: 0, SubscriptionTier.PRO: 1, SubscriptionTier.ENTERPRISE: 2}
        # user_tier = await get_user_subscription_tier(user.id)
        # if tier_order[user_tier] < tier_order[min_tier]:
        #     raise HTTPException(status_code=403, detail=f"Requires {min_tier.value} tier")
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
    if user is not None:
        # Authenticated user — use user_id as bucket key with tier multiplier
        # TODO Phase 3: fetch tier from subscription
        client_id = f"user:{user.id}"
        allowed, info = await rate_limiter.is_allowed_for_user(client_id, tier="default")
    else:
        # Anonymous — use IP + User-Agent hash
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")
        client_id = f"{ip}:{hashlib.md5(user_agent.encode()).hexdigest()[:8]}"
        allowed, info = await rate_limiter.is_allowed(client_id)

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
