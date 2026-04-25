"""
SaaS Router — All new SaaS-related API endpoints.

This router is mounted in api/__init__.py to keep the main file
from growing uncontrollably.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends

from reasoner.domain.saas import User, SubscriptionTier
from reasoner.application.services.quota_service import TIER_LIMITS
from reasoner.api.dependencies import get_current_user, get_optional_user, _get_quota_service

router = APIRouter(prefix="/api", tags=["saas"])


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
