"""
Data models for PhaseSubAgent communication protocol.

Phase-level subagents receive mutable PipelineState (not frozen like HyperGate)
and return structured outputs that are accumulated into the state for transparency.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PhaseSubAgentInput:
    """Sent by a PhaseHyperAgent to each sub-agent."""
    agent_name: str
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class PhaseSubAgentOutput:
    """Returned by every phase sub-agent back to its hyper-agent."""
    agent_name: str
    result: dict[str, Any]          # agent-specific payload
    confidence: float               # 0.0–1.0
    reasoning: str                  # human-readable rationale
    tokens_in: int
    tokens_out: int
    model: str
    duration_ms: float
    error: str | None = None        # non-None = graceful failure

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "result": self.result,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "model": self.model,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }
