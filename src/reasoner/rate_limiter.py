"""
Production-Ready Rate Limiter
Token bucket algorithm with Redis-like sliding window.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Optional
import asyncio


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_size: int = 10  # Allow short bursts


@dataclass
class ClientBucket:
    """Token bucket for a client."""
    tokens: float = field(default=0.0)
    last_update: float = field(default_factory=time.time)
    requests_minute: int = 0
    requests_hour: int = 0
    minute_window_start: float = field(default_factory=time.time)
    hour_window_start: float = field(default_factory=time.time)


class RateLimiter:
    """
    Production rate limiter with multiple algorithms.
    
    Features:
    - Token bucket for smooth rate limiting
    - Sliding window for accurate per-minute/hour limits
    - Per-client tracking
    - Async-safe
    """
    
    from reasoner.core.constants import MAX_RATE_LIMIT_BUCKETS
    _MAX_BUCKETS: int = MAX_RATE_LIMIT_BUCKETS
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self._buckets: Dict[str, ClientBucket] = defaultdict(ClientBucket)
        self._lock = asyncio.Lock()
    
    def _get_bucket(self, client_id: str) -> ClientBucket:
        """Get or create bucket for client."""
        if client_id not in self._buckets:
            if len(self._buckets) >= self._MAX_BUCKETS:
                oldest = next(iter(self._buckets))
                del self._buckets[oldest]
            bucket = ClientBucket()
            bucket.tokens = self.config.burst_size  # Start with full burst
            self._buckets[client_id] = bucket
        return self._buckets[client_id]
    
    def _refill_tokens(self, bucket: ClientBucket) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - bucket.last_update
        
        # Refill rate: 1 token per (60 / requests_per_minute) seconds
        refill_rate = self.config.requests_per_minute / 60.0
        bucket.tokens = min(
            self.config.burst_size,
            bucket.tokens + (elapsed * refill_rate)
        )
        bucket.last_update = now
    
    def _reset_windows_if_needed(self, bucket: ClientBucket) -> None:
        """Reset sliding windows if expired."""
        now = time.time()
        
        # Reset minute window
        if now - bucket.minute_window_start >= 60:
            bucket.requests_minute = 0
            bucket.minute_window_start = now
        
        # Reset hour window
        if now - bucket.hour_window_start >= 3600:
            bucket.requests_hour = 0
            bucket.hour_window_start = now
    
    async def is_allowed(self, client_id: str) -> tuple[bool, dict]:
        """
        Check if request is allowed for client.
        
        Returns:
            (allowed: bool, info: dict with retry-after and limits)
        """
        async with self._lock:
            bucket = self._get_bucket(client_id)
            self._refill_tokens(bucket)
            self._reset_windows_if_needed(bucket)
            
            info = {
                "limit_minute": self.config.requests_per_minute,
                "limit_hour": self.config.requests_per_hour,
                "remaining_minute": self.config.requests_per_minute - bucket.requests_minute,
                "remaining_hour": self.config.requests_per_hour - bucket.requests_hour,
                "retry_after": None,
            }
            
            # Check per-minute limit
            if bucket.requests_minute >= self.config.requests_per_minute:
                info["retry_after"] = 60 - (time.time() - bucket.minute_window_start)
                info["reason"] = "per_minute_limit"
                return False, info
            
            # Check per-hour limit
            if bucket.requests_hour >= self.config.requests_per_hour:
                info["retry_after"] = 3600 - (time.time() - bucket.hour_window_start)
                info["reason"] = "per_hour_limit"
                return False, info
            
            # Check token bucket
            if bucket.tokens < 1:
                # Calculate time until next token
                tokens_needed = 1 - bucket.tokens
                refill_rate = self.config.requests_per_minute / 60.0
                info["retry_after"] = tokens_needed / refill_rate
                info["reason"] = "burst_limit"
                return False, info
            
            # Consume token
            bucket.tokens -= 1
            bucket.requests_minute += 1
            bucket.requests_hour += 1
            
            # Update remaining
            info["remaining_minute"] = self.config.requests_per_minute - bucket.requests_minute
            info["remaining_hour"] = self.config.requests_per_hour - bucket.requests_hour
            
            return True, info
    
    async def record_request(self, client_id: str) -> None:
        """Record a successful request (alternative to is_allowed)."""
        async with self._lock:
            bucket = self._get_bucket(client_id)
            bucket.requests_minute += 1
            bucket.requests_hour += 1
    
    def get_client_stats(self, client_id: str) -> dict:
        """Get rate limit stats for client."""
        bucket = self._get_bucket(client_id)
        return {
            "tokens": bucket.tokens,
            "requests_minute": bucket.requests_minute,
            "requests_hour": bucket.requests_hour,
            "limit_minute": self.config.requests_per_minute,
            "limit_hour": self.config.requests_per_hour,
        }
    
    def reset_client(self, client_id: str) -> None:
        """Reset rate limits for client."""
        if client_id in self._buckets:
            del self._buckets[client_id]
    
    def reset_all(self) -> None:
        """Reset all rate limits."""
        self._buckets.clear()


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter(config: Optional[RateLimitConfig] = None) -> RateLimiter:
    """Get or create global rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(config)
    return _rate_limiter
