# Author: Georgios-Chrysovalantis Chatzivantsidis
"""
Reasoner Pipeline - Retry Utilities
Provides automatic retry with exponential backoff for transient failures.
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, TypeVar

from circuit_breaker import get_circuit_breaker, CircuitOpenError
from exceptions import RateLimitError, ProviderUnavailableError, ProviderTimeoutError
from logging_utils import llm_logger

T = TypeVar("T")


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 10.0     # seconds
    backoff_factor: float = 2.0
    jitter_fraction: float = 0.5


# Exceptions that should trigger a retry
RETRYABLE_EXCEPTIONS = (
    RateLimitError,
    ProviderUnavailableError,
    ProviderTimeoutError,
    asyncio.TimeoutError,
)


async def retry_with_backoff(
    func: Callable[..., Awaitable[T]],
    *args: Any,
    config: RetryConfig | None = None,
    circuit_breaker_name: str | None = None,
    **kwargs: Any,
) -> T:
    """
    Retry an async function with exponential backoff and jitter.
    
    Args:
        func: The async function to call
        config: Retry configuration
        circuit_breaker_name: Optional name of circuit breaker to use
        
    Returns:
        The result of the function call
        
    Raises:
        The last exception if all retries fail
    """
    cfg = config or RetryConfig()
    last_exception: Exception | None = None
    delay = cfg.initial_delay
    
    circuit_breaker = None
    if circuit_breaker_name:
        circuit_breaker = get_circuit_breaker(circuit_breaker_name)

    for attempt in range(cfg.max_retries + 1):
        try:
            # Execute the function (with circuit breaker protection if available)
            if circuit_breaker:
                result = await circuit_breaker.call(func, *args, **kwargs)
            elif asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)


            if attempt > 0:
                llm_logger.info(
                    f"Retry succeeded on attempt {attempt + 1}",
                    extra={
                        "attempt": attempt + 1,
                        "function": func.__name__,
                    },
                )
            return result
        except RETRYABLE_EXCEPTIONS as e:
            last_exception = e
            if attempt == cfg.max_retries:
                llm_logger.error(
                    f"Max retries reached for {func.__name__}",
                    extra={
                        "attempts": cfg.max_retries,
                        "function": func.__name__,
                        "error": str(e),
                    },
                )
                break  # Exit loop to re-raise

            jitter = random.uniform(
                -cfg.jitter_fraction * delay,
                cfg.jitter_fraction * delay,
            )
            sleep_time = min(delay + jitter, cfg.max_delay)

            llm_logger.warning(
                f"Retryable error in {func.__name__}, retrying in {sleep_time:.2f}s",
                extra={
                    "attempt": attempt + 1,
                    "function": func.__name__,
                    "error": str(e),
                    "delay_seconds": round(sleep_time, 2),
                },
            )

            await asyncio.sleep(sleep_time)
            delay *= cfg.backoff_factor
        
        except CircuitOpenError as e:
            # Circuit breaker is open - don't retry, propagate immediately
            llm_logger.error(
                f"Circuit breaker '{e.circuit_name}' is open. Failing fast.",
                extra={
                    "circuit_name": e.circuit_name,
                    "function": func.__name__,
                },
            )
            raise

    # This should only be reached if all retries fail
    # We check last_exception to satisfy type checker, though it should always be set
    # if the loop completes due to retries
    # It might not be set if max_retries = 0 and the first call fails with a non-retryable
    # error, but in that case the original error would have been raised.
    # So, we check and raise here just in case
    if last_exception:
        raise last_exception

    raise RuntimeError("Retry logic error: no exception but no result")


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass
