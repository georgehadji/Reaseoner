"""
SaaS Router — All new SaaS-related API endpoints.

This router is mounted in api/__init__.py to keep the main file
from growing uncontrollably.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from reasoner.domain.saas import User
from reasoner.api.dependencies import get_current_user, get_optional_user

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
