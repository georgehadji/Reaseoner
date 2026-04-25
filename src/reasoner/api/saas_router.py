"""
SaaS Router — All new SaaS-related API endpoints.

This router is mounted in api/__init__.py to keep the main file
from growing uncontrollably.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
from datetime import datetime, timezone, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from reasoner.domain.saas import User, SubscriptionTier
from reasoner.application.services.quota_service import TIER_LIMITS
from reasoner.api.dependencies import (
    get_current_user,
    get_optional_user,
    _get_quota_service,
    security,
)
from reasoner.rate_limiter import get_rate_limiter, RateLimitConfig
from reasoner.core.settings import settings

router = APIRouter(prefix="/api", tags=["saas"])

# Strict rate limiter for sensitive endpoints (Critical Enhancement 6.4)
_strict_rate_limiter = get_rate_limiter(
    RateLimitConfig(
        requests_per_minute=5,
        requests_per_hour=20,
        burst_size=2,
    )
)


async def _check_strict_rate_limit(request: Request):
    """Rate limit sensitive endpoints (export, delete) to prevent DoS."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else "unknown"
    user = getattr(request.state, "user", None)
    client_id = f"user:{user.id}" if user else f"ip:{ip}"
    allowed, info = await _strict_rate_limiter.is_allowed(client_id)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={"error": "Rate limit exceeded for sensitive endpoint", "retry_after": int(info.get("retry_after", 60))},
            headers={"Retry-After": str(int(info.get("retry_after", 60)))},
        )


async def _log_auth_event(
    user_id: UUID | None,
    event_type: str,
    ip: str | None,
    user_agent: str | None,
) -> None:
    """Insert an auth audit log row (Critical Enhancement 6.3)."""
    from reasoner.infrastructure.persistence.quota_repo_postgres import PostgresQuotaRepository
    dsn = settings.DATABASE_URL.replace("+asyncpg", "")
    repo = PostgresQuotaRepository(dsn, pool_size=2)
    pool = await repo._get_pool()
    await pool.execute(
        """
        INSERT INTO auth_audit_log (user_id, event_type, ip_address, user_agent)
        VALUES ($1, $2, $3, $4)
        """,
        str(user_id) if user_id else None,
        event_type,
        ip,
        user_agent,
    )


@router.get("/auth/me")
async def get_me(user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
    }


@router.get("/auth/me/optional")
async def get_me_optional(user: User | None = Depends(get_optional_user)):
    """Return user if authenticated, null otherwise. Useful for UI state hydration."""
    if user is None:
        return {"authenticated": False}
    return {
        "authenticated": True,
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
    }


@router.get("/quota")
async def get_quota_status(user: User = Depends(get_current_user)):
    """Return current usage and remaining quota."""
    service = _get_quota_service()
    result = await service.check(str(user.id), SubscriptionTier.FREE)
    # TODO Phase 4: use actual user tier
    used = (TIER_LIMITS[SubscriptionTier.FREE] - result.remaining) if result.remaining >= 0 else 0
    return {
        "used": used,
        "max": TIER_LIMITS[SubscriptionTier.FREE],
        "remaining": result.remaining,
        "reset_date": (datetime.now(timezone.utc).replace(day=1) + timedelta(days=32)).replace(day=1).isoformat(),
    }


# ── GDPR Endpoints (Critical Enhancement 6.4) ──

@router.get("/account/export")
async def export_data(
    request: Request,
    user: User = Depends(get_current_user),
    _: None = Depends(_check_strict_rate_limit),
):
    """Export all personal data as JSON (GDPR Article 20).

    Critical Enhancement 6.7: capped at 1000 query logs to prevent OOM.
    """
    from reasoner.infrastructure.persistence.quota_repo_postgres import PostgresQuotaRepository
    dsn = settings.DATABASE_URL.replace("+asyncpg", "")
    repo = PostgresQuotaRepository(dsn, pool_size=2)
    pool = await repo._get_pool()

    profile = await pool.fetchrow("SELECT * FROM users WHERE id = $1", str(user.id))
    subscriptions = await pool.fetch("SELECT * FROM subscriptions WHERE user_id = $1", str(user.id))
    quotas = await pool.fetchrow("SELECT * FROM usage_quotas WHERE user_id = $1", str(user.id))
    queries = await pool.fetch(
        "SELECT * FROM query_audit_logs WHERE user_id = $1 ORDER BY timestamp DESC LIMIT 1000",
        str(user.id),
    )

    await _log_auth_event(
        user.id, "data_export",
        request.client.host if request.client else None,
        request.headers.get("User-Agent"),
    )

    return {
        "profile": dict(profile) if profile else {},
        "subscriptions": [dict(s) for s in subscriptions],
        "quota": dict(quotas) if quotas else {},
        "queries": [dict(q) for q in queries],
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/account/delete")
async def delete_account(
    request: Request,
    user: User = Depends(get_current_user),
    _: None = Depends(_check_strict_rate_limit),
):
    """Hard delete user and all data (GDPR Article 17).

    Critical Enhancement 6.2: cancels active Stripe subscription first.
    """
    from reasoner.infrastructure.persistence.quota_repo_postgres import PostgresQuotaRepository
    dsn = settings.DATABASE_URL.replace("+asyncpg", "")
    repo = PostgresQuotaRepository(dsn, pool_size=2)
    pool = await repo._get_pool()

    # Find active subscription to cancel Stripe billing
    sub_row = await pool.fetchrow(
        "SELECT external_subscription_id FROM subscriptions WHERE user_id = $1 AND status = 'active' LIMIT 1",
        str(user.id),
    )
    if sub_row and sub_row["external_subscription_id"]:
        try:
            from reasoner.infrastructure.billing.stripe_adapter import StripeBillingAdapter
            adapter = StripeBillingAdapter()
            await adapter.cancel_subscription(sub_row["external_subscription_id"])
        except Exception as exc:
            # Log but proceed with deletion — webhook will eventually sync
            import logging
            logging.getLogger(__name__).warning(
                "Failed to cancel Stripe subscription %s for user %s: %s",
                sub_row["external_subscription_id"], user.id, exc,
            )

    # Audit log before deletion
    await _log_auth_event(
        user.id, "account_delete",
        request.client.host if request.client else None,
        request.headers.get("User-Agent"),
    )

    # Cascade delete handled by ON DELETE CASCADE in schema
    await pool.execute("DELETE FROM users WHERE id = $1", str(user.id))

    return {"status": "deleted", "user_id": str(user.id)}
