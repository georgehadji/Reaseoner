"""
Reasoner - Domain Events for Event Sourcing

All events are immutable (frozen dataclasses) and represent
something that happened in the domain.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from datetime import datetime
from enum import Enum


class EventType(str, Enum):
    """Types of domain events."""
    # Pipeline Events
    PIPELINE_STARTED = "pipeline_started"
    PHASE_STARTED = "phase_started"
    PHASE_COMPLETED = "phase_completed"
    PHASE_FAILED = "phase_failed"
    PIPELINE_COMPLETED = "pipeline_completed"
    PIPELINE_FAILED = "pipeline_failed"
    
    # Context Events
    CONTEXT_FETCHED = "context_fetched"
    CONTEXT_VETTED = "context_vetted"
    SOURCE_ADDED = "source_added"
    
    # Method-Specific Events
    PERSPECTIVE_GENERATED = "perspective_generated"
    CANDIDATE_SCORED = "candidate_scored"
    STRESS_TEST_COMPLETED = "stress_test_completed"
    
    # Widget Events
    WIDGET_DETECTED = "widget_detected"
    WIDGET_EXECUTED = "widget_executed"
    WIDGET_FAILED = "widget_failed"
    
    # Memory Events
    MEMORY_STORED = "memory_stored"
    MEMORY_RECALLED = "memory_recalled"
    
    # Error Events
    ERROR_OCCURRED = "error_occurred"
    RETRY_ATTEMPTED = "retry_attempted"


@dataclass(frozen=True)
class DomainEvent:
    """
    Base class for all domain events.
    
    All events are immutable and contain:
    - event_id: Unique identifier
    - event_type: Type of event
    - timestamp: When it happened
    - aggregate_id: ID of the aggregate this event belongs to
    - version: Event version for optimistic concurrency
    """
    event_id: str
    event_type: EventType
    timestamp: float
    aggregate_id: str
    version: int
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize event to dictionary for storage."""
        from dataclasses import asdict
        return {
            **asdict(self),
            'event_type': self.event_type.value,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DomainEvent:
        """Deserialize event from dictionary."""
        return cls(**data)


# ─────────────────────────────────────────────────────────────────────
# PIPELINE EVENTS
# ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PipelineStarted(DomainEvent):
    """Pipeline execution started."""
    problem: str = ""
    preset: str = ""
    method: str = ""
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PhaseStarted(DomainEvent):
    """Phase execution started."""
    phase_name: str = ""
    config: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PhaseCompleted(DomainEvent):
    """Phase execution completed successfully."""
    phase_name: str = ""
    result: Any = None
    tokens: dict[str, int] = field(default_factory=dict)
    model_used: str = ""
    duration_seconds: float = 0.0


@dataclass(frozen=True)
class PhaseFailed(DomainEvent):
    """Phase execution failed."""
    phase_name: str = ""
    error: str = ""
    retry_count: int = 0


@dataclass(frozen=True)
class PipelineCompleted(DomainEvent):
    """Pipeline execution completed successfully."""
    solution: dict[str, Any] = field(default_factory=dict)
    total_tokens: dict[str, int] = field(default_factory=dict)
    total_duration_seconds: float = 0.0
    phases_completed: int = 0


@dataclass(frozen=True)
class PipelineFailed(DomainEvent):
    """Pipeline execution failed."""
    error: str = ""
    phase_at_failure: str = ""
    phases_completed: int = 0


# ─────────────────────────────────────────────────────────────────────
# CONTEXT EVENTS
# ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ContextFetched(DomainEvent):
    """Context fetched from external source."""
    source_type: str = ""
    query: str = ""
    result_count: int = 0


@dataclass(frozen=True)
class ContextVetted(DomainEvent):
    """Context vetting completed."""
    sources_vetted: int = 0
    flags: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class SourceAdded(DomainEvent):
    """New source added to context."""
    url: str = ""
    title: str = ""
    source_type: str = ""
    relevance_score: float = 0.0


# ─────────────────────────────────────────────────────────────────────
# METHOD-SPECIFIC EVENTS
# ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PerspectiveGenerated(DomainEvent):
    """Perspective solution generated."""
    perspective_type: str = ""
    model_used: str = ""
    confidence: float = 0.0


@dataclass(frozen=True)
class CandidateScored(DomainEvent):
    """Candidate solution scored."""
    candidate_id: str = ""
    scores: dict[str, float] = field(default_factory=dict)
    total_score: float = 0.0
    flags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class StressTestCompleted(DomainEvent):
    """Stress test completed for a candidate."""
    candidate_id: str = ""
    scenario: str = ""
    survival_rate: float = 0.0
    failure_mode: str = ""


# ─────────────────────────────────────────────────────────────────────
# WIDGET EVENTS
# ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class WidgetDetected(DomainEvent):
    """Widget auto-detected from query."""
    widget_type: str = ""
    trigger_pattern: str = ""
    confidence: float = 0.0


@dataclass(frozen=True)
class WidgetExecuted(DomainEvent):
    """Widget executed successfully."""
    widget_type: str = ""
    result: dict[str, Any] = field(default_factory=dict)
    duration_seconds: float = 0.0


@dataclass(frozen=True)
class WidgetFailed(DomainEvent):
    """Widget execution failed."""
    widget_type: str = ""
    error: str = ""


# ─────────────────────────────────────────────────────────────────────
# MEMORY EVENTS
# ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class MemoryStored(DomainEvent):
    """Memory stored in Neuro system."""
    session_id: str = ""
    entry_id: int = 0
    compressed: bool = False


@dataclass(frozen=True)
class MemoryRecalled(DomainEvent):
    """Memory recalled from Neuro system."""
    query: str = ""
    chunks_found: int = 0
    latency_ms: float = 0.0


# ─────────────────────────────────────────────────────────────────────
# ERROR EVENTS
# ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ErrorOccurred(DomainEvent):
    """Error occurred during execution."""
    error_type: str = ""
    error_message: str = ""
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetryAttempted(DomainEvent):
    """Retry attempt for failed operation."""
    operation: str = ""
    attempt: int = 0
    max_retries: int = 0
    delay_seconds: float = 0.0


# ─────────────────────────────────────────────────────────────────────
# EVENT FACTORY
# ─────────────────────────────────────────────────────────────────────

import uuid
import time


def make_event(
    event_type: EventType,
    aggregate_id: str,
    version: int,
    **kwargs: Any
) -> DomainEvent:
    """
    Factory function to create domain events.
    
    Automatically sets:
    - event_id: UUID
    - timestamp: Current time
    """
    event_class = EVENT_CLASSES.get(event_type, DomainEvent)
    
    return event_class(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        timestamp=time.time(),
        aggregate_id=aggregate_id,
        version=version,
        **kwargs
    )


# Map event types to classes
EVENT_CLASSES: dict[EventType, type[DomainEvent]] = {
    EventType.PIPELINE_STARTED: PipelineStarted,
    EventType.PHASE_STARTED: PhaseStarted,
    EventType.PHASE_COMPLETED: PhaseCompleted,
    EventType.PHASE_FAILED: PhaseFailed,
    EventType.PIPELINE_COMPLETED: PipelineCompleted,
    EventType.PIPELINE_FAILED: PipelineFailed,
    EventType.CONTEXT_FETCHED: ContextFetched,
    EventType.CONTEXT_VETTED: ContextVetted,
    EventType.SOURCE_ADDED: SourceAdded,
    EventType.PERSPECTIVE_GENERATED: PerspectiveGenerated,
    EventType.CANDIDATE_SCORED: CandidateScored,
    EventType.STRESS_TEST_COMPLETED: StressTestCompleted,
    EventType.WIDGET_DETECTED: WidgetDetected,
    EventType.WIDGET_EXECUTED: WidgetExecuted,
    EventType.WIDGET_FAILED: WidgetFailed,
    EventType.MEMORY_STORED: MemoryStored,
    EventType.MEMORY_RECALLED: MemoryRecalled,
    EventType.ERROR_OCCURRED: ErrorOccurred,
    EventType.RETRY_ATTEMPTED: RetryAttempted,
}
