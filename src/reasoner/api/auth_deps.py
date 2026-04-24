"""Authentication and rate-limiting FastAPI dependencies."""

from __future__ import annotations

import hashlib
from typing import Optional

import logging

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from reasoner.auth import AuthenticationError, get_auth_manager
from reasoner.api.csrf import verify_csrf_token

logger = logging.getLogger(__name__)
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

auth_manager = get_auth_manager()


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
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
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
            },
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
    except AuthenticationError as e:
        logger.warning("Invalid API key rejected in optional_auth: %s", e.message)
        return None


async def require_csrf(request: Request):
    """
    Require a valid CSRF token on state-changing requests.

    Reads the X-CSRF-Token header and validates its HMAC signature.
    Raises HTTPException(403) if missing, invalid, or if CSRF is
    misconfigured (no secret set).

    Can be disabled globally via CSRF_ENFORCE_BACKEND=false.
    """
    if not settings.CSRF_ENFORCE_BACKEND:
        return True

    token = request.headers.get("X-CSRF-Token")
    if not token:
        raise HTTPException(
            status_code=403,
            detail="Missing CSRF token. Include X-CSRF-Token header.",
        )

    try:
        valid = verify_csrf_token(token)
    except RuntimeError as e:
        logger.error("CSRF verification misconfigured: %s", e)
        raise HTTPException(
            status_code=500,
            detail="CSRF protection misconfigured on server.",
        )

    if not valid:
        raise HTTPException(
            status_code=403,
            detail="Invalid CSRF token.",
        )

    return True
