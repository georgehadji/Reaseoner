"""
ARA Pipeline — Routing Presets
Pre-built pipeline configurations for every use case.

Each preset defines which model handles which phase role.
Roles: classification, decomposition, constructive, destructive,
       systemic, minimalist, scoring, stress_testing, synthesis
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from reasoner.llm import ProviderRouter, build_provider, list_models, _REGISTRY

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
    # Post-synthesis verification
    "post_synthesis_verify",
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
    if "sot" in preset:
        return "sot"
    if "tot" in preset:
        return "tot"
    if "pot" in preset:
        return "pot"
    return "multi-perspective"


def get_preset_tier(preset_id: str) -> Literal["budget", "premium", "unknown"]:
    """Infer pricing tier from preset ID suffix."""
    if preset_id.endswith("-budget"):
        return "budget"
    if preset_id.endswith("-premium"):
        return "premium"
    return "unknown"


# Maps HyperGateAgent method names → preset slug prefixes.
# Keys are the method strings returned by MethodClassifierSubAgent.
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
}


def build_auto_preset(method: str, tier: str) -> str:
    """Translate a HyperGate method name + tier into a valid preset ID.

    Examples:
        build_auto_preset("debate", "budget")       → "debate-budget"
        build_auto_preset("self_discover", "premium") → "self-discover-premium"
        build_auto_preset("unknown_method", "budget") → "multi-perspective-budget"

    The tier must be "budget" or "premium". Any other value falls back to "budget".
    """
    safe_tier = tier if tier in ("budget", "premium") else "budget"
    slug = _METHOD_TO_SLUG.get(method, "multi-perspective")
    candidate = f"{slug}-{safe_tier}"
    # Belt-and-suspenders: confirm it actually exists in the registry.
    if is_valid_preset_name(candidate):
        return candidate
    return f"multi-perspective-{safe_tier}"


# Agent model used for follow-up synthesis / classification / decomposition.
# This ensures a consistent conversational persona across all methods.
FOLLOWUP_AGENT_MODELS: dict[str, str] = {
    "budget": "kimi-k2-5",
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
    # Per-phase LLM parameter overrides; keys must match ARAPipeline._PHASE_CONFIGS keys
    phase_overrides: "dict[str, PhaseConfig]" = field(default_factory=dict)
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


# ─────────────────────────────────────────────────────────────────────
# PRESET FACTORY
# ─────────────────────────────────────────────────────────────────────

# Declarative configuration for all 24 presets (2 per method).
_PRESET_CONFIGS: list[dict] = [
    # ── Multi-Perspective ───────────────────────────────────────────
    {
        "id": "multi-perspective-budget",
        "name": "Multi-Perspective (Budget)",
        "description": "Standard 6-phase pipeline using cheapest cross-lab models. DeepSeek (reasoning) + Qwen (cross-lab scoring). Pennies per run.",
        "primary_id": "deepseek-v3",
        "routing": {
            "prompt_enhancement": "gemma-4-26b",
            "classification": "gemma-4-26b",
            "decomposition": "deepseek-v3",
            "constructive": "deepseek-v3",
            "destructive": "mistral-large-3",
            "systemic": "deepseek-v3",
            "minimalist": "gemma-4-26b",
            "scoring": "deepseek-v3",
            "stress_testing": "deepseek-v3",
            "synthesis": "qwen3-max"
        },
        "fallback_routing": {
            "prompt_enhancement": "glm-4-air",
            "classification": "glm-4-air",
            "decomposition": "glm-4-air",
            "constructive": "qwen3-plus",
            "destructive": "deepseek-v3",
            "systemic": "qwen3-plus",
            "minimalist": "deepseek-v3",
            "scoring": "glm-4-air",
            "stress_testing": "qwen3-plus",
            "synthesis": "glm-4-air"
        },
        "notes": [
            "DeepSeek + Qwen + GLM: 3 different labs in Phase 2 = genuine diversity",
            "qwen3-turbo at ~$0.03/M is the cheapest capable model in registry",
            "Full run estimated at <$0.02 total",
        ],
    },
    {
        "id": "multi-perspective-premium",
        "name": "Multi-Perspective (Premium)",
        "description": "Best available model per phase. Perplexity Sonar fact-checks candidates in Phase 3. GLM-5 and Claude Opus dual-check synthesis. Cross-ecosystem for maximum epistemic diversity.",
        "primary_id": "claude-opus",
        "routing": {
            "prompt_enhancement": "gemini-flash",
            "classification": "gemini-flash",
            "decomposition": "claude-sonnet",
            "constructive": "kimi-k2-5",
            "destructive": "deepseek-r1",
            "systemic": "claude-opus",
            "minimalist": "gemini-flash",
            "scoring": "sonar-pro",
            "stress_testing": "claude-opus",
            "synthesis": "claude-opus"
        },
        "fallback_routing": {
            "prompt_enhancement": "claude-sonnet",
            "classification": "deepseek-r1",
            "decomposition": "gemini-flash",
            "constructive": "claude-opus",
            "destructive": "claude-opus",
            "systemic": "deepseek-r1",
            "minimalist": "deepseek-r1",
            "scoring": "claude-opus",
            "stress_testing": "deepseek-r1",
            "synthesis": "gpt-5"
        },
        "notes": [
            "Phase 2: Moonshot + DeepSeek + Anthropic + Mistral — 4 different training lineages",
            "Sonar Pro in scoring phase enables live fact-checking of candidates",
            "GLM-5 for synthesis: top of Artificial Analysis Intelligence Index",
            "Kimi K2.5 for constructive: strongest creative breadth in Chinese OSS",
            "DeepSeek for destructive: 85K+ adversarial RL environments",
            "Ministral-8b for minimalist: order-of-magnitude fewer tokens by design",
        ],
    },
    # ── Debate ───────────────────────────────────────────────────────
    {
        "id": "debate-budget",
        "name": "Debate (Budget)",
        "description": "Adversarial debate with 3 cheap cross-lab models. DeepSeek (Model A) vs Qwen (Model B), judged by GLM. 3 different training lineages.",
        "primary_id": "deepseek-v3",
        "routing": {
            "prompt_enhancement": "gemma-4-26b",
            "classification": "gemma-4-26b",
            "decomposition": "deepseek-v3",
            "constructive": "deepseek-v3",
            "destructive": "qwen3-max",
            "systemic": "glm-4-air",
            "minimalist": "gemma-4-26b",
            "scoring": "glm-4-air",
            "stress_testing": "deepseek-v3",
            "synthesis": "deepseek-v3"
        },
        "fallback_routing": {
            "prompt_enhancement": "glm-4-air",
            "classification": "glm-4-air",
            "decomposition": "glm-4-air",
            "constructive": "qwen3-plus",
            "destructive": "deepseek-v3",
            "systemic": "deepseek-v3",
            "minimalist": "deepseek-v3",
            "scoring": "qwen3-plus",
            "stress_testing": "qwen3-plus",
            "synthesis": "glm-4-air"
        },
        "notes": [
            "3 labs: DeepSeek / Qwen (Alibaba) / GLM (ZhipuAI) — genuine adversarial dynamic",
            "GLM as neutral judge: not invested in either A or B training paradigm",
        ],
    },
    {
        "id": "debate-premium",
        "name": "Debate (Premium)",
        "description": "Two models (A & B) generate independent solutions. A third model (Judge) evaluates and selects the best. Ideal for complex decisions requiring multiple perspectives.",
        "primary_id": "claude-sonnet",
        "routing": {
            "prompt_enhancement": "gemini-flash",
            "classification": "gemini-flash",
            "decomposition": "claude-sonnet",
            "constructive": "gpt-5",
            "destructive": "claude-opus",
            "systemic": "deepseek-r1",
            "minimalist": "claude-sonnet",
            "scoring": "sonar-pro",
            "stress_testing": "claude-opus",
            "synthesis": "claude-sonnet"
        },
        "fallback_routing": {
            "prompt_enhancement": "claude-sonnet",
            "classification": "deepseek-r1",
            "decomposition": "gemini-flash",
            "constructive": "claude-opus",
            "destructive": "deepseek-r1",
            "systemic": "claude-opus",
            "minimalist": "deepseek-r1",
            "scoring": "claude-opus",
            "stress_testing": "deepseek-r1",
            "synthesis": "claude-opus"
        },
        "notes": [
            "Model A (GPT-5), Model B (Claude Opus), systemic (DeepSeek) = 3 labs",
            "Sonar Pro as independent judge with live web fact-checking",
        ],
    },
    # ── Scientific ───────────────────────────────────────────────────
    {
        "id": "scientific-budget",
        "name": "Scientific (Budget)",
        "description": "Evidence-grounded analysis with minimal cost. Sonar for search phases only, DeepSeek for reasoning. Single web-search provider with cross-lab diversity.",
        "primary_id": "sonar",
        "routing": {
            "prompt_enhancement": "gemma-4-26b",
            "classification": "sonar",
            "decomposition": "deepseek-v3",
            "constructive": "sonar",
            "destructive": "deepseek-v3",
            "systemic": "glm-4-air",
            "minimalist": "sonar",
            "scoring": "deepseek-v3",
            "stress_testing": "deepseek-v3",
            "synthesis": "sonar"
        },
        "fallback_routing": {
            "prompt_enhancement": "glm-4-air",
            "classification": "glm-4-air",
            "decomposition": "glm-4-air",
            "constructive": "deepseek-v3",
            "systemic": "deepseek-v3",
            "scoring": "glm-4-air",
            "stress_testing": "qwen3-plus",
            "synthesis": "deepseek-v3"
        },
        "notes": [
            "Sonar only in classification + synthesis for minimum search cost",
            "DeepSeek + Qwen + GLM for reasoning: 3 different labs, different biases",
        ],
    },
    {
        "id": "scientific-premium",
        "name": "Scientific (Premium)",
        "description": "Perplexity Sonar grounded models dominate. Every phase benefits from web-verified evidence. Ideal for empirical questions, current events, market analysis.",
        "primary_id": "sonar-pro",
        "routing": {
            "prompt_enhancement": "gemini-flash",
            "classification": "sonar",
            "decomposition": "claude-sonnet",
            "constructive": "sonar-deep-research",
            "destructive": "deepseek-r1",
            "systemic": "claude-sonnet",
            "minimalist": "sonar",
            "scoring": "sonar-pro",
            "stress_testing": "grok-4",
            "synthesis": "sonar-deep-research"
        },
        "fallback_routing": {
            "prompt_enhancement": "claude-sonnet",
            "classification": "claude-sonnet",
            "decomposition": "gemini-flash",
            "constructive": "claude-sonnet",
            "destructive": "claude-opus",
            "systemic": "claude-sonnet",
            "minimalist": "claude-sonnet",
            "scoring": "claude-sonnet",
            "stress_testing": "deepseek-r1",
            "synthesis": "claude-sonnet"
        },
        "notes": [
            "WARNING: Sonar models add search latency (~2-5x slower)",
            "Each Sonar call includes citations — synthesis is verifiable",
            "Deep Research performs 20-30 web searches per call",
        ],
    },
    # ── Socratic ─────────────────────────────────────────────────────
    {
        "id": "socratic-budget",
        "name": "Socratic (Budget)",
        "description": "Standard 6-phase pipeline using cheapest cross-lab models. DeepSeek (reasoning) + Qwen (cross-lab scoring). Pennies per run.",
        "primary_id": "deepseek-v3",
        "routing": {
            "prompt_enhancement": "gemma-4-26b",
            "classification": "gemma-4-26b",
            "decomposition": "deepseek-v3",
            "constructive": "deepseek-v3",
            "destructive": "qwen3-max",
            "systemic": "glm-4-air",
            "minimalist": "gemma-4-26b",
            "scoring": "deepseek-v3",
            "stress_testing": "deepseek-v3",
            "synthesis": "deepseek-v3"
        },
        "fallback_routing": {
            "prompt_enhancement": "glm-4-air",
            "classification": "glm-4-air",
            "decomposition": "glm-4-air",
            "constructive": "qwen3-plus",
            "destructive": "deepseek-v3",
            "systemic": "deepseek-v3",
            "minimalist": "deepseek-v3",
            "scoring": "glm-4-air",
            "stress_testing": "qwen3-plus",
            "synthesis": "glm-4-air"
        },
        "notes": [
            "DeepSeek + Qwen + GLM: 3 different labs in Phase 2 = genuine diversity",
            "qwen3-turbo at ~$0.03/M is the cheapest capable model in registry",
        ],
    },
    {
        "id": "socratic-premium",
        "name": "Socratic (Premium)",
        "description": "Pure open-weight Chinese ecosystem. ~30x cheaper than GPT-5 per token. Cross-lab scoring (Claude evaluates DeepSeek/Kimi/GLM candidates).",
        "primary_id": "deepseek-v3",
        "routing": {
            "prompt_enhancement": "gemini-flash",
            "classification": "gemini-flash",
            "decomposition": "claude-sonnet",
            "constructive": "kimi-k2-5",
            "destructive": "deepseek-r1",
            "systemic": "qwen3-max",
            "minimalist": "glm-5.1",
            "scoring": "claude-sonnet",
            "stress_testing": "deepseek-r1",
            "synthesis": "glm-5.1"
        },
        "fallback_routing": {
            "prompt_enhancement": "claude-sonnet",
            "classification": "claude-sonnet",
            "decomposition": "glm-4-air",
            "constructive": "deepseek-r1",
            "systemic": "deepseek-r1",
            "minimalist": "deepseek-r1",
            "scoring": "qwen3-max",
            "stress_testing": "qwen3-max",
            "synthesis": "claude-sonnet"
        },
        "notes": [
            "All models open-weight — can be self-hosted for zero API cost",
            "DeepSeek ~$0.27/M, Qwen ~$0.03/M, GLM-Air ~$0.05/M",
            "Cross-lab: Claude Sonnet scores DeepSeek/Kimi/GLM/Qwen candidates (Western judges Chinese OSS)",
        ],
    },
    # ── Research ─────────────────────────────────────────────────────
    {
        "id": "research-budget",
        "name": "Research (Budget)",
        "description": "Evidence-grounded analysis with minimal cost. Sonar for search phases only, DeepSeek for reasoning. Single web-search provider with cross-lab diversity.",
        "primary_id": "sonar",
        "routing": {
            "prompt_enhancement": "gemma-4-26b",
            "classification": "sonar",
            "decomposition": "deepseek-v3",
            "constructive": "sonar",
            "destructive": "deepseek-v3",
            "systemic": "glm-4-air",
            "minimalist": "sonar",
            "scoring": "deepseek-v3",
            "stress_testing": "deepseek-v3",
            "synthesis": "sonar"
        },
        "fallback_routing": {
            "prompt_enhancement": "glm-4-air",
            "classification": "glm-4-air",
            "decomposition": "glm-4-air",
            "constructive": "deepseek-v3",
            "systemic": "deepseek-v3",
            "scoring": "glm-4-air",
            "stress_testing": "qwen3-plus",
            "synthesis": "deepseek-v3"
        },
        "notes": [
            "Sonar only in classification + synthesis for minimum search cost",
            "DeepSeek + Qwen + GLM for reasoning: 3 different labs, different biases",
        ],
    },
    {
        "id": "research-premium",
        "name": "Research (Premium)",
        "description": "Perplexity Sonar grounded models dominate. Every phase benefits from web-verified evidence. Ideal for empirical questions, current events, market analysis.",
        "primary_id": "sonar-pro",
        "routing": {
            "prompt_enhancement": "gemini-flash",
            "classification": "sonar",
            "decomposition": "claude-sonnet",
            "constructive": "sonar-deep-research",
            "destructive": "deepseek-r1",
            "systemic": "claude-opus",
            "minimalist": "sonar",
            "scoring": "sonar-pro",
            "stress_testing": "grok-4",
            "synthesis": "sonar-deep-research"
        },
        "fallback_routing": {
            "prompt_enhancement": "claude-sonnet",
            "classification": "claude-sonnet",
            "decomposition": "gemini-flash",
            "constructive": "claude-sonnet",
            "destructive": "claude-opus",
            "systemic": "claude-sonnet",
            "minimalist": "claude-sonnet",
            "scoring": "claude-sonnet",
            "stress_testing": "deepseek-r1",
            "synthesis": "claude-sonnet"
        },
        "notes": [
            "WARNING: Sonar models add search latency (~2-5x slower)",
            "Each Sonar call includes citations — synthesis is verifiable",
            "Deep Research performs 20-30 web searches per call",
        ],
    },
    # ── Jury ─────────────────────────────────────────────────────────
    {
        "id": "jury-budget",
        "name": "Jury (Budget)",
        "description": "Panel-of-experts evaluation using cheap cross-lab models. DeepSeek reasoning + Qwen cross-scoring for impartial verdicts.",
        "primary_id": "deepseek-v3",
        "routing": {
            "prompt_enhancement": "gemma-4-26b",
            "classification": "gemma-4-26b",
            "decomposition": "deepseek-v3",
            "constructive": "deepseek-v3",
            "destructive": "qwen3-max",
            "systemic": "glm-4-air",
            "minimalist": "gemma-4-26b",
            "scoring": "qwen3-max",
            "stress_testing": "deepseek-v3",
            "synthesis": "deepseek-v3"
        },
        "fallback_routing": {
            "prompt_enhancement": "glm-4-air",
            "classification": "glm-4-air",
            "decomposition": "glm-4-air",
            "constructive": "qwen3-plus",
            "destructive": "deepseek-v3",
            "systemic": "deepseek-v3",
            "minimalist": "deepseek-v3",
            "scoring": "glm-4-air",
            "stress_testing": "qwen3-plus",
            "synthesis": "glm-4-air"
        },
        "notes": [
            "DeepSeek + Qwen + GLM: 3 different labs in Phase 2 = genuine diversity",
            "Budget-friendly panel evaluation for multi-candidate problems",
        ],
    },
    {
        "id": "jury-premium",
        "name": "Jury (Premium)",
        "description": "One model per lab in Phase 2. Chinese + Western + EU + real-time coverage. Perplexity for grounded critique. Grok for real-time synthesis.",
        "primary_id": "claude-sonnet",
        "routing": {
            "prompt_enhancement": "gemini-flash",
            "classification": "gemini-flash",
            "decomposition": "claude-sonnet",
            "constructive": "kimi-k2-5",
            "destructive": "deepseek-r1",
            "systemic": "claude-opus",
            "minimalist": "mistral-large-3",
            "scoring": "sonar-pro",
            "stress_testing": "grok-4",
            "synthesis": "gpt-5"
        },
        "fallback_routing": {
            "prompt_enhancement": "claude-sonnet",
            "classification": "deepseek-r1",
            "decomposition": "gemini-flash",
            "constructive": "claude-opus",
            "destructive": "claude-opus",
            "systemic": "deepseek-r1",
            "minimalist": "claude-opus",
            "scoring": "claude-opus",
            "stress_testing": "claude-opus",
            "synthesis": "claude-opus"
        },
        "notes": [
            "Phase 2: Moonshot + DeepSeek + Anthropic + Mistral — 4 different training lineages",
            "Sonar Pro scoring: real-time fact-check against current web",
            "Grok 4 stress-testing: 1M token context + X data for adversarial framing",
        ],
    },
    # ── Pre-Mortem ───────────────────────────────────────────────────
    {
        "id": "pre-mortem-budget",
        "name": "Pre-Mortem (Budget)",
        "description": "Prospective failure analysis — budget tier. Failure narrative → root cause → early signals → hardened redesign. Gary Klein (1989) methodology.",
        "primary_id": "deepseek-v3",
        "routing": {
            "prompt_enhancement": "gemma-4-26b",
            "destructive": "deepseek-v3",
            "scoring": "deepseek-v3",
            "synthesis": "deepseek-v3"
        },
        "fallback_routing": {
            "prompt_enhancement": "glm-4-air"
        },
    },
    {
        "id": "pre-mortem-premium",
        "name": "Pre-Mortem (Premium)",
        "description": "Prospective failure analysis — premium tier with Claude Sonnet. Four-phase pre-mortem: failure narrative → root cause → early signals → hardened redesign.",
        "primary_id": "claude-sonnet",
        "routing": {
            "prompt_enhancement": "gemini-flash",
            "destructive": "claude-sonnet",
            "scoring": "claude-sonnet",
            "synthesis": "claude-sonnet"
        },
        "fallback_routing": {
            "prompt_enhancement": "claude-sonnet"
        },
    },
    # ── Bayesian ─────────────────────────────────────────────────────
    {
        "id": "bayesian-budget",
        "name": "Bayesian (Budget)",
        "description": "Four-phase Bayesian epistemology — budget tier. Prior elicitation → likelihood assessment → posterior update → sensitivity analysis. Jaynes (2003) methodology.",
        "primary_id": "deepseek-v3",
        "routing": {
            "prompt_enhancement": "gemma-4-26b",
            "constructive": "deepseek-v3",
            "destructive": "deepseek-v3",
            "scoring": "deepseek-v3",
            "synthesis": "deepseek-v3"
        },
        "fallback_routing": {
            "prompt_enhancement": "glm-4-air"
        },
    },
    {
        "id": "bayesian-premium",
        "name": "Bayesian (Premium)",
        "description": "Four-phase Bayesian epistemology — premium tier with Claude Sonnet. Prior elicitation → likelihood assessment → posterior update → sensitivity analysis.",
        "primary_id": "claude-sonnet",
        "routing": {
            "prompt_enhancement": "gemini-flash",
            "constructive": "claude-sonnet",
            "destructive": "claude-sonnet",
            "scoring": "claude-sonnet",
            "synthesis": "claude-sonnet"
        },
        "fallback_routing": {
            "prompt_enhancement": "claude-sonnet"
        },
    },
    # ── Dialectical ──────────────────────────────────────────────────
    {
        "id": "dialectical-budget",
        "name": "Dialectical (Budget)",
        "description": "Hegelian dialectic — budget tier. Thesis → antithesis → contradiction analysis → Aufhebung. Qualitative transcendence, not compromise.",
        "primary_id": "deepseek-v3",
        "routing": {
            "prompt_enhancement": "gemma-4-26b",
            "constructive": "deepseek-v3",
            "destructive": "deepseek-v3",
            "scoring": "deepseek-v3",
            "synthesis": "deepseek-v3"
        },
        "fallback_routing": {
            "prompt_enhancement": "glm-4-air"
        },
    },
    {
        "id": "dialectical-premium",
        "name": "Dialectical (Premium)",
        "description": "Hegelian dialectic — premium tier with Claude Sonnet. Thesis → antithesis → contradiction analysis → Aufhebung. Genuine philosophical transcendence of the thesis-antithesis.",
        "primary_id": "claude-sonnet",
        "routing": {
            "prompt_enhancement": "gemini-flash",
            "constructive": "claude-sonnet",
            "destructive": "claude-sonnet",
            "scoring": "claude-sonnet",
            "synthesis": "claude-sonnet"
        },
        "fallback_routing": {
            "prompt_enhancement": "claude-sonnet"
        },
    },
    # ── Analogical ───────────────────────────────────────────────────
    {
        "id": "analogical-budget",
        "name": "Analogical (Budget)",
        "description": "Structure-mapping theory — find isomorphic problems solved in other domains, then transfer the solution. Budget tier with DeepSeek V3. Abstraction → domain search → mapping → transfer & adaptation.",
        "primary_id": "deepseek-v3",
        "routing": {
            "prompt_enhancement": "gemma-4-26b",
            "systemic": "deepseek-v3",
            "synthesis": "deepseek-v3"
        },
        "fallback_routing": {
            "prompt_enhancement": "glm-4-air"
        },
    },
    {
        "id": "analogical-premium",
        "name": "Analogical (Premium)",
        "description": "Structure-mapping theory — find isomorphic problems solved in other domains, then transfer the solution. Premium tier with Claude Sonnet. Abstraction → domain search → mapping → transfer & adaptation.",
        "primary_id": "claude-sonnet",
        "routing": {
            "prompt_enhancement": "gemini-flash",
            "systemic": "claude-sonnet",
            "synthesis": "claude-sonnet"
        },
        "fallback_routing": {
            "prompt_enhancement": "claude-sonnet"
        },
    },
    # ── Delphi ───────────────────────────────────────────────────────
    {
        "id": "delphi-budget",
        "name": "Delphi (Budget)",
        "description": "RAND Delphi expert consensus — budget tier. 4 independent experts + anonymous aggregation + revision + dissent. All experts use the same model for cost efficiency.",
        "primary_id": "deepseek-v3",
        "routing": {
            "prompt_enhancement": "gemma-4-26b",
            "expert_1": "deepseek-v3",
            "expert_2": "deepseek-v3",
            "expert_3": "deepseek-v3",
            "expert_4": "deepseek-v3",
            "synthesis": "deepseek-v3"
        },
        "fallback_routing": {
            "prompt_enhancement": "glm-4-air"
        },
    },
    {
        "id": "delphi-premium",
        "name": "Delphi (Premium)",
        "description": "RAND Delphi expert consensus — premium tier with maximum epistemic diversity. 4 experts from different model families (Claude + GPT + Gemini + DeepSeek) for independent perspectives across architectures.",
        "primary_id": "claude-sonnet",
        "routing": {
            "prompt_enhancement": "gemini-flash",
            "expert_1": "claude-sonnet",
            "expert_2": "gpt-5-mini",
            "expert_3": "gemini-flash",
            "expert_4": "deepseek-v3",
            "synthesis": "claude-sonnet"
        },
        "fallback_routing": {
            "prompt_enhancement": "claude-sonnet"
        },
    },
    # ── Chain-of-Verification (CoVe) ─────────────────────────────────
    {
        "id": "cove-budget",
        "name": "Chain-of-Verification (Budget)",
        "description": "Structured fact-checking loop: draft → verify → answer → revise. Budget tier using DeepSeek + Qwen + GLM for cross-lab verification.",
        "primary_id": "deepseek-v3",
        "routing": {
            "prompt_enhancement": "gemma-4-26b",
            "cove_draft": "deepseek-v3",
            "cove_verify": "qwen3-max",
            "cove_answer": "glm-4-air",
            "cove_revise": "deepseek-v3",
            "synthesis": "deepseek-v3"
        },
        "fallback_routing": {
            "prompt_enhancement": "glm-4-air"
        },
    },
    {
        "id": "cove-premium",
        "name": "Chain-of-Verification (Premium)",
        "description": "Structured fact-checking loop: draft → verify → answer → revise. Premium tier with Claude Opus draft, Sonar verification, and cross-lab revision.",
        "primary_id": "claude-opus",
        "routing": {
            "prompt_enhancement": "gemini-flash",
            "cove_draft": "claude-opus",
            "cove_verify": "sonar-pro",
            "cove_answer": "deepseek-r1",
            "cove_revise": "claude-opus",
            "synthesis": "claude-opus"
        },
        "fallback_routing": {
            "prompt_enhancement": "claude-sonnet"
        },
    },
    # ── Skeleton-of-Thought (SoT) ────────────────────────────────────
    {
        "id": "sot-budget",
        "name": "Skeleton-of-Thought (Budget)",
        "description": "Parallel decomposition: skeleton → parallel sub-problem solving → assembly. Budget tier with 3-lab parallel execution for latency reduction.",
        "primary_id": "deepseek-v3",
        "routing": {
            "prompt_enhancement": "gemma-4-26b",
            "sot_skeleton": "deepseek-v3",
            "sot_solve": "qwen3-max",
            "sot_assemble": "deepseek-v3",
            "synthesis": "deepseek-v3"
        },
        "fallback_routing": {
            "prompt_enhancement": "glm-4-air"
        },
    },
    {
        "id": "sot-premium",
        "name": "Skeleton-of-Thought (Premium)",
        "description": "Parallel decomposition: skeleton → parallel sub-problem solving → assembly. Premium tier with Claude skeleton and 4-lab parallel solve.",
        "primary_id": "claude-opus",
        "routing": {
            "prompt_enhancement": "gemini-flash",
            "sot_skeleton": "claude-opus",
            "sot_solve": "kimi-k2-5",
            "sot_assemble": "claude-opus",
            "synthesis": "claude-opus"
        },
        "fallback_routing": {
            "prompt_enhancement": "claude-sonnet"
        },
    },
    # ── Tree-of-Thoughts (ToT) ───────────────────────────────────────
    {
        "id": "tot-budget",
        "name": "Tree-of-Thoughts (Budget)",
        "description": "Reasoning as tree search: generate candidates → evaluate → backtrack. Budget tier with bounded depth and branching for planning problems.",
        "primary_id": "deepseek-v3",
        "routing": {
            "prompt_enhancement": "gemma-4-26b",
            "tot_decompose": "deepseek-v3",
            "tot_generate": "qwen3-max",
            "tot_evaluate": "glm-4-air",
            "tot_backtrack": "deepseek-v3",
            "synthesis": "deepseek-v3"
        },
        "fallback_routing": {
            "prompt_enhancement": "glm-4-air"
        },
    },
    {
        "id": "tot-premium",
        "name": "Tree-of-Thoughts (Premium)",
        "description": "Reasoning as tree search: generate candidates → evaluate → backtrack. Premium tier with Claude decomposition and cross-lab evaluation.",
        "primary_id": "claude-opus",
        "routing": {
            "prompt_enhancement": "gemini-flash",
            "tot_decompose": "claude-opus",
            "tot_generate": "deepseek-r1",
            "tot_evaluate": "sonar-pro",
            "tot_backtrack": "claude-opus",
            "synthesis": "claude-opus"
        },
        "fallback_routing": {
            "prompt_enhancement": "claude-sonnet"
        },
    },
    # ── Program-of-Thoughts (PoT) ────────────────────────────────────
    {
        "id": "pot-budget",
        "name": "Program-of-Thoughts (Budget)",
        "description": "Generate executable code as intermediate reasoning steps. Budget tier with Python code generation and simulated execution for quantitative problems.",
        "primary_id": "deepseek-v3",
        "routing": {
            "prompt_enhancement": "gemma-4-26b",
            "pot_generate": "deepseek-v3",
            "pot_execute": "deepseek-v3",
            "pot_interpret": "deepseek-v3",
            "synthesis": "deepseek-v3"
        },
        "fallback_routing": {
            "prompt_enhancement": "glm-4-air"
        },
    },
    {
        "id": "pot-premium",
        "name": "Program-of-Thoughts (Premium)",
        "description": "Generate executable code as intermediate reasoning steps. Premium tier with GPT-5 code generation and Claude interpretation for maximum accuracy.",
        "primary_id": "gpt-5",
        "routing": {
            "prompt_enhancement": "gemini-flash",
            "pot_generate": "gpt-5",
            "pot_execute": "gpt-5",
            "pot_interpret": "claude-opus",
            "synthesis": "claude-opus"
        },
        "fallback_routing": {
            "prompt_enhancement": "claude-sonnet"
        },
    },
    # ── Self-Discover ────────────────────────────────────────────────
    {
        "id": "self-discover-budget",
        "name": "Self-Discover (Budget)",
        "description": "Dynamic reasoning module composition: the LLM selects and composes reasoning modules per problem. Budget tier with DeepSeek module selection.",
        "primary_id": "deepseek-v3",
        "routing": {
            "prompt_enhancement": "gemma-4-26b",
            "sd_select": "deepseek-v3",
            "sd_adapt": "qwen3-max",
            "sd_implement": "deepseek-v3",
            "synthesis": "deepseek-v3"
        },
        "fallback_routing": {
            "prompt_enhancement": "glm-4-air"
        },
    },
    {
        "id": "self-discover-premium",
        "name": "Self-Discover (Premium)",
        "description": "Dynamic reasoning module composition: the LLM selects and composes reasoning modules per problem. Premium tier with Claude selection and cross-lab implementation.",
        "primary_id": "claude-opus",
        "routing": {
            "prompt_enhancement": "gemini-flash",
            "sd_select": "claude-opus",
            "sd_adapt": "deepseek-r1",
            "sd_implement": "claude-opus",
            "synthesis": "claude-opus"
        },
        "fallback_routing": {
            "prompt_enhancement": "claude-sonnet"
        },
    },
]


PRESETS: dict[str, PipelinePreset] = {
    cfg["id"]: PipelinePreset(
        name=cfg["name"],
        description=cfg["description"],
        primary_id=cfg["primary_id"],
        routing=cfg.get("routing", {}),
        notes=cfg.get("notes", []),
        required_env_vars=cfg.get("required_env_vars", ["OPENROUTER_API_KEY"]),
        fallback_routing=cfg.get("fallback_routing", {}),
    )
    for cfg in _PRESET_CONFIGS
}


def get_preset(name: str) -> PipelinePreset:
    """Get a preset by name. Raises ValueError if not found."""
    if name not in PRESETS:
        available = ", ".join(sorted(PRESETS.keys()))
        raise ValueError(f"Unknown preset: {name!r}. Available: {available}")
    return PRESETS[name]


def is_valid_preset_name(name: str) -> bool:
    """Return True if name is a known preset key."""
    return name in PRESETS


def resolve_preset_name(name: str) -> str:
    """Return name unchanged if valid, else raise ValueError."""
    if name not in PRESETS:
        available = ", ".join(sorted(PRESETS.keys()))
        raise ValueError(f"Unknown preset: {name!r}. Available: {available}")
    return name


def build_custom_router(routing_dict: dict[str, str]) -> ProviderRouter:
    """
    Build a ProviderRouter from a custom role->model_id dict.
    The 'primary' key (required) sets the fallback provider.

    Example:
        build_custom_router({
            "primary":        "claude-sonnet",
            "constructive":   "kimi-k2",
            "scoring":        "sonar-pro",
            "synthesis":      "glm-5",
        })
    """
    if "primary" not in routing_dict:
        raise ValueError("Custom routing must include a 'primary' key.")

    primary_id = routing_dict["primary"]
    rest = {k: v for k, v in routing_dict.items() if k != "primary"}
    return ProviderRouter.from_model_ids(primary_id=primary_id, routing=rest)


def print_presets_summary() -> None:
    """Print a formatted summary of all available presets."""
    from rich.console import Console
    from rich.table import Table
    from rich import box

    console = Console()
    table = Table(title="ARA v2.0 — Available Pipeline Presets", box=box.ROUNDED)
    table.add_column("Preset ID", style="cyan", width=22)
    table.add_column("Name", width=30)
    table.add_column("Primary Model", width=18)
    table.add_column("API Keys Needed", width=40)

    for pid, preset in PRESETS.items():
        missing = preset.missing_keys()
        key_status = (
            "[green]✓ All set[/green]" if not missing
            else f"[red]Missing: {', '.join(missing)}[/red]"
        )
        table.add_row(pid, preset.name, preset.primary_id, key_status)

    console.print(table)
