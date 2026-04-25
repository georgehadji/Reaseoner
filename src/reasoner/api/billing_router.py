"""FastAPI router for all billing endpoints."""

from __future__ import annotations

import os
from fastapi import APIRouter, Depends, HTTPException, Request
from reasoner.domain.saas import User, SubscriptionTier
from reasoner.api.dependencies import get_current_user
from reasoner.infrastructure.billing.stripe_adapter import StripeBillingAdapter
from reasoner.application.services.billing_service import BillingService

router = APIRouter(prefix="/api/billing", tags=["billing"])


def _get_billing_service() -> BillingService:
    adapter = StripeBillingAdapter()
    return BillingService(adapter)


@router.post("/checkout")
async def create_checkout(
    request: Request,
    tier: str,
    user: User = Depends(get_current_user),
):
    """Create a Stripe Checkout session for upgrading."""
    try:
        tier_enum = SubscriptionTier(tier.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid tier: {tier}. Must be one of: free, pro, enterprise.")
    service = _get_billing_service()
    app_url = os.environ.get("APP_URL", "http://localhost:3000")
    url = await service.create_checkout(
        str(user.id),
        tier_enum,
        success_url=f"{app_url}/dashboard?checkout=success",
        cancel_url=f"{app_url}/pricing?checkout=cancel",
    )
    return {"checkout_url": url}


@router.post("/portal")
async def create_portal(
    user: User = Depends(get_current_user),
):
    """Create a Stripe Billing Portal session."""
    service = _get_billing_service()
    app_url = os.environ.get("APP_URL", "http://localhost:3000")
    url = await service.create_portal(str(user.id), f"{app_url}/dashboard")
    return {"portal_url": url}


@router.get("/subscription")
async def get_subscription(user: User = Depends(get_current_user)):
    """Get current subscription status from database."""
    from reasoner.infrastructure.persistence.subscription_repo import PostgresSubscriptionRepository
    from reasoner.core.settings import settings

    repo = PostgresSubscriptionRepository(
        settings.DATABASE_URL.replace("+asyncpg", ""),
        pool_size=10,
    )
    sub = await repo.get_subscription_by_user(str(user.id))
    if sub is None:
        return {"tier": "free", "status": "active"}
    return {
        "tier": sub.tier.value,
        "status": sub.status.value,
        "stripe_subscription_id": sub.stripe_subscription_id,
        "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
    }


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Public endpoint for Stripe webhooks."""
    from reasoner.infrastructure.billing.webhooks import handle_stripe_webhook
    return await handle_stripe_webhook(request)
