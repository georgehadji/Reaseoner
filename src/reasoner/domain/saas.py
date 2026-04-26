"""
SaaS Domain Entities

Pure dataclasses representing the billing, auth, and quota domain.
These entities know nothing about HTTP, databases, or third-party APIs.

⚠️ CRITICAL ENHANCEMENTS (PHASE_ENHANCEMENTS.md 1.1–1.5):
- Use datetime.now(timezone.utc) instead of deprecated datetime.utcnow()
- Freeze Subscription dataclass for consistency with User and QuotaResult
- Add __slots__ to frequently-instantiated entities (User, QuotaResult) for ~40 bytes savings per instance
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID


class SubscriptionTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"
    TRIALING = "trialing"


@dataclass(frozen=True, slots=True)
class User:
    """Canonical user entity — auth-provider agnostic."""
    id: UUID
    email: str
    display_name: Optional[str] = None
    scopes: set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class Subscription:
    """A user's subscription plan. Frozen for immutability consistency."""
    id: UUID
    user_id: UUID
    tier: SubscriptionTier
    status: SubscriptionStatus
    stripe_subscription_id: Optional[str] = None
    current_period_end: Optional[datetime] = None
    stripe_customer_id: Optional[str] = None  # NEW: Store Stripe customer ID (Enhancement 4.4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class UsageQuota:
    """Per-user query quota, reset monthly."""
    user_id: UUID
    tier: SubscriptionTier
    used_queries: int = 0
    max_queries: int = 20          # -1 means unlimited
    period_start: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    )
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class QueryAuditLog:
    """Immutable record of a single pipeline execution."""
    id: UUID
    user_id: UUID
    preset: str
    method: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True, slots=True)
class QuotaResult:
    """Result of a quota check."""
    allowed: bool
    remaining: int
    retry_after: Optional[int] = None   # seconds until reset (computed from period_start + 1 month)
    reason: Optional[str] = None
