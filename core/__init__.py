"""
core — shared abstractions for the ARA pipeline.

Imports:
    from core import Phase, PhaseResult, PhaseConfig, make_phase_result
    from core import PerspectiveDefinition, DEFAULT_PERSPECTIVES, PERSPECTIVES_BY_NAME
"""

from core.protocol import Phase, PhaseConfig, PhaseResult, make_phase_result
from core.perspectives import PerspectiveDefinition, DEFAULT_PERSPECTIVES, PERSPECTIVES_BY_NAME

__all__ = [
    "Phase",
    "PhaseConfig",
    "PhaseResult",
    "make_phase_result",
    "PerspectiveDefinition",
    "DEFAULT_PERSPECTIVES",
    "PERSPECTIVES_BY_NAME",
]
