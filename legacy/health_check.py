"""
Reasoner Pipeline - Health Checks
Provider health monitoring and status reporting.
"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from logging_utils import llm_logger
from llm import _REGISTRY, build_provider


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ProviderHealth:
    """Health status for a single provider."""
    name: str
    status: HealthStatus
    latency_ms: float | None = None
    last_check: float | None = None
    error: str | None = None
    consecutive_failures: int = 0


@dataclass
class HealthCheckResult:
    """Result of health check operation."""
    overall_status: HealthStatus
    providers: dict[str, ProviderHealth]
    timestamp: float = field(default_factory=time.time)
    total_latency_ms: float = 0.0


# Simple test prompt for health checks
_HEALTH_CHECK_PROMPT = "Respond with exactly: OK"


class ProviderHealthChecker:
    """
    Health checker for LLM providers.
    """

    def __init__(self, timeout_seconds: float = 10.0):
        self.timeout_seconds = timeout_seconds
        self._health_cache: dict[str, ProviderHealth] = {}
        self._cache_ttl: float = 60.0  # Cache health for 60 seconds
        self._last_full_check: float = 0.0

    async def check_provider(self, model_id: str) -> ProviderHealth:
        """
        Check health of a single provider.
        """
        # Check if we have a recent result
        cached = self._health_cache.get(model_id)
        if cached and (time.time() - (cached.last_check or 0)) < self._cache_ttl:
            return cached

        health = ProviderHealth(
            name=model_id,
            status=HealthStatus.UNKNOWN,
        )

        # Get registry entry
        entry = _REGISTRY.get(model_id)
        if not entry:
            health.status = HealthStatus.UNHEALTHY
            health.error = "Model not in registry"
            return health

        # Check if API key is available
        env_key = entry.get("env")
        if env_key and not os.environ.get(env_key):
            health.status = HealthStatus.UNHEALTHY
            health.error = f"Missing API key: {env_key}"
            return health

        # Try to create provider and make a test call
        try:
            provider = build_provider(model_id)

            start_time = time.time()
            try:
                result = await asyncio.wait_for(
                    provider.complete(
                        system_prompt="You are a helpful assistant.",
                        user_prompt=_HEALTH_CHECK_PROMPT,
                        max_tokens=10,
                        temperature=0.0,
                    ),
                    timeout=self.timeout_seconds,
                )
                latency = (time.time() - start_time) * 1000

                health.latency_ms = latency
                health.last_check = time.time()

                if "OK" in result:
                    health.status = HealthStatus.HEALTHY
                    health.consecutive_failures = 0
                else:
                    health.status = HealthStatus.DEGRADED
                    health.error = "Unexpected response"

            except asyncio.TimeoutError:
                health.status = HealthStatus.UNHEALTHY
                health.error = "Timeout"
                health.consecutive_failures += 1

        except Exception as e:
            health.status = HealthStatus.UNHEALTHY
            health.error = str(e)
            health.consecutive_failures += 1

        # Update cache
        self._health_cache[model_id] = health

        return health

    async def check_all_providers(
        self,
        model_ids: list[str] | None = None,
    ) -> HealthCheckResult:
        """
        Check health of all configured providers.
        """
        if model_ids is None:
            # Get all models with API keys available
            model_ids = []
            for model_id, entry in _REGISTRY.items():
                env_key = entry.get("env")
                if env_key and os.environ.get(env_key):
                    model_ids.append(model_id)

        # Run checks in parallel
        tasks = [self.check_provider(mid) for mid in model_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        providers = {}
        total_latency = 0.0
        unhealthy_count = 0
        degraded_count = 0

        for i, result in enumerate(results):
            model_id = model_ids[i]

            if isinstance(result, Exception):
                providers[model_id] = ProviderHealth(
                    name=model_id,
                    status=HealthStatus.UNHEALTHY,
                    error=str(result),
                )
                unhealthy_count += 1
            else:
                providers[model_id] = result
                if result.latency_ms:
                    total_latency += result.latency_ms
                if result.status == HealthStatus.UNHEALTHY:
                    unhealthy_count += 1
                elif result.status == HealthStatus.DEGRADED:
                    degraded_count += 1

        # Determine overall status
        if unhealthy_count > 0:
            overall = HealthStatus.UNHEALTHY
        elif degraded_count > 0:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY

        self._last_full_check = time.time()

        return HealthCheckResult(
            overall_status=overall,
            providers=providers,
            total_latency_ms=total_latency,
        )

    def get_cached_status(self) -> dict[str, Any]:
        """Get cached provider statuses."""
        return {
            model_id: {
                "status": health.status.value,
                "latency_ms": health.latency_ms,
                "last_check": health.last_check,
                "error": health.error,
            }
            for model_id, health in self._health_cache.items()
        }


# Global health checker
_health_checker: ProviderHealthChecker | None = None


def get_health_checker() -> ProviderHealthChecker:
    """Get or create global health checker."""
    global _health_checker
    if _health_checker is None:
        _health_checker = ProviderHealthChecker()
    return _health_checker


async def check_provider_health(model_id: str) -> ProviderHealth:
    """Quick helper to check a single provider."""
    return await get_health_checker().check_provider(model_id)


async def get_system_health() -> HealthCheckResult:
    """Get health status of all providers."""
    return await get_health_checker().check_all_providers()