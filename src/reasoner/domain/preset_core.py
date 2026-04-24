"""Core preset domain logic: dataclass, validation, and helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from reasoner.llm import ProviderRouter, _REGISTRY

if TYPE_CHECKING:
    from reasoner.core.protocol import PhaseConfig


# Single source of truth for valid routing role keys.
# When adding a new perspective, add its routing_key here.
_KNOWN_ROUTING_ROLES: frozenset[str] = frozenset({
    # Phase roles
    "classification",
    "decomposition",
    "scoring",
    "stress_testing",
    "synthesis",
    # Default perspective roles (must match PerspectiveDefinition.routing_key values)
    "constructive",
    "destructive",
    "systemic",
    "minimalist",
    # Delphi expert roles (Sprint 3 — B5)
    "expert_1",
    "expert_2",
    "expert_3",
    "expert_4",
    # Prompt enhancement (opt-in pre-phase)
    "prompt_enhancement",
    # CoVe roles
    "cove_draft",
    "cove_verify",
    "cove_answer",
    "cove_revise",
    # SoT roles
    "sot_skeleton",
    "sot_solve",
    "sot_assemble",
    # ToT roles
    "tot_decompose",
    "tot_generate",
    "tot_evaluate",
    "tot_backtrack",
    # PoT roles
    "pot_generate",
    "pot_execute",
    "pot_interpret",
    # Self-Discover roles
    "sd_select",
    "sd_adapt",
    "sd_implement",
    # PhaseSubAgent roles (v2.2 — per-subagent routing with fallbacks)
    "subagent_synthesis_analysis",
    "subagent_synthesis_writer",
    "subagent_critique_logic",
    "subagent_critique_evidence",
    "subagent_critique_bias",
    "subagent_critique_counter",
    "subagent_enhancement",
    "subagent_decomposition",
    "subagent_search_query",
    "subagent_search_eval",
    # Article Pipeline roles (research-backed article generation)
    "article_decompose",
    "article_claim_extract",
    "article_cove_verify",
    "article_cove_answer",
    "article_cove_revise",
    "article_verifier",
    "article_sot_skeleton",
    "article_sot_solve",
    "article_synthesize",
    "article_pre_mortem",
    "article_critic",
    "article_assemble",
})


def get_method_from_preset(preset: str) -> str:
    """Extract method name from preset string."""
    if "debate" in preset:
        return "debate"
    if "iterative" in preset:
        return "iterative"
    if "jury" in preset or "orchestrated" in preset:
        return "jury"
    if "research" in preset:
        return "research"
    if "scientific" in preset:
        return "scientific"
    if "socratic" in preset:
        return "socratic"
    if "pre-mortem" in preset or "premortem" in preset:
        return "pre_mortem"
    if "bayesian" in preset:
        return "bayesian"
    if "dialectical" in preset:
        return "dialectical"
    if "analogical" in preset:
        return "analogical"
    if "delphi" in preset:
        return "delphi"
    if "self-discover" in preset:
        return "self_discover"
    if "cove" in preset:
        return "cove"
    if "writing" in preset:
        return "writing"
    if "sot" in preset:
        return "sot"
    if "tot" in preset:
        return "tot"
    if "pot" in preset:
        return "pot"
    if "cross-language" in preset or "cross_language" in preset:
        return "cross_language"
    return "multi-perspective"


def get_preset_tier(preset_id: str) -> Literal["budget", "premium", "unknown"]:
    """Infer pricing tier from preset ID suffix."""
    if preset_id.endswith("-budget"):
        return "budget"
    if preset_id.endswith("-premium"):
        return "premium"
    return "unknown"


_METHOD_TO_SLUG: dict[str, str] = {
    "debate": "debate",
    "scientific": "scientific",
    "socratic": "socratic",
    "multi_perspective": "multi-perspective",
    "iterative": "multi-perspective",   # no iterative preset — fall back to multi-perspective
    "research": "research",
    "jury": "jury",
    "pre_mortem": "pre-mortem",
    "bayesian": "bayesian",
    "dialectical": "dialectical",
    "analogical": "analogical",
    "delphi": "delphi",
    "cove": "cove",
    "sot": "sot",
    "tot": "tot",
    "pot": "pot",
    "self_discover": "self-discover",
    "writing": "writing",
}


def build_auto_preset(method: str, tier: str = "budget") -> str:
    """Build a preset name from method classifier output."""
    safe_tier = tier if tier in ("budget", "premium") else "budget"
    slug = _METHOD_TO_SLUG.get(method, "multi-perspective")
    candidate = f"{slug}-{safe_tier}"
    # Belt-and-suspenders: confirm it actually exists in the registry.
    # We avoid a circular import by doing a late import of is_valid_preset_name.
    from reasoner.domain.preset_registry import PRESETS
    if candidate in PRESETS:
        return candidate
    return f"multi-perspective-{safe_tier}"


# Agent model used for follow-up synthesis / classification / decomposition.
# This ensures a consistent conversational persona across all methods.
FOLLOWUP_AGENT_MODELS: dict[str, str] = {
    "budget": "kimi-k2-6",
    "premium": "grok-4.20",
}


@dataclass
class PipelinePreset:
    """A named routing configuration with metadata."""
    name: str
    description: str
    primary_id: str
    routing: dict[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    required_env_vars: list[str] = field(default_factory=list)
    # Per-role fallback model IDs. If a role's provider fails, this model is tried next.
    # Roles absent here fall back to primary automatically (if they use a non-primary model).
    fallback_routing: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate routing keys and model IDs at construction time."""
        unknown_roles = set(self.routing.keys()) - _KNOWN_ROUTING_ROLES
        if unknown_roles:
            raise ValueError(
                f"Preset '{self.name}' has unknown routing keys: {sorted(unknown_roles)}. "
                f"Valid roles: {sorted(_KNOWN_ROUTING_ROLES)}"
            )
        unknown_models = {
            role: mid for role, mid in self.routing.items() if mid not in _REGISTRY
        }
        if unknown_models:
            raise ValueError(
                f"Preset '{self.name}' references unknown model IDs: {unknown_models}. "
                f"Run 'python main.py --list-models' to see valid IDs."
            )
        if self.primary_id not in _REGISTRY:
            raise ValueError(
                f"Preset '{self.name}' primary model '{self.primary_id}' is not in the registry. "
                f"Run 'python main.py --list-models' to see valid IDs."
            )
        unknown_fb_roles = set(self.fallback_routing.keys()) - _KNOWN_ROUTING_ROLES
        if unknown_fb_roles:
            raise ValueError(
                f"Preset '{self.name}' has unknown fallback routing keys: {sorted(unknown_fb_roles)}. "
                f"Valid roles: {sorted(_KNOWN_ROUTING_ROLES)}"
            )
        unknown_fb_models = {
            role: mid for role, mid in self.fallback_routing.items() if mid not in _REGISTRY
        }
        if unknown_fb_models:
            raise ValueError(
                f"Preset '{self.name}' references unknown fallback model IDs: {unknown_fb_models}. "
                f"Run 'python main.py --list-models' to see valid IDs."
            )

    def build_router(self) -> ProviderRouter:
        return ProviderRouter.from_model_ids(
            primary_id=self.primary_id,
            routing=self.routing,
            fallback_routing=self.fallback_routing,
        )

    def check_keys(self) -> dict[str, bool]:
        """Return {env_var: is_set} for all required API keys."""
        return {k: bool(os.environ.get(k)) for k in self.required_env_vars}

    def missing_keys(self) -> list[str]:
        return [k for k, present in self.check_keys().items() if not present]
