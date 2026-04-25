"""Shared Redis connection pool for all Redis-backed features."""

from __future__ import annotations

import os
from typing import Optional

import redis.asyncio as aioredis

_pool: Optional[aioredis.Redis] = None


def get_redis() -> aioredis.Redis:
    """Get or create shared Redis client."""
    global _pool
    if _pool is None:
        url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        _pool = aioredis.from_url(url, decode_responses=True)
    return _pool


def set_redis(client: aioredis.Redis) -> None:
    """Override Redis client (useful for tests)."""
    global _pool
    _pool = client
