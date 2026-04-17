"""
MethodClassifierSubAgent — ONE JOB: classify which reasoning method best fits
the problem, using an opaque letter taxonomy (B–Q).

The real method names are NEVER exposed to the LLM (security: prevents prompt
injection that could manipulate routing by naming a method directly).

Output schema: {category: str (B–Q), confidence: float, rationale: str}
"""

from __future__ import annotations

from typing import Any

from reasoner.core.constants import HYPERGATE_MAX_TOKENS_METHOD
from reasoner.hypergate.base_sub_agent import BaseSubAgent

# Opaque taxonomy — letters only, no real method names visible to LLM.
# A and W are intentionally excluded: those cases are handled by DirectDetector
# and WebDetector respectively.
_TAXONOMY: dict[str, tuple[str, str]] = {
    "B": ("pipeline", "debate"),
    "C": ("pipeline", "scientific"),
    "D": ("pipeline", "socratic"),
    "E": ("pipeline", "multi_perspective"),
    "F": ("pipeline", "iterative"),
    "G": ("pipeline", "research"),
    "H": ("pipeline", "pre_mortem"),
    "I": ("pipeline", "bayesian"),
    "J": ("pipeline", "dialectical"),
    "K": ("pipeline", "analogical"),
    "L": ("pipeline", "delphi"),
    "M": ("pipeline", "cove"),
    "N": ("pipeline", "sot"),
    "O": ("pipeline", "tot"),
    "P": ("pipeline", "pot"),
    "Q": ("pipeline", "self_discover"),
}

_SYSTEM = (
    "You are a reasoning-method classifier. Read the user's problem and choose the single "
    "best category from the list below.\n\n"
    "Categories:\n"
    "- B: problem with conflicting viewpoints that need adversarial debate\n"
    "- C: requires scientific hypothesis generation and falsification testing\n"
    "- D: benefits from deep Socratic questioning to expose hidden assumptions\n"
    "- E: needs multi-faceted analysis from several independent perspectives\n"
    "- F: requires iterative refinement — early drafts improve over multiple rounds\n"
    "- G: requires deep research synthesis across many sources\n"
    "- H: risk assessment — imagine the project failing and work backwards\n"
    "- I: involves explicit probability estimation and Bayesian belief updates\n"
    "- J: dialectical synthesis — thesis, antithesis, transcendence\n"
    "- K: cross-domain analogical reasoning to transfer solutions\n"
    "- L: requires expert panel consensus through structured rounds\n"
    "- M: requires structured fact-checking and claim verification\n"
    "- N: can be decomposed into independent parallel subtasks then assembled\n"
    "- O: requires sequential decision-tree exploration of solution branches\n"
    "- P: requires computational or mathematical reasoning with executable code\n"
    "- Q: requires dynamic composition of reasoning modules to fit the problem\n\n"
    "Output ONLY valid JSON with exactly three keys: "
    "'category' (one letter B–Q), "
    "'confidence' (float 0.0–1.0), "
    "'rationale' (one short sentence). "
    "No markdown, no extra text."
)


class MethodClassifierSubAgent(BaseSubAgent):
    AGENT_NAME = "method_classifier"
    MAX_TOKENS = HYPERGATE_MAX_TOKENS_METHOD

    def _system_prompt(self) -> str:
        return _SYSTEM

    def _parse_result(self, raw: str) -> dict[str, Any]:
        try:
            data = self._extract_json(raw)
            category = str(data.get("category", "")).strip().upper()
            if category not in _TAXONOMY:
                category = "E"  # default to multi_perspective
            action, method = _TAXONOMY[category]
            return {
                "category": category,
                "action": action,
                "method": method,
                "confidence": min(1.0, max(0.0, float(data.get("confidence", 0.5)))),
                "rationale": str(data.get("rationale", "")),
            }
        except Exception:
            return {
                "category": "E",
                "action": "pipeline",
                "method": "multi_perspective",
                "confidence": 0.0,
                "rationale": "parse error",
            }

    @staticmethod
    def resolve(category: str) -> tuple[str, str]:
        """Map a taxonomy letter to (action, method). Safe fallback to E."""
        return _TAXONOMY.get(category.upper(), _TAXONOMY["E"])
