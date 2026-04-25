"""Stripe webhook receiver with signature verification and idempotency."""

from __future__ import annotations

import os
import logging

import stripe
from fastapi import Request

from reasoner.infrastructure.billing.stripe_adapter import StripeBillingAdapter
from reasoner.infrastructure.redis.client import get_redis
from reasoner.application.services.billing_service import BillingService

logger = logging.getLogger(__name__)

# TTL for webhook deduplication (24 hours to cover Stripe retry window)
WEBHOOK_DEDUP_TTL_SECONDS = 86400


async def handle_stripe_webhook(request: Request) -> dict:
    """
    Receive and process Stripe webhook events.

    Returns:
        {"status": "ok"} with HTTP 200 even on processing errors
        to prevent infinite Stripe retries (Critical Enhancement 4.3).
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

    # Verify signature if secret is configured
    if webhook_secret:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except ValueError:
            logger.warning("Stripe webhook: invalid payload")
            return {"status": "ok"}
        except stripe.error.SignatureVerificationError:
            logger.warning("Stripe webhook: invalid signature")
            return {"status": "ok"}
    else:
        # Dev/test mode: parse JSON directly
        import json
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            logger.warning("Stripe webhook: invalid JSON payload")
            return {"status": "ok"}

    event_id = event.get("id", "unknown")
    event_type = event.get("type", "unknown")
    logger.info("Stripe webhook received: %s (id=%s)", event_type, event_id)

    # Deduplication: skip if we've already processed this event (Critical Enhancement 4.9)
    redis = get_redis()
    dedup_key = f"stripe_webhook:{event_id}"
    try:
        already_processed = await redis.get(dedup_key)
        if already_processed:
            logger.info("Stripe webhook deduplicated: %s", event_id)
            return {"status": "ok"}
        await redis.setex(dedup_key, WEBHOOK_DEDUP_TTL_SECONDS, "1")
    except Exception as exc:
        logger.warning("Redis dedup check failed (proceeding anyway): %s", exc)

    # Process the event
    try:
        adapter = StripeBillingAdapter()
        service = BillingService(adapter)
        await service.handle_webhook(event)
    except Exception as exc:
        logger.exception("Stripe webhook processing failed for event %s: %s", event_id, exc)
        # Still return 200 to prevent Stripe retries (Critical Enhancement 4.3)

    return {"status": "ok"}
