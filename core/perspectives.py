"""
Data-driven perspective definitions for Phase 2 (Multi-Perspective Analysis).

Replaces the PERSPECTIVE_SYSTEMS dict in phases.py with typed, self-contained objects.
Adding a new perspective requires only:
  1. Append a PerspectiveDefinition here
  2. Add the routing_key to the preset's routing dict
  3. Add the name to _KNOWN_ROUTING_ROLES in presets.py
  4. Add the enum value to PerspectiveType in models.py (if SolutionCandidate.perspective is typed)

No changes needed in pipeline.py, phases.py, or the orchestration loop.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PerspectiveDefinition:
    """
    Self-contained definition of one analysis perspective.

    name        — matches PerspectiveType enum value (e.g. "constructive")
    label       — human-readable display name for renderer
    system_prompt — full system prompt passed to LLM as the system role
    routing_key — ProviderRouter role key (usually identical to name)
    """
    name: str
    label: str
    system_prompt: str
    routing_key: str


DEFAULT_PERSPECTIVES: list[PerspectiveDefinition] = [
    PerspectiveDefinition(
        name="constructive",
        label="Constructive Analysis",
        system_prompt=(
            "You reason constructively.\n"
            "Find the strongest possible solution. Focus on what works and why.\n"
            "Be specific, evidence-grounded, and actionable.\n"
            "Output ONLY valid JSON."
        ),
        routing_key="constructive",
    ),
    PerspectiveDefinition(
        name="destructive",
        label="Adversarial Critique",
        system_prompt=(
            "You are a rigorous critic and adversary.\n"
            "Your sole goal: find every way this problem resists solution.\n"
            "Attack assumptions, find edge cases, expose hidden failure modes.\n"
            "Do NOT propose solutions — only identify weaknesses.\n"
            "Output ONLY valid JSON."
        ),
        routing_key="destructive",
    ),
    PerspectiveDefinition(
        name="systemic",
        label="Systems Analysis",
        system_prompt=(
            "You think in systems.\n"
            "Identify second and third-order effects. How does any solution interact\n"
            "with the broader system? What unintended consequences emerge?\n"
            "Focus on emergent properties and feedback loops.\n"
            "Output ONLY valid JSON."
        ),
        routing_key="systemic",
    ),
    PerspectiveDefinition(
        name="minimalist",
        label="Minimalist Reduction",
        system_prompt=(
            "You apply Occam's Razor aggressively.\n"
            "Find the simplest solution that addresses \u226580% of the problem.\n"
            "Cut complexity ruthlessly. What is truly necessary vs what is merely comfortable?\n"
            "Output ONLY valid JSON."
        ),
        routing_key="minimalist",
    ),
]

# Lookup by name for O(1) access in pipeline
PERSPECTIVES_BY_NAME: dict[str, PerspectiveDefinition] = {
    p.name: p for p in DEFAULT_PERSPECTIVES
}
