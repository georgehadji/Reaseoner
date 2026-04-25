"""Stripe implementation of BillingPort."""

from __future__ import annotations

import asyncio
import os
import logging
from uuid import UUID, uuid4

import stripe

from reasoner.domain.saas import Subscription, SubscriptionTier, SubscriptionStatus
from reasoner.application.ports.billing_port import BillingPort

logger = logging.getLogger(__name__)


class StripeBillingAdapter(BillingPort):
    def __init__(self, api_key: str | None = None):
        stripe.api_key = api_key or os.environ["STRIPE_SECRET_KEY"]

    async def create_checkout_session(
        self,
        user_id: str,
        tier: SubscriptionTier,
        success_url: str,
        cancel_url: str,
    ) -> str:
        price_id = self._price_id_for_tier(tier)
        session = await asyncio.to_thread(
            stripe.checkout.Session.create,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=user_id,
            allow_promotion_codes=True,
        )
        return session.url

    async def create_portal_session(self, user_id: str, return_url: str) -> str:
        # Lookup Stripe customer by user_id (stored in metadata)
        customers = await asyncio.to_thread(
            stripe.Customer.list,
            limit=1,
            metadata={"reasoner_user_id": user_id},
        )
        if not customers.data:
            raise ValueError(f"No Stripe customer found for user {user_id}")

        session = await asyncio.to_thread(
            stripe.billing_portal.Session.create,
            customer=customers.data[0].id,
            return_url=return_url,
        )
        return session.url

    async def sync_subscription(self, provider_event: dict) -> Subscription:
        event_type = provider_event.get("type")
        data = provider_event.get("data", {}).get("object", {})

        if event_type == "checkout.session.completed":
            return await self._handle_checkout_completed(data)
        elif event_type == "customer.subscription.updated":
            return await self._handle_subscription_updated(data)
        elif event_type == "customer.subscription.deleted":
            return await self._handle_subscription_deleted(data)

        # Return a no-op subscription for unhandled events
        return Subscription(
            id=uuid4(),
            user_id=uuid4(),
            tier=SubscriptionTier.FREE,
            status=SubscriptionStatus.CANCELLED,
        )

    def _price_id_for_tier(self, tier: SubscriptionTier) -> str:
        mapping = {
            SubscriptionTier.PRO: os.environ["STRIPE_PRO_PRICE_ID"],
            SubscriptionTier.ENTERPRISE: os.environ["STRIPE_ENTERPRISE_PRICE_ID"],
        }
        return mapping[tier]

    async def _handle_checkout_completed(self, session: dict) -> Subscription:
        # Extract user_id from client_reference_id
        user_id = session.get("client_reference_id")
        # Subscription object is in subscription field
        sub_id = session.get("subscription")
        stripe_sub = await asyncio.to_thread(stripe.Subscription.retrieve, sub_id)
        return self._stripe_sub_to_domain(stripe_sub, UUID(user_id))

    async def _handle_subscription_updated(self, stripe_sub: dict) -> Subscription:
        # Lookup user_id from customer metadata
        customer = await asyncio.to_thread(
            stripe.Customer.retrieve, stripe_sub["customer"]
        )
        user_id = customer.metadata.get("reasoner_user_id")
        return self._stripe_sub_to_domain(stripe_sub, UUID(user_id))

    async def _handle_subscription_deleted(self, stripe_sub: dict) -> Subscription:
        customer = await asyncio.to_thread(
            stripe.Customer.retrieve, stripe_sub["customer"]
        )
        user_id = customer.metadata.get("reasoner_user_id")
        return Subscription(
            id=uuid4(),
            user_id=UUID(user_id),
            tier=SubscriptionTier.FREE,
            status=SubscriptionStatus.CANCELLED,
            stripe_subscription_id=stripe_sub["id"],
            stripe_customer_id=stripe_sub.get("customer"),
        )

    def _stripe_sub_to_domain(self, stripe_sub: dict, user_id: UUID) -> Subscription:
        tier = self._tier_from_price(stripe_sub["items"]["data"][0]["price"]["id"])
        status_map = {
            "active": SubscriptionStatus.ACTIVE,
            "canceled": SubscriptionStatus.CANCELLED,
            "past_due": SubscriptionStatus.PAST_DUE,
            "trialing": SubscriptionStatus.TRIALING,
        }
        return Subscription(
            id=uuid4(),  # Enhancement 4.5: use uuid4() instead of UUID(int=0)
            user_id=user_id,
            tier=tier,
            status=status_map.get(stripe_sub["status"], SubscriptionStatus.CANCELLED),
            stripe_subscription_id=stripe_sub["id"],
            stripe_customer_id=stripe_sub.get("customer"),
            current_period_end=self._timestamp_to_datetime(stripe_sub.get("current_period_end")),
        )

    def _tier_from_price(self, price_id: str) -> SubscriptionTier:
        if price_id == os.environ.get("STRIPE_PRO_PRICE_ID"):
            return SubscriptionTier.PRO
        if price_id == os.environ.get("STRIPE_ENTERPRISE_PRICE_ID"):
            return SubscriptionTier.ENTERPRISE
        return SubscriptionTier.FREE

    async def cancel_subscription(self, stripe_subscription_id: str) -> None:
        """Immediately cancel a Stripe subscription."""
        await asyncio.to_thread(
            stripe.Subscription.delete,
            stripe_subscription_id,
        )

    def _timestamp_to_datetime(self, ts: int | None):
        from datetime import datetime, timezone
        if ts is None:
            return None
        return datetime.fromtimestamp(ts, tz=timezone.utc)
