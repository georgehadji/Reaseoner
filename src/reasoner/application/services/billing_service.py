"""Billing Service — Orchestrates checkout, portal, and webhook sync."""

from __future__ import annotations

import logging

from reasoner.domain.saas import SubscriptionTier
from reasoner.application.ports.billing_port import BillingPort

logger = logging.getLogger(__name__)


class BillingService:
    def __init__(self, port: BillingPort):
        self._port = port

    async def create_checkout(
        self,
        user_id: str,
        tier: SubscriptionTier,
        success_url: str,
        cancel_url: str,
    ) -> str:
        return await self._port.create_checkout_session(user_id, tier, success_url, cancel_url)

    async def create_portal(self, user_id: str, return_url: str) -> str:
        return await self._port.create_portal_session(user_id, return_url)

    async def handle_webhook(self, event: dict) -> None:
        """Idempotent webhook processing with subscription persistence."""
        sub = await self._port.sync_subscription(event)

        # Persist to database
        from reasoner.infrastructure.persistence.subscription_repo import PostgresSubscriptionRepository
        from reasoner.core.settings import settings

        repo = PostgresSubscriptionRepository(
            settings.DATABASE_URL.replace("+asyncpg", ""),
            pool_size=10,
        )

        event_type = event.get("type", "")

        if event_type == "customer.subscription.deleted":
            # Downgrade to free — update subscription status
            if sub.stripe_subscription_id:
                await repo.set_subscription_status(
                    sub.stripe_subscription_id,
                    "cancelled",
                )
                await repo.sync_quota_for_subscription(sub)
            return

        if event_type == "invoice.payment_failed":
            if sub.stripe_subscription_id:
                await repo.set_subscription_status(
                    sub.stripe_subscription_id,
                    "past_due",
                )
            return

        if event_type == "invoice.payment_succeeded":
            # Payment succeeded — ensure subscription is active and reset usage for the new period
            if sub.stripe_subscription_id:
                await repo.set_subscription_status(
                    sub.stripe_subscription_id,
                    "active",
                )
                await repo.sync_quota_for_subscription(sub)
            return

        if event_type in ("checkout.session.completed", "customer.subscription.updated"):
            # Upsert subscription and sync quota
            await repo.upsert_subscription(sub)
            await repo.sync_quota_for_subscription(sub)
            logger.info(
                "Subscription synced for user %s: tier=%s status=%s",
                sub.user_id, sub.tier.value, sub.status.value
            )
            return

        logger.debug("Unhandled Stripe event type: %s", event_type)
