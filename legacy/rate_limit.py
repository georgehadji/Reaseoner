"""
Reasoner Pipeline - Rate Limiting
Token bucket rate limiter for API endpoints.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

# Try to import slowapi, but provide fallback if not available
try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    SLOWAPI_AVAILABLE = True
except ImportError:
    SLOWAPI_AVAILABLE = False
    Limiter = None
    get_remote_address = None
    RateLimitExceeded = None


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_minute: int = 30
    requests_per_hour: int = 200
    burst_size: int = 10


class TokenBucket:
    """
    Token bucket implementation for rate limiting.
    """

    def __init__(
        self,
        capacity: int,
        refill_rate: float,  # tokens per second
    ):
        self.capacity = capacity
        self.tokens = float(capacity)
        self.refill_rate = refill_rate
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from the bucket.
        Returns True if successful, False if rate limited.
        """
        async with self._lock:
            self._refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.last_refill

        # Add tokens based on elapsed time
        new_tokens = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_refill = now


class RateLimiter:
    """
    Multi-level rate limiter using token buckets.
    """

    def __init__(self, config: RateLimitConfig | None = None):
        self.config = config or RateLimitConfig()

        # Per-minute bucket
        self.minute_bucket = TokenBucket(
            capacity=self.config.requests_per_minute,
            refill_rate=self.config.requests_per_minute / 60.0,
        )

        # Per-hour bucket
        self.hour_bucket = TokenBucket(
            capacity=self.config.requests_per_hour,
            refill_rate=self.config.requests_per_hour / 3600.0,
        )

        # Burst bucket for short-term spikes
        self.burst_bucket = TokenBucket(
            capacity=self.config.burst_size,
            refill_rate=self.config.burst_size / 10.0,  # Refill over 10 seconds
        )

    async def check_rate_limit(self) -> tuple[bool, dict[str, Any]]:
        """
        Check if request is allowed.
        Returns (allowed, rate_limit_info).
        """
        # Try burst first (most restrictive for spikes)
        if not await self.burst_bucket.consume():
            return False, {
                "error": "Rate limit exceeded (burst)",
                "retry_after": self._calculate_retry_time(self.burst_bucket),
            }

        # Check per-minute limit
        if not await self.minute_bucket.consume():
            return False, {
                "error": "Rate limit exceeded (per minute)",
                "retry_after": self._calculate_retry_time(self.minute_bucket),
            }

        # Check per-hour limit
        if not await self.hour_bucket.consume():
            return False, {
                "error": "Rate limit exceeded (per hour)",
                "retry_after": self._calculate_retry_time(self.hour_bucket),
            }

        return True, {"allowed": True}

    def _calculate_retry_time(self, bucket: TokenBucket) -> int:
        """Calculate seconds until a token becomes available."""
        tokens_needed = 1
        if bucket.tokens < tokens_needed:
            tokens_short = tokens_needed - bucket.tokens
            return int(tokens_short / bucket.refill_rate) + 1
        return 0

    def get_status(self) -> dict[str, Any]:
        """Get current rate limit status."""
        return {
            "requests_per_minute": self.config.requests_per_minute,
            "requests_per_hour": self.config.requests_per_hour,
            "burst_size": self.config.burst_size,
            "minute_bucket_tokens": round(self.minute_bucket.tokens, 2),
            "hour_bucket_tokens": round(self.hour_bucket.tokens, 2),
            "burst_bucket_tokens": round(self.burst_bucket.tokens, 2),
        }


# Global rate limiter instance
_rate_limiter: RateLimiter | None = None


def get_rate_limiter(config: RateLimitConfig | None = None) -> RateLimiter:
    """Get or create global rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(config)
    return _rate_limiter


# SlowAPI integration (if available)
def create_limiter():
    """Create SlowAPI limiter if available."""
    if SLOWAPI_AVAILABLE:
        return Limiter(key_func=get_remote_address)
    return None


def is_slowapi_available() -> bool:
    """Check if slowapi is available."""
    return SLOWAPI_AVAILABLE