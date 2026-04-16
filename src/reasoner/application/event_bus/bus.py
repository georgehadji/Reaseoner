"""
Application Layer - Event Bus

The event bus distributes domain events to subscribers.
This enables:
- Decoupled communication between components
- Async processing
- Multiple side effects from single events
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Awaitable
from collections import defaultdict

from reasoner.core.events.domain_events import DomainEvent, EventType

logger = logging.getLogger(__name__)


# Type alias for event handlers
EventHandler = Callable[[DomainEvent], Awaitable[None]]


class EventBus:
    """
    In-memory event bus for domain events.
    
    Supports:
    - Synchronous and async handlers
    - Event type filtering
    - Wildcard subscriptions
    - Error isolation (one handler failure doesn't affect others)
    """
    
    def __init__(self):
        self._handlers: dict[EventType, list[EventHandler]] = defaultdict(list)
        self._global_handlers: list[EventHandler] = []
        self._error_handlers: list[Callable[[DomainEvent, Exception], Awaitable[None]]] = []
        self._running = False
        self._task_queue: asyncio.Queue[tuple[DomainEvent, EventHandler]] | None = None
    
    def subscribe(
        self,
        event_type: EventType,
        handler: EventHandler,
    ) -> None:
        """
        Subscribe to a specific event type.
        
        Args:
            event_type: Type of event to subscribe to
            handler: Async function to call when event occurs
        """
        self._handlers[event_type].append(handler)
        logger.debug(f"Subscribed handler to {event_type.value}")
    
    def subscribe_all(
        self,
        handler: EventHandler,
    ) -> None:
        """
        Subscribe to all events.
        
        Args:
            handler: Async function to call for every event
        """
        self._global_handlers.append(handler)
        logger.debug("Subscribed global handler")
    
    def on_error(
        self,
        handler: Callable[[DomainEvent, Exception], Awaitable[None]],
    ) -> None:
        """
        Register error handler for handler failures.
        
        Args:
            handler: Async function called when a handler fails
        """
        self._error_handlers.append(handler)
    
    async def publish(self, event: DomainEvent) -> None:
        """
        Publish an event to all subscribers.
        
        Handlers are called concurrently. Errors in one handler
        don't affect others.
        
        Args:
            event: Domain event to publish
        """
        handlers = (
            self._handlers.get(event.event_type, []) + 
            self._global_handlers
        )
        
        if not handlers:
            logger.debug(f"No handlers for {event.event_type.value}")
            return
        
        # Execute all handlers concurrently
        tasks = [
            self._safe_execute(handler, event)
            for handler in handlers
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _safe_execute(
        self,
        handler: EventHandler,
        event: DomainEvent,
    ) -> None:
        """Execute handler with error isolation."""
        try:
            await handler(event)
        except Exception as exc:
            logger.error(
                f"Handler error for {event.event_type.value}: {exc}",
                exc_info=True,
            )
            
            # Notify error handlers
            for error_handler in self._error_handlers:
                try:
                    await error_handler(event, exc)
                except Exception as inner_exc:
                    logger.error(f"Error handler failed: {inner_exc}")
    
    def clear(self) -> None:
        """Clear all subscriptions."""
        self._handlers.clear()
        self._global_handlers.clear()
        self._error_handlers.clear()
    
    def get_subscriber_count(self, event_type: EventType) -> int:
        """Get number of subscribers for an event type."""
        return len(self._handlers.get(event_type, []))
    
    @property
    def total_subscribers(self) -> int:
        """Get total number of subscribers."""
        return (
            sum(len(handlers) for handlers in self._handlers.values()) +
            len(self._global_handlers)
        )


# ─────────────────────────────────────────────────────────────────────
# GLOBAL EVENT BUS INSTANCE
# ─────────────────────────────────────────────────────────────────────

_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get or create the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def reset_event_bus() -> None:
    """Reset the global event bus (for testing)."""
    global _event_bus
    _event_bus = None


# ─────────────────────────────────────────────────────────────────────
# EVENT HANDLER DECORATORS
# ─────────────────────────────────────────────────────────────────────

def handle_event(event_type: EventType) -> Callable[[EventHandler], EventHandler]:
    """
    Decorator to register an event handler.
    
    Usage:
        @handle_event(EventType.PHASE_COMPLETED)
        async def on_phase_completed(event: DomainEvent):
            ...
    """
    def decorator(handler: EventHandler) -> EventHandler:
        bus = get_event_bus()
        bus.subscribe(event_type, handler)
        return handler
    
    return decorator


def handle_all_events() -> Callable[[EventHandler], EventHandler]:
    """
    Decorator to subscribe to all events.
    
    Usage:
        @handle_all_events()
        async def on_any_event(event: DomainEvent):
            ...
    """
    def decorator(handler: EventHandler) -> EventHandler:
        bus = get_event_bus()
        bus.subscribe_all(handler)
        return handler
    
    return decorator


# ─────────────────────────────────────────────────────────────────────
# EXAMPLE SUBSCRIBERS
# ─────────────────────────────────────────────────────────────────────

async def log_all_events(event: DomainEvent) -> None:
    """Log all events for debugging."""
    logger.debug(
        f"Event: {event.event_type.value} "
        f"(aggregate: {event.aggregate_id}, version: {event.version})"
    )


async def track_pipeline_metrics(event: DomainEvent) -> None:
    """Track metrics for pipeline events."""
    from reasoner.core.events.domain_events import (
        PipelineCompleted,
        PipelineFailed,
        PhaseCompleted,
    )
    
    if isinstance(event, PipelineCompleted):
        logger.info(
            f"Pipeline completed: {event.total_duration_seconds:.2f}s, "
            f"{event.total_tokens.get('total', 0)} tokens"
        )
    elif isinstance(event, PipelineFailed):
        logger.warning(f"Pipeline failed: {event.error}")
    elif isinstance(event, PhaseCompleted):
        logger.debug(
            f"Phase {event.phase_name} completed: "
            f"{event.duration_seconds:.2f}s"
        )


# Auto-register example subscribers
get_event_bus().subscribe_all(log_all_events)
get_event_bus().subscribe_all(track_pipeline_metrics)
