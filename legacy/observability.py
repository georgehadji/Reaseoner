
"""
Observability Decorator for Reasoner Pipeline

Provides automatic metric collection, structured logging, and tracing.
"""

from __future__ import annotations

import asyncio
import functools
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, TypeVar, Optional
from contextvars import ContextVar
import logging
import json

logger = logging.getLogger(__name__)

# Trace context propagation
_trace_id_ctx: ContextVar[str] = ContextVar("trace_id", default="")
_span_id_ctx: ContextVar[str] = ContextVar("span_id", default="")


@dataclass
class MetricData:
    """Metric data point."""
    name: str
    value: float
    labels: dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    unit: str = "ms"


@dataclass
class SpanData:
    """Span data for distributed tracing."""
    trace_id: str
    span_id: str
    parent_span_id: str | None
    operation_name: str
    start_time: float
    end_time: float | None = None
    tags: dict[str, str] = field(default_factory=dict)
    logs: list[dict[str, Any]] = field(default_factory=list)
    status: str = "OK"  # OK, ERROR


# Global metric storage (replace with Prometheus/Datadog in production)
_metrics_buffer: list[MetricData] = []
_spans_buffer: list[SpanData] = []


def emit_metric(metric: MetricData) -> None:
    """Emit a metric to the monitoring system."""
    _metrics_buffer.append(metric)
    
    # Log metric for immediate visibility
    logger.info(
        f"metric.{metric.name}",
        extra={
            "metric_name": metric.name,
            "metric_value": metric.value,
            "metric_labels": metric.labels,
            "metric_timestamp": metric.timestamp,
            "metric_unit": metric.unit,
        },
    )
    
    # In production, send to Prometheus/Datadog:
    # prometheus_client.Gauge(metric.name, ...).set(metric.value)
    # datadog.api.Metric.send(metric=metric.name, points=metric.value, tags=...)


def start_span(
    operation_name: str,
    parent_span_id: Optional[str] = None,
    tags: Optional[dict[str, str]] = None,
) -> SpanData:
    """Start a new trace span."""
    import uuid
    
    trace_id = _trace_id_ctx.get() or str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    
    span = SpanData(
        trace_id=trace_id,
        span_id=span_id,
        parent_span_id=parent_span_id or _span_id_ctx.get() or None,
        operation_name=operation_name,
        start_time=time.time(),
        tags=tags or {},
    )
    
    _span_id_ctx.set(span_id)
    _trace_id_ctx.set(trace_id)
    
    return span


def end_span(span: SpanData, status: str = "OK") -> None:
    """End a trace span."""
    span.end_time = time.time()
    span.status = status
    
    _spans_buffer.append(span)
    
    duration_ms = (span.end_time - span.start_time) * 1000
    
    logger.info(
        f"span.{span.operation_name}",
        extra={
            "trace_id": span.trace_id,
            "span_id": span.span_id,
            "parent_span_id": span.parent_span_id,
            "operation": span.operation_name,
            "duration_ms": duration_ms,
            "status": status,
            "tags": span.tags,
        },
    )


def observe(
    metric: str,
    labels: Optional[list[str]] = None,
    histogram_buckets: Optional[list[float]] = None,
    alert_threshold_ms: Optional[float] = None,
    alert_severity: str = "P1",
    log_level: str = "INFO",
) -> Callable:
    """
    Decorator for automatic observability injection.
    
    Args:
        metric: Metric name (e.g., "llm_call_duration")
        labels: List of label names to extract from function args
        histogram_buckets: Histogram bucket boundaries in ms
        alert_threshold_ms: Alert if duration exceeds this threshold
        alert_severity: Alert severity (P0, P1, P2, P3)
        log_level: Logging level for structured logs
    
    Example:
        @observe(
            metric="llm_call_duration",
            labels=["model", "provider"],
            histogram_buckets=[10, 50, 100, 250, 500, 1000],
            alert_threshold_ms=300,
        )
        async def call_llm(model: str, prompt: str) -> str:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await _execute_with_observation(
                func, args, kwargs, metric, labels,
                histogram_buckets, alert_threshold_ms, alert_severity, log_level
            )
        
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return _execute_with_observation(
                func, args, kwargs, metric, labels,
                histogram_buckets, alert_threshold_ms, alert_severity, log_level
            )
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def _execute_with_observation(
    func: Callable,
    args: tuple,
    kwargs: dict,
    metric_name: str,
    labels: Optional[list[str]],
    histogram_buckets: Optional[list[float]],
    alert_threshold_ms: Optional[float],
    alert_severity: str,
    log_level: str,
) -> Any:
    """Execute function with observation."""
    import uuid
    
    # Extract labels from function arguments
    label_values = {}
    if labels:
        sig = __import__("inspect").signature(func)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        for label_name in labels:
            if label_name in bound.arguments:
                label_values[label_name] = str(bound.arguments[label_name])
    
    # Start span
    span = start_span(func.__name__, tags=label_values)
    
    start_time = time.time()
    status = "OK"
    error_msg = None
    
    try:
        result = func(*args, **kwargs)
        return result
    except Exception as e:
        status = "ERROR"
        error_msg = str(e)
        raise
    finally:
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        
        # End span
        end_span(span, status)
        
        # Emit metric
        metric = MetricData(
            name=metric_name,
            value=duration_ms,
            labels={**label_values, "status": status},
            unit="ms",
        )
        emit_metric(metric)
        
        # Check alert threshold
        if alert_threshold_ms and duration_ms > alert_threshold_ms:
            logger.warning(
                f"alert.{alert_severity}: {metric_name} exceeded threshold",
                extra={
                    "alert_severity": alert_severity,
                    "alert_type": "threshold_breach",
                    "metric_name": metric_name,
                    "threshold_ms": alert_threshold_ms,
                    "actual_ms": duration_ms,
                    "labels": label_values,
                },
            )
        
        # Structured log
        log_extra = {
            "function": func.__name__,
            "duration_ms": duration_ms,
            "status": status,
            "labels": label_values,
        }
        
        if error_msg:
            log_extra["error"] = error_msg
            log_extra["traceback"] = traceback.format_exc()
        
        getattr(logger, log_level.lower())(
            f"{func.__name__} completed",
            extra=log_extra,
        )


def get_trace_context() -> dict[str, str]:
    """Get current trace context for propagation."""
    return {
        "trace_id": _trace_id_ctx.get(),
        "span_id": _span_id_ctx.get(),
    }


def inject_trace_context(headers: dict[str, str]) -> None:
    """Inject trace context into outgoing request headers."""
    ctx = get_trace_context()
    headers["X-Trace-ID"] = ctx["trace_id"]
    headers["X-Span-ID"] = ctx["span_id"]


def extract_trace_context(headers: dict[str, str]) -> None:
    """Extract trace context from incoming request headers."""
    if "X-Trace-ID" in headers:
        _trace_id_ctx.set(headers["X-Trace-ID"])
    if "X-Span-ID" in headers:
        _span_id_ctx.set(headers["X-Span-ID"])


def get_metrics_buffer() -> list[MetricData]:
    """Get metrics buffer (for testing/export)."""
    return _metrics_buffer.copy()


def get_spans_buffer() -> list[SpanData]:
    """Get spans buffer (for testing/export)."""
    return _spans_buffer.copy()


def clear_buffers() -> None:
    """Clear metrics and spans buffers."""
    _metrics_buffer.clear()
    _spans_buffer.clear()

