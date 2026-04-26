"""Safe JSON loading with depth limits to prevent stack exhaustion."""

from __future__ import annotations

import json
from typing import Any


class JSONDepthExceededError(ValueError):
    """Raised when JSON nesting exceeds the configured maximum depth."""


def _check_depth(obj: Any, current_depth: int, max_depth: int) -> None:
    """Recursively check nesting depth of parsed JSON object."""
    if current_depth > max_depth:
        raise JSONDepthExceededError(f"JSON depth {current_depth} exceeds maximum {max_depth}")
    if isinstance(obj, dict):
        for v in obj.values():
            _check_depth(v, current_depth + 1, max_depth)
    elif isinstance(obj, list):
        for item in obj:
            _check_depth(item, current_depth + 1, max_depth)


def safe_json_loads(data: str | bytes, max_depth: int = 100) -> Any:
    """Parse JSON with a strict depth limit.

    Args:
        data: JSON string or bytes.
        max_depth: Maximum allowed nesting depth (default 100).

    Raises:
        JSONDepthExceededError: If parsed structure exceeds *max_depth*.
        json.JSONDecodeError: If *data* is not valid JSON.
    """
    parsed = json.loads(data)
    _check_depth(parsed, 1, max_depth)
    return parsed
