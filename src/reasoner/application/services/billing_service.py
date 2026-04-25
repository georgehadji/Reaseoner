"""
Billing Service — Orchestrates checkout, portal, and webhook sync.
"""

from __future__ import annotations

from reasoner.domain.saas import SubscriptionTier
from reasoner.application.ports.billing_port import BillingPort


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
        """Idempotent webhook processing."""
        await self._port.sync_subscription(event)
