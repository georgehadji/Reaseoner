"""
ARA Pipeline - Core Data Models
Adaptive Reasoning Architecture v2.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from core.protocol import PhaseResult


class TaskType(str, Enum):
    ANALYTICAL = "analytical"
    STRATEGIC = "strategic"
    CREATIVE = "creative"
    TECHNICAL = "technical"
    HYBRID = "hybrid"


class ClaimLabel(str, Enum):
    VERIFIED = "VERIFIED"
    HYPOTHESIS = "HYPOTHESIS"
    UNKNOWN = "UNKNOWN"


class ModelProvider(str, Enum):
    ANTHROPIC  = "anthropic"
    OPENAI     = "openai"
    GOOGLE     = "google"
    XAI        = "xai"
    PERPLEXITY = "perplexity"
    MISTRAL    = "mistral"
    DEEPSEEK   = "deepseek"
    QWEN       = "qwen"
    KIMI       = "kimi"
    GLM        = "glm"
    MINIMAX    = "minimax"


class PerspectiveType(str, Enum):
    CONSTRUCTIVE = "constructive"
    DESTRUCTIVE = "destructive"
    SYSTEMIC = "systemic"
    MINIMALIST = "minimalist"


class ScenarioType(str, Enum):
    OPTIMAL = "optimal"
    CONSTRAINT_VIOLATION = "constraint_violation"
    ADVERSARIAL = "adversarial"


@dataclass
class SubProblem:
    id: str
    description: str
    inputs: list[str]
    outputs: list[str]
    constraints: list[str]


@dataclass
class Assumption:
    text: str
    label: ClaimLabel
    rationale: str


@dataclass
class Decomposition:
    sub_problems: list[SubProblem]
    assumptions: list[Assumption]
    failure_modes: list[str]
    raw_response: str


@dataclass
class SolutionCandidate:
    perspective: PerspectiveType
    content: str
    key_insights: list[str]
    model_used: str


@dataclass
class CritiqueScore:
    perspective: PerspectiveType
    logical_consistency: float       # 0-10
    evidence_support: float          # 0-10
    failure_resilience: float        # 0-10
    feasibility: float               # 0-10
    bias_flags: list[str]
    steel_man: str                   # strongest counter-argument

    @property
    def total(self) -> float:
        return (
            self.logical_consistency
            + self.evidence_support
            + self.failure_resilience
            + self.feasibility
        ) / 4.0


@dataclass
class StressTestResult:
    scenario: ScenarioType
    survival_rate: float             # 0.0 - 1.0
    failure_mode: str
    recovery_path: str


@dataclass
class MetaCognitiveAudit:
    most_dangerous_assumption: str
    dominant_bias: str
    remaining_uncertainty: str
    assumption_failure_impact: str
    non_obvious_insight: str


@dataclass
class FinalSolution:
    core_solution: str
    critical_insights: list[str]     # max 5, non-obvious only
    action_blueprint: list[dict[str, Any]]
    open_questions: list[str]
    claim_labels: dict[str, ClaimLabel]
    meta_audit: MetaCognitiveAudit


@dataclass
class PipelineState:
    """Complete pipeline state — passed between phases."""
    problem: str
    started_at: "datetime" = field(default_factory=datetime.now)
    task_type: TaskType | None = None
    task_type_rationale: str = ""
    language: str = "English"  # Detected language from the problem
    decomposition: Decomposition | None = None
    candidates: list[SolutionCandidate] = field(default_factory=list)
    scores: list[CritiqueScore] = field(default_factory=list)
    top_candidates: list[SolutionCandidate] = field(default_factory=list)
    stress_results: list[StressTestResult] = field(default_factory=list)
    final_solution: FinalSolution | None = None
    phase_logs: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    # Tracks which model was used for each phase role
    phase_models: dict[str, str] = field(default_factory=dict)
    # Tracks tokens used per phase: {phase_name: {"input": int, "output": int}}
    phase_tokens: dict[str, dict[str, int]] = field(default_factory=dict)
    # Immutable per-phase results (foundation for future resume/replay support)
    phase_results: list["PhaseResult"] = field(default_factory=list)
    # Which preset was used — drives method-specific rendering
    preset_name: str | None = None

    def log(self, phase: str, message: str) -> None:
        entry = f"[{phase}] {message}"
        self.phase_logs.append(entry)

    def to_context_dict(self) -> dict[str, Any]:
        """Serialize state for passing to next LLM call."""
        return {
            "problem": self.problem,
            "task_type": self.task_type.value if self.task_type else None,
            "language": self.language,
            "sub_problems": [
                {
                    "id": sp.id,
                    "description": sp.description,
                    "inputs": sp.inputs,
                    "outputs": sp.outputs,
                    "constraints": sp.constraints,
                }
                for sp in (self.decomposition.sub_problems if self.decomposition else [])
            ],
            "assumptions": [
                {"text": a.text, "label": a.label.value}
                for a in (self.decomposition.assumptions if self.decomposition else [])
            ],
            "candidates": [
                {
                    "perspective": c.perspective.value,
                    "content": c.content[:800],  # truncate for context efficiency
                    "key_insights": c.key_insights,
                }
                for c in self.top_candidates or self.candidates
            ],
            "scores": [
                {
                    "perspective": s.perspective.value,
                    "total": round(s.total, 2),
                    "bias_flags": s.bias_flags,
                }
                for s in self.scores
            ],
            "stress_results": [
                {
                    "scenario": sr.scenario.value,
                    "survival_rate": sr.survival_rate,
                    "failure_mode": sr.failure_mode,
                    "recovery_path": sr.recovery_path,
                }
                for sr in self.stress_results
            ],
        }
