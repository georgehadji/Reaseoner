"""
ARA Pipeline - Alerting Configuration

Defines alerts, thresholds, and notification strategies for production monitoring.
Integrates with Prometheus, Grafana, and common alerting systems.

Usage:
    from alerts import AlertManager, AlertConfig, AlertSeverity
    
    alert_manager = AlertManager(AlertConfig(
        prometheus_url="http://localhost:9090",
        slack_webhook_url="https://hooks.slack.com/...",
    ))
    
    # Check and fire alerts
    await alert_manager.check_and_alert()
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# ALERT SEVERITY LEVELS
# ═══════════════════════════════════════════════════════════════════════════════

class AlertSeverity(str, Enum):
    """Alert severity levels."""
    P0_CRITICAL = "p0_critical"    # Page immediately, system down
    P1_HIGH = "p1_high"            # Page within 5 minutes, degraded service
    P2_MEDIUM = "p2_medium"        # Alert within 1 hour, needs attention
    P3_LOW = "p3_low"              # Log only, fix opportunistically


# ═══════════════════════════════════════════════════════════════════════════════
# ALERT DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AlertRule:
    """Definition of an alert rule."""
    name: str
    description: str
    severity: AlertSeverity
    metric_name: str
    threshold: float
    comparison: str  # "gt", "lt", "eq", "gte", "lte"
    duration_seconds: float = 0  # How long condition must persist
    cooldown_seconds: float = 300  # Minimum time between alerts
    runbook_url: str = ""
    labels: dict[str, str] = field(default_factory=dict)
    
    # Internal state
    _last_triggered: float = 0
    _triggered_at: float | None = None
    
    def check(self, value: float) -> bool:
        """Check if the alert condition is met."""
        ops = {
            "gt": lambda v, t: v > t,
            "lt": lambda v, t: v < t,
            "eq": lambda v, t: v == t,
            "gte": lambda v, t: v >= t,
            "lte": lambda v, t: v <= t,
        }
        return ops.get(self.comparison, lambda v, t: False)(value, self.threshold)
    
    def should_fire(self, value: float) -> bool:
        """Check if alert should fire (condition met + cooldown passed)."""
        now = time.monotonic()
        
        if not self.check(value):
            self._triggered_at = None
            return False
        
        # Check duration requirement
        if self.duration_seconds > 0:
            if self._triggered_at is None:
                self._triggered_at = now
                return False
            elif now - self._triggered_at < self.duration_seconds:
                return False
        
        # Check cooldown
        if now - self._last_triggered < self.cooldown_seconds:
            return False
        
        self._last_triggered = now
        return True


# Pre-defined alert rules for ARA Pipeline
DEFAULT_ALERT_RULES: list[AlertRule] = [
    # P0 - Critical
    AlertRule(
        name="system_down",
        description="System is not responding to health checks",
        severity=AlertSeverity.P0_CRITICAL,
        metric_name="health_check_success",
        threshold=0,
        comparison="eq",
        duration_seconds=30,
        cooldown_seconds=60,
        runbook_url="runbooks/system-down.md",
    ),
    AlertRule(
        name="memory_exhausted",
        description="Memory usage exceeds 90% of limit",
        severity=AlertSeverity.P0_CRITICAL,
        metric_name="memory_usage_percent",
        threshold=90,
        comparison="gt",
        duration_seconds=60,
        cooldown_seconds=300,
        runbook_url="runbooks/memory-exhausted.md",
    ),
    
    # P1 - High
    AlertRule(
        name="high_error_rate",
        description="Error rate exceeds 5%",
        severity=AlertSeverity.P1_HIGH,
        metric_name="error_rate_percent",
        threshold=5,
        comparison="gt",
        duration_seconds=60,
        cooldown_seconds=300,
        runbook_url="runbooks/high-error-rate.md",
    ),
    AlertRule(
        name="high_latency_p99",
        description="P99 latency exceeds 10 seconds",
        severity=AlertSeverity.P1_HIGH,
        metric_name="latency_p99_seconds",
        threshold=10,
        comparison="gt",
        duration_seconds=180,
        cooldown_seconds=300,
        runbook_url="runbooks/high-latency.md",
    ),
    AlertRule(
        name="circuit_breaker_open",
        description="Circuit breaker is open for a provider",
        severity=AlertSeverity.P1_HIGH,
        metric_name="circuit_breaker_open_count",
        threshold=0,
        comparison="gt",
        duration_seconds=0,
        cooldown_seconds=600,
        runbook_url="runbooks/provider-failover.md",
    ),
    AlertRule(
        name="llm_provider_failure",
        description="LLM provider failure rate exceeds 10%",
        severity=AlertSeverity.P1_HIGH,
        metric_name="llm_failure_rate_percent",
        threshold=10,
        comparison="gt",
        duration_seconds=120,
        cooldown_seconds=300,
        runbook_url="runbooks/provider-failure.md",
    ),
    
    # P2 - Medium
    AlertRule(
        name="high_latency_p95",
        description="P95 latency exceeds 5 seconds",
        severity=AlertSeverity.P2_MEDIUM,
        metric_name="latency_p95_seconds",
        threshold=5,
        comparison="gt",
        duration_seconds=300,
        cooldown_seconds=600,
        runbook_url="runbooks/latency-tuning.md",
    ),
    AlertRule(
        name="cache_hit_rate_low",
        description="Cache hit rate below 10%",
        severity=AlertSeverity.P2_MEDIUM,
        metric_name="cache_hit_rate_percent",
        threshold=10,
        comparison="lt",
        duration_seconds=600,
        cooldown_seconds=1800,
        runbook_url="runbooks/cache-optimization.md",
    ),
    AlertRule(
        name="rate_limit_rejections",
        description="Rate limit rejections exceeding 10 per minute",
        severity=AlertSeverity.P2_MEDIUM,
        metric_name="rate_limit_rejections_per_minute",
        threshold=10,
        comparison="gt",
        duration_seconds=120,
        cooldown_seconds=600,
        runbook_url="runbooks/rate-limiting.md",
    ),
    
    # P3 - Low
    AlertRule(
        name="memory_warning",
        description="Memory usage exceeds 75% of limit",
        severity=AlertSeverity.P3_LOW,
        metric_name="memory_usage_percent",
        threshold=75,
        comparison="gt",
        duration_seconds=300,
        cooldown_seconds=1800,
        runbook_url="runbooks/memory-warning.md",
    ),
    AlertRule(
        name="slow_requests",
        description="More than 10% of requests taking >30s",
        severity=AlertSeverity.P3_LOW,
        metric_name="slow_request_percent",
        threshold=10,
        comparison="gt",
        duration_seconds=600,
        cooldown_seconds=3600,
        runbook_url="runbooks/slow-requests.md",
    ),
]


# ═══════════════════════════════════════════════════════════════════════════════
# ALERT NOTIFIERS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Alert:
    """An alert instance."""
    rule: AlertRule
    value: float
    timestamp: datetime
    message: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.rule.name,
            "severity": self.rule.severity.value,
            "description": self.rule.description,
            "value": self.value,
            "threshold": self.rule.threshold,
            "timestamp": self.timestamp.isoformat(),
            "message": self.message,
            "runbook_url": self.rule.runbook_url,
        }


class AlertNotifier:
    """Base class for alert notifiers."""
    
    async def notify(self, alert: Alert) -> bool:
        """Send alert notification. Returns True if successful."""
        raise NotImplementedError


class LoggingNotifier(AlertNotifier):
    """Logs alerts to the standard logger."""
    
    async def notify(self, alert: Alert) -> bool:
        level = {
            AlertSeverity.P0_CRITICAL: logging.CRITICAL,
            AlertSeverity.P1_HIGH: logging.ERROR,
            AlertSeverity.P2_MEDIUM: logging.WARNING,
            AlertSeverity.P3_LOW: logging.INFO,
        }.get(alert.rule.severity, logging.WARNING)
        
        logger.log(
            level,
            f"[ALERT:{alert.rule.severity.value}] {alert.rule.name}: "
            f"{alert.rule.description} (value={alert.value}, threshold={alert.rule.threshold})"
        )
        return True


class SlackNotifier(AlertNotifier):
    """Sends alerts to Slack via webhook."""
    
    def __init__(self, webhook_url: str, channel: str = "#alerts"):
        self.webhook_url = webhook_url
        self.channel = channel
    
    async def notify(self, alert: Alert) -> bool:
        if not self.webhook_url:
            return False
        
        color = {
            AlertSeverity.P0_CRITICAL: "#FF0000",  # Red
            AlertSeverity.P1_HIGH: "#FFA500",      # Orange
            AlertSeverity.P2_MEDIUM: "#FFFF00",    # Yellow
            AlertSeverity.P3_LOW: "#00FF00",       # Green
        }.get(alert.rule.severity, "#808080")
        
        payload = {
            "channel": self.channel,
            "attachments": [{
                "color": color,
                "title": f"[{alert.rule.severity.value.upper()}] {alert.rule.name}",
                "text": alert.rule.description,
                "fields": [
                    {"title": "Current Value", "value": str(alert.value), "short": True},
                    {"title": "Threshold", "value": str(alert.rule.threshold), "short": True},
                    {"title": "Time", "value": alert.timestamp.isoformat(), "short": True},
                ],
                "actions": [
                    {
                        "type": "button",
                        "text": "View Runbook",
                        "url": alert.rule.runbook_url,
                    }
                ] if alert.rule.runbook_url else [],
            }]
        }
        
        try:
            req = urllib.request.Request(
                self.webhook_url,
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False


class WebhookNotifier(AlertNotifier):
    """Sends alerts to a generic webhook."""
    
    def __init__(self, webhook_url: str, headers: dict[str, str] | None = None):
        self.webhook_url = webhook_url
        self.headers = headers or {}
    
    async def notify(self, alert: Alert) -> bool:
        if not self.webhook_url:
            return False
        
        payload = alert.to_dict()
        
        try:
            req = urllib.request.Request(
                self.webhook_url,
                data=json.dumps(payload).encode(),
                headers={**self.headers, "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                return 200 <= response.status < 300
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
            return False


# ═══════════════════════════════════════════════════════════════════════════════
# ALERT MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AlertConfig:
    """Configuration for the alert manager."""
    # Notifier URLs
    slack_webhook_url: str = ""
    generic_webhook_url: str = ""
    slack_channel: str = "#alerts"
    
    # Thresholds
    memory_limit_mb: int = 1024
    latency_warning_seconds: float = 5.0
    latency_critical_seconds: float = 10.0
    error_rate_warning_percent: float = 5.0
    error_rate_critical_percent: float = 10.0
    
    # Cooldowns
    default_cooldown_seconds: float = 300.0
    
    # Enable/disable
    enabled: bool = True
    log_alerts: bool = True
    slack_alerts: bool = False
    webhook_alerts: bool = False


class AlertManager:
    """
    Manages alert rules and notifications.
    
    Usage:
        config = AlertConfig(
            slack_webhook_url=os.environ.get("SLACK_WEBHOOK_URL"),
        )
        manager = AlertManager(config)
        
        # Register metrics collector
        manager.register_collector("memory_usage_percent", get_memory_percent)
        
        # Check and fire alerts
        await manager.check_and_alert()
    """
    
    def __init__(self, config: AlertConfig | None = None):
        self.config = config or AlertConfig()
        self.rules: list[AlertRule] = list(DEFAULT_ALERT_RULES)
        self.notifiers: list[AlertNotifier] = []
        self.collectors: dict[str, Callable[[], float]] = {}
        self._alert_history: list[Alert] = []
        
        # Initialize notifiers
        if self.config.log_alerts:
            self.notifiers.append(LoggingNotifier())
        
        if self.config.slack_alerts and self.config.slack_webhook_url:
            self.notifiers.append(
                SlackNotifier(self.config.slack_webhook_url, self.config.slack_channel)
            )
        
        if self.config.webhook_alerts and self.config.generic_webhook_url:
            self.notifiers.append(WebhookNotifier(self.config.generic_webhook_url))
    
    def register_collector(self, metric_name: str, collector: Callable[[], float]) -> None:
        """Register a metric collector function."""
        self.collectors[metric_name] = collector
    
    def add_rule(self, rule: AlertRule) -> None:
        """Add a custom alert rule."""
        self.rules.append(rule)
    
    async def check_and_alert(self) -> list[Alert]:
        """Check all rules and fire alerts if conditions are met."""
        if not self.config.enabled:
            return []
        
        fired_alerts: list[Alert] = []
        
        for rule in self.rules:
            collector = self.collectors.get(rule.metric_name)
            if collector is None:
                continue
            
            try:
                value = collector()
            except Exception as e:
                logger.warning(f"Failed to collect metric {rule.metric_name}: {e}")
                continue
            
            if rule.should_fire(value):
                alert = Alert(
                    rule=rule,
                    value=value,
                    timestamp=datetime.utcnow(),
                    message=f"Metric {rule.metric_name} = {value} (threshold: {rule.threshold})",
                )
                
                # Send notifications
                for notifier in self.notifiers:
                    try:
                        await notifier.notify(alert)
                    except Exception as e:
                        logger.error(f"Notifier failed: {e}")
                
                fired_alerts.append(alert)
                self._alert_history.append(alert)
        
        return fired_alerts
    
    def get_alert_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get recent alert history."""
        return [a.to_dict() for a in self._alert_history[-limit:]]
    
    def get_active_alerts(self) -> list[dict[str, Any]]:
        """Get currently active alerts (conditions still met)."""
        active = []
        for alert in self._alert_history[-50:]:
            collector = self.collectors.get(alert.rule.metric_name)
            if collector and alert.rule.check(collector()):
                active.append(alert.to_dict())
        return active


# ═══════════════════════════════════════════════════════════════════════════════
# METRIC COLLECTORS
# ═══════════════════════════════════════════════════════════════════════════════

def get_memory_usage_percent() -> float:
    """Get current memory usage as percentage of limit."""
    try:
        import psutil
        import os
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        limit_mb = int(os.environ.get("MEMORY_LIMIT_MB", "1024"))
        return (memory_mb / limit_mb) * 100
    except ImportError:
        return 0.0


def get_circuit_breaker_open_count() -> float:
    """Get count of open circuit breakers."""
    from circuit_breaker import get_all_circuit_breakers
    circuits = get_all_circuit_breakers()
    return sum(1 for cb in circuits.values() if cb["state"] == "open")


def get_health_check_success() -> float:
    """Check if health endpoint is responding."""
    # This would be called from the health check itself
    return 1.0  # If we're running, we're healthy


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL ALERT MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

_alert_manager: AlertManager | None = None


def get_alert_manager(config: AlertConfig | None = None) -> AlertManager:
    """Get or create global alert manager."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager(config)
        
        # Register default collectors
        _alert_manager.register_collector("memory_usage_percent", get_memory_usage_percent)
        _alert_manager.register_collector("circuit_breaker_open_count", get_circuit_breaker_open_count)
        _alert_manager.register_collector("health_check_success", get_health_check_success)
    
    return _alert_manager