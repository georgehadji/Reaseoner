"""Prometheus metrics for Reasoner.

Critical Enhancements:
- 7.2: metrics_endpoint is async with asyncio.to_thread()
- 7.6: connection pool metrics for Postgres and Redis
"""

from __future__ import annotations

import asyncio
import time

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

# Request counters
REASONER_QUERIES_TOTAL = Counter(
    "reasoner_queries_total",
    "Total queries executed",
    ["tier", "preset", "status"],
)

REASONER_QUOTA_EXCEEDED_TOTAL = Counter(
    "reasoner_quota_exceeded_total",
    "Quota exceeded events",
    ["tier"],
)

REASONER_LLM_ERRORS_TOTAL = Counter(
    "reasoner_llm_errors_total",
    "LLM provider errors",
    ["provider"],
)

STRIPE_WEBHOOK_SIG_FAILURES = Counter(
    "stripe_webhook_signature_failures_total",
    "Stripe webhook signature verification failures",
)

# Latency histograms
REASONER_QUERY_DURATION = Histogram(
    "reasoner_query_duration_seconds",
    "Pipeline execution duration",
    ["preset"],
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0],
)

# Gauges
REASONER_ACTIVE_USERS = Gauge(
    "reasoner_active_users_total",
    "Unique users in last 24h",
)

# Connection pool metrics (Critical Enhancement 7.6)
REASONER_POSTGRES_POOL_SIZE = Gauge(
    "reasoner_postgres_pool_size",
    "Current Postgres connection pool size",
)

REASONER_POSTGRES_POOL_FREE = Gauge(
    "reasoner_postgres_pool_free",
    "Free connections in Postgres pool",
)

REASONER_REDIS_POOL_SIZE = Gauge(
    "reasoner_redis_pool_size",
    "Current Redis connection pool size",
)


async def metrics_endpoint() -> Response:
    """Expose Prometheus metrics.

    Critical Enhancement 7.2: generate_latest is synchronous,
    so we run it in a thread to avoid blocking the event loop.
    """
    content = await asyncio.to_thread(generate_latest)
    return Response(content=content, media_type=CONTENT_TYPE_LATEST)


class QueryTimer:
    """Explicit timer for async pipeline execution (Critical Enhancement 7.1).

    Using `.time()` context manager on an async generator only measures
    until the first yield. This class records start time and exposes
    an explicit `observe()` call after the generator completes.
    """

    def __init__(self, preset: str):
        self.preset = preset
        self._start: float | None = None

    def start(self) -> None:
        self._start = time.monotonic()

    def observe(self) -> None:
        if self._start is not None:
            REASONER_QUERY_DURATION.labels(preset=self.preset).observe(
                time.monotonic() - self._start
            )
