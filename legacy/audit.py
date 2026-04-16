"""
ARA Pipeline - Audit Logging
Comprehensive audit logging for API calls and pipeline operations.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from logging_utils import api_logger
from sanitization import sanitize_for_logging


class AuditEventType(str, Enum):
    # API events
    API_REQUEST_RECEIVED = "api_request_received"
    API_REQUEST_VALIDATED = "api_request_validated"
    API_REQUEST_REJECTED = "api_request_rejected"
    API_RESPONSE_SENT = "api_response_sent"
    API_ERROR = "api_error"

    # Pipeline events
    PIPELINE_STARTED = "pipeline_started"
    PIPELINE_PHASE_STARTED = "pipeline_phase_started"
    PIPELINE_PHASE_COMPLETED = "pipeline_phase_completed"
    PIPELINE_COMPLETED = "pipeline_completed"
    PIPELINE_ERROR = "pipeline_error"

    # Security events
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    INPUT_SANITIZATION_WARNING = "input_sanitization_warning"
    INPUT_BLOCKED = "input_blocked"
    AUTH_FAILURE = "auth_failure"

    # Provider events
    PROVIDER_CALL_STARTED = "provider_call_started"
    PROVIDER_CALL_COMPLETED = "provider_call_completed"
    PROVIDER_CALL_FAILED = "provider_call_failed"
    CIRCUIT_BREAKER_OPENED = "circuit_breaker_opened"


@dataclass
class AuditEvent:
    """Single audit event."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    event_type: str = ""
    correlation_id: str = ""
    user_id: str | None = None
    ip_address: str | None = None
    endpoint: str | None = None
    method: str | None = None
    status_code: int | None = None
    duration_ms: float | None = None
    details: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AuditLogger:
    """
    Audit logger for tracking all API and pipeline operations.
    """

    def __init__(self, audit_file: Path | None = None):
        self.audit_file = audit_file
        self._events: list[AuditEvent] = []
        self._max_events_in_memory = 1000

    def log(
        self,
        event_type: AuditEventType,
        correlation_id: str,
        details: dict[str, Any] | None = None,
        user_id: str | None = None,
        ip_address: str | None = None,
        endpoint: str | None = None,
        method: str | None = None,
        status_code: int | None = None,
        duration_ms: float | None = None,
        error: str | None = None,
    ) -> AuditEvent:
        """Log an audit event."""
        # Sanitize sensitive details
        safe_details = {}
        if details:
            for key, value in details.items():
                if key in ("problem", "prompt", "user_input"):
                    safe_details[key] = sanitize_for_logging(str(value))
                else:
                    safe_details[key] = value

        event = AuditEvent(
            event_type=event_type.value,
            correlation_id=correlation_id,
            user_id=user_id,
            ip_address=ip_address,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            duration_ms=duration_ms,
            details=safe_details,
            error=error,
        )

        # Store in memory
        self._events.append(event)

        # Trim if too many events
        if len(self._events) > self._max_events_in_memory:
            self._events = self._events[-self._max_events_in_memory:]

        # Write to file if configured
        if self.audit_file:
            self._write_to_file(event)

        # Also log to structured logger
        log_level = "warning" if error else "info"
        log_func = api_logger.warning if error else api_logger.info

        log_func(
            f"AUDIT: {event_type.value}",
            extra={
                "event_type": event_type.value,
                "correlation_id": correlation_id,
                "endpoint": endpoint,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "error": error,
            },
        )

        return event

    def _write_to_file(self, event: AuditEvent) -> None:
        """Write event to audit file."""
        try:
            self.audit_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.audit_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event.to_dict()) + "\n")
        except Exception:
            pass  # Don't fail on audit logging errors

    def get_recent_events(
        self,
        event_type: AuditEventType | None = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        """Get recent audit events."""
        events = self._events

        if event_type:
            events = [e for e in events if e.event_type == event_type.value]

        return events[-limit:]

    def get_events_for_correlation(
        self,
        correlation_id: str,
    ) -> list[AuditEvent]:
        """Get all events for a specific correlation ID."""
        return [e for e in self._events if e.correlation_id == correlation_id]


# Context manager for timing operations
class AuditTimer:
    """Context manager for timing operations and logging audit events."""

    def __init__(
        self,
        audit_logger: AuditLogger,
        event_type: AuditEventType,
        correlation_id: str,
        details: dict[str, Any] | None = None,
    ):
        self.audit_logger = audit_logger
        self.event_type = event_type
        self.correlation_id = correlation_id
        self.details = details or {}
        self.start_time = 0.0

    def __enter__(self):
        self.start_time = time.time() * 1000  # Convert to ms
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() * 1000) - self.start_time
        error = str(exc_val) if exc_val else None

        self.audit_logger.log(
            event_type=self.event_type,
            correlation_id=self.correlation_id,
            details=self.details,
            duration_ms=round(duration_ms, 2),
            error=error,
        )


# Global audit logger
_audit_logger: AuditLogger | None = None


def get_audit_logger() -> AuditLogger:
    """Get or create global audit logger."""
    global _audit_logger
    if _audit_logger is None:
        audit_dir = Path(__file__).parent / "audit"
        audit_file = audit_dir / "audit.log"
        _audit_logger = AuditLogger(audit_file=audit_file)
    return _audit_logger


def log_api_request(
    correlation_id: str,
    endpoint: str,
    method: str,
    ip_address: str | None = None,
    details: dict[str, Any] | None = None,
) -> AuditEvent:
    """Log incoming API request."""
    return get_audit_logger().log(
        event_type=AuditEventType.API_REQUEST_RECEIVED,
        correlation_id=correlation_id,
        endpoint=endpoint,
        method=method,
        ip_address=ip_address,
        details=details,
    )


def log_api_response(
    correlation_id: str,
    endpoint: str,
    status_code: int,
    duration_ms: float,
) -> AuditEvent:
    """Log API response."""
    return get_audit_logger().log(
        event_type=AuditEventType.API_RESPONSE_SENT,
        correlation_id=correlation_id,
        endpoint=endpoint,
        status_code=status_code,
        duration_ms=duration_ms,
    )


def log_pipeline_event(
    correlation_id: str,
    event_type: AuditEventType,
    phase: str | None = None,
    details: dict[str, Any] | None = None,
    duration_ms: float | None = None,
    error: str | None = None,
) -> AuditEvent:
    """Log pipeline event."""
    event_details = details or {}
    if phase:
        event_details["phase"] = phase

    return get_audit_logger().log(
        event_type=event_type,
        correlation_id=correlation_id,
        details=event_details,
        duration_ms=duration_ms,
        error=error,
    )