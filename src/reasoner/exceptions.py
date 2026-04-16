"""
ARA Pipeline - Exception Taxonomy
Structured exception hierarchy for better error handling.

This module provides a comprehensive exception hierarchy for the ARA Pipeline,
enabling precise error handling and appropriate retry strategies.

Exception Hierarchy:
    ARAError (base)
    ├── ParseError
    │   ├── JSONExtractionError
    │   └── JSONValidationError
    ├── ProviderError
    │   ├── AuthenticationError
    │   ├── RateLimitError
    │   ├── ModelNotFoundError
    │   ├── ProviderTimeoutError
    │   └── ProviderUnavailableError
    └── PipelineError
        ├── PhaseError
        └── ConfigurationError

Usage:
    try:
        result = await provider.complete(...)
    except AuthenticationError:
        # Don't retry - API key is invalid
        log_error("Invalid API key")
    except RateLimitError as e:
        # Retry after specified delay
        await asyncio.sleep(e.retry_after)
    except ProviderError as e:
        # Retry with exponential backoff
        if is_retryable(e):
            await retry_with_backoff()
"""

from __future__ import annotations


class ARAError(Exception):
    """
    Base exception for all ARA pipeline errors.
    
    Attributes:
        message (str): Human-readable error message
        details (dict): Additional error context
        retryable (bool): Whether the error is retryable
    """
    retryable: bool = False
    
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.details = details or {}


# ─────────────────────────────────────────────────────────────────────
# PARSE ERRORS
# ─────────────────────────────────────────────────────────────────────

class ParseError(ARAError):
    """Raised when LLM response cannot be parsed into expected structure."""
    retryable = False


class JSONExtractionError(ParseError):
    """Failed to extract JSON from LLM response."""
    pass


class JSONValidationError(ParseError):
    """JSON extracted but doesn't match expected schema."""
    pass


# ─────────────────────────────────────────────────────────────────────
# PROVIDER ERRORS
# ─────────────────────────────────────────────────────────────────────

class ProviderError(ARAError):
    """Base exception for LLM provider errors."""
    pass


class AuthenticationError(ProviderError):
    """
    Invalid or missing API key.
    
    This error is NOT retryable - retrying will not help.
    The user must update their API key configuration.
    """
    retryable = False
    
    def __init__(self, message: str, provider: str | None = None):
        super().__init__(message, {"provider": provider})


class RateLimitError(ProviderError):
    """
    Rate limit exceeded.
    
    This error IS retryable after the specified delay.
    
    Attributes:
        retry_after (int | None): Seconds to wait before retrying
    """
    retryable = True
    
    def __init__(self, message: str, provider: str | None = None, retry_after: int | None = None):
        super().__init__(message, {"provider": provider, "retry_after": retry_after})


class ModelNotFoundError(ProviderError):
    """
    Requested model doesn't exist.
    
    This error is NOT retryable - the model ID is invalid.
    """
    retryable = False
    
    def __init__(self, message: str, model: str | None = None):
        super().__init__(message, {"model": model})


class ProviderTimeoutError(ProviderError):
    """
    Provider request timed out.
    
    This error IS retryable - the provider may be temporarily unavailable.
    """
    retryable = True


class ProviderUnavailableError(ProviderError):
    """
    Provider service is unavailable.
    
    This error IS retryable - may be a temporary outage.
    """
    retryable = True


# ─────────────────────────────────────────────────────────────────────
# PIPELINE ERRORS
# ─────────────────────────────────────────────────────────────────────

class PipelineError(ARAError):
    """Base exception for pipeline execution errors."""
    pass


class PhaseError(PipelineError):
    """
    Error during a specific pipeline phase.
    
    Attributes:
        phase (int): Phase number where error occurred
        phase_name (str): Human-readable phase name
    """
    def __init__(self, message: str, phase: int, phase_name: str):
        super().__init__(message, {"phase": phase, "phase_name": phase_name})
        self.phase = phase
        self.phase_name = phase_name


class ConfigurationError(ARAError):
    """
    Invalid pipeline configuration.
    
    This error is NOT retryable - configuration must be fixed.
    """
    retryable = False


# ─────────────────────────────────────────────────────────────────────
# UTILITY FUNCTIONS
# ─────────────────────────────────────────────────────────────────────

def is_retryable(error: Exception) -> bool:
    """
    Check if an error is retryable.
    
    Args:
        error: Exception to check
        
    Returns:
        bool: True if the error should be retried
        
    Examples:
        >>> is_retryable(AuthenticationError("Invalid key"))
        False
        >>> is_retryable(RateLimitError("Rate limit"))
        True
        >>> is_retryable(ValueError("Unknown error"))
        False
    """
    if isinstance(error, ARAError):
        return error.retryable
    # Unknown errors are not retryable by default
    return False


def classify_error(error: Exception) -> str:
    """
    Classify error type for logging/monitoring.
    
    Args:
        error: Exception to classify
        
    Returns:
        str: Error category for monitoring
        
    Categories:
        - auth: Authentication/authorization errors
        - rate_limit: Rate limiting errors
        - model_not_found: Invalid model ID
        - timeout: Request timeouts
        - unavailable: Service unavailable
        - parse: JSON parsing errors
        - pipeline: Pipeline execution errors
        - unknown: Unclassified errors
    """
    if isinstance(error, AuthenticationError):
        return "auth"
    elif isinstance(error, RateLimitError):
        return "rate_limit"
    elif isinstance(error, ModelNotFoundError):
        return "model_not_found"
    elif isinstance(error, ProviderTimeoutError):
        return "timeout"
    elif isinstance(error, ProviderUnavailableError):
        return "unavailable"
    elif isinstance(error, ParseError):
        return "parse"
    elif isinstance(error, PipelineError):
        return "pipeline"
    else:
        return "unknown"
