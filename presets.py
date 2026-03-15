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
from typing import TYPE_CHECKING

from llm import ProviderRouter, build_provider, list_models, _REGISTRY

if TYPE_CHECKING:
    from core.protocol import PhaseConfig


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
})


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
# PRESET DEFINITIONS
# ─────────────────────────────────────────────────────────────────────

PRESETS: dict[str, PipelinePreset] = {

    # ────────────────────────────────────────────────────────────────
    # 1. MAXIMUM QUALITY — best available model per phase
    # ────────────────────────────────────────────────────────────────
    "max-quality": PipelinePreset(
        name="Maximum Quality",
        description=(
            "Best available model per phase. "
            "Perplexity Sonar fact-checks candidates in Phase 3. "
            "GLM-5 and Claude Opus dual-check synthesis. "
            "Cross-ecosystem for maximum epistemic diversity."
        ),
        primary_id="claude-opus",
        routing={
            "classification":  "gemini-flash",      # fast, cheap, reliable
            "decomposition":   "claude-sonnet",     # calibration king
            "constructive":    "kimi-k2-5",         # creative breadth
            "destructive":     "deepseek-v3",       # adversarial RL training
            "systemic":        "deepseek-v3",       # long-range causal chains
            "minimalist":      "ministral-8b",      # token-efficient by design
            "scoring":         "sonar-pro",         # web-grounded fact-checking
            "stress_testing":  "claude-opus",       # specificity + recovery
            "synthesis":       "glm-5",             # #1 Intelligence Index
        },
        notes=[
            "Sonar Pro in scoring phase enables live fact-checking of candidates",
            "GLM-5 for synthesis: top of Artificial Analysis Intelligence Index",
            "Kimi K2.5 for constructive: strongest creative breadth in Chinese OSS",
            "DeepSeek for destructive/systemic: 85K+ adversarial RL environments",
            "Ministral-8b for minimalist: order-of-magnitude fewer tokens by design",
        ],
        required_env_vars=[
            "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "MOONSHOT_API_KEY",
            "DEEPSEEK_API_KEY", "PERPLEXITY_API_KEY", "MISTRAL_API_KEY",
            "ZHIPUAI_API_KEY",
        ],
    ),

    # ────────────────────────────────────────────────────────────────
    # 2. COST EFFICIENCY — pure open-weight Chinese OSS
    # ────────────────────────────────────────────────────────────────
    "cost-efficient": PipelinePreset(
        name="Cost Efficient (OSS)",
        description=(
            "Pure open-weight Chinese ecosystem. "
            "~30x cheaper than GPT-5 per token. "
            "Cross-lab scoring (Qwen evaluates DeepSeek/Kimi/GLM candidates)."
        ),
        primary_id="deepseek-v3",
        routing={
            "classification":  "qwen3-turbo",      # cheapest, fast
            "decomposition":   "deepseek-v3",      # structured + calibrated
            "constructive":    "kimi-k2",           # writing + breadth
            "destructive":     "deepseek-v3",      # adversarial RL
            "systemic":        "deepseek-v3",      # long-range reasoning
            "minimalist":      "glm-4-plus",     # plus = balanced performance
            "scoring":         "qwen3-max",        # cross-lab (≠ DeepSeek/Kimi)
            "stress_testing":  "deepseek-v3",      # adversarial strength
            "synthesis":       "glm-5",            # best open-weight synthesizer
        },
        notes=[
            "All models open-weight — can be self-hosted for zero API cost",
            "DeepSeek ~$0.27/M, Qwen ~$0.03/M, GLM-Air ~$0.05/M",
            "Cross-lab: Qwen scores DeepSeek/Kimi candidates (different lab = different bias)",
            "GLM-5 synthesis: Apache 2.0, top Intelligence Index",
        ],
        required_env_vars=["DEEPSEEK_API_KEY", "DASHSCOPE_API_KEY", "MOONSHOT_API_KEY", "ZHIPUAI_API_KEY"],
    ),

    # ────────────────────────────────────────────────────────────────
    # 3. EU SOVEREIGN — GDPR/AI Act compliant, on-prem deployable
    # ────────────────────────────────────────────────────────────────
    "eu-sovereign": PipelinePreset(
        name="EU Sovereign (Mistral / Apache 2.0)",
        description=(
            "All-Mistral pipeline. Apache 2.0 license throughout. "
            "On-prem deployable — no data leaves your infrastructure. "
            "GDPR and EU AI Act compliant by design."
        ),
        primary_id="mistral-large-3",
        routing={
            "classification":  "ministral-3b",     # lightest, fastest
            "decomposition":   "mistral-large-3",  # most capable
            "constructive":    "mistral-large-3",  # same model, diff temperature
            "destructive":     "mistral-large-3",  # less restricted guardrails
            "systemic":        "mistral-large-3",  # 256K context window
            "minimalist":      "ministral-8b",     # efficient by design
            "scoring":         "mistral-medium",   # intermediate cross-check
            "stress_testing":  "mistral-large-3",  # best available
            "synthesis":       "mistral-large-3",  # #2 OSS LMArena non-reasoning
        },
        notes=[
            "All Apache 2.0 — commercial use, modification, redistribution allowed",
            "On-prem deployment via vLLM on single 8×H100 node",
            "Mistral Large 3: 675B MoE, 41B active, 256K context",
            "Trade-off: sacrifices cross-ecosystem epistemic diversity",
            "Recommended for: HSBC-style enterprise, regulated industries, public sector",
        ],
        required_env_vars=["MISTRAL_API_KEY"],
    ),

    # ────────────────────────────────────────────────────────────────
    # 4. MAXIMUM EPISTEMIC DIVERSITY — one model per lab per perspective
    # ────────────────────────────────────────────────────────────────
    "epistemic-diversity": PipelinePreset(
        name="Maximum Epistemic Diversity",
        description=(
            "One model per lab in Phase 2. "
            "Chinese + Western + EU + real-time coverage. "
            "Perplexity for grounded critique. Grok for real-time synthesis."
        ),
        primary_id="claude-sonnet",
        routing={
            "classification":  "gemini-flash",     # Google — fast
            "decomposition":   "claude-sonnet",    # Anthropic — calibration
            "constructive":    "kimi-k2-5",        # Moonshot — creative
            "destructive":     "deepseek-v3",      # DeepSeek — adversarial RL
            "systemic":        "claude-opus",      # Anthropic — causal chains
            "minimalist":      "mistral-large-3",  # Mistral EU — concise
            "scoring":         "sonar-pro",        # Perplexity — web-grounded
            "stress_testing":  "grok-4",           # xAI — real-time adversarial
            "synthesis":       "gpt-5",            # OpenAI — broad synthesis
        },
        notes=[
            "Phase 2: Moonshot + DeepSeek + Anthropic + Mistral — 4 different training lineages",
            "Sonar Pro scoring: real-time fact-check against current web",
            "Grok 4 stress-testing: 1M token context + X data for adversarial framing",
            "GPT-5 synthesis: maximum breadth across diverse inputs",
            "Most expensive preset — justified for high-stakes irreversible decisions",
        ],
        required_env_vars=[
            "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "MOONSHOT_API_KEY",
            "DEEPSEEK_API_KEY", "MISTRAL_API_KEY", "PERPLEXITY_API_KEY",
            "XAI_API_KEY", "OPENAI_API_KEY",
        ],
        # Auto-fallback → claude-sonnet (primary). Explicit overrides push to claude-opus
        # for the roles where quality matters most (scoring, stress, synthesis).
        fallback_routing={
            "scoring":         "claude-opus",      # sonar-pro fails → best ungrounded scorer
            "stress_testing":  "claude-opus",      # grok-4 fails → best adversarial
            "synthesis":       "claude-opus",      # gpt-5 fails → top-tier synthesis
        },
    ),

    # ────────────────────────────────────────────────────────────────
    # 5. WESTERN ONLY — no Chinese models
    # ────────────────────────────────────────────────────────────────
    "western-only": PipelinePreset(
        name="Western Only",
        description=(
            "Anthropic + OpenAI + Google + Mistral. "
            "No Chinese models. Suitable for US/EU data-sensitive contexts."
        ),
        primary_id="claude-sonnet",
        routing={
            "classification":  "gemini-flash",
            "decomposition":   "claude-sonnet",
            "constructive":    "gemini-pro",
            "destructive":     "claude-opus",
            "systemic":        "gpt-5",
            "minimalist":      "ministral-8b",
            "scoring":         "gpt-5",
            "stress_testing":  "claude-opus",
            "synthesis":       "claude-opus",
        },
        notes=[
            "Mistral included as EU-based Western alternative",
            "No Grok — xAI/X data integration not always desirable",
            "Use 'western-plus-grok' preset if real-time X data is valuable",
        ],
        required_env_vars=["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY", "MISTRAL_API_KEY"],
    ),

    # ────────────────────────────────────────────────────────────────
    # 6. RESEARCH — grounded throughout, Perplexity-heavy
    # ────────────────────────────────────────────────────────────────
    "research": PipelinePreset(
        name="Research / Evidence-Grounded",
        description=(
            "Perplexity Sonar grounded models dominate. "
            "Every phase benefits from web-verified evidence. "
            "Ideal for empirical questions, current events, market analysis."
        ),
        primary_id="sonar-pro",
        routing={
            "classification":  "sonar",                # fast search classification
            "decomposition":   "claude-sonnet",        # calibrated structure
            "constructive":    "sonar-deep-research",  # deep research for ideas
            "destructive":     "deepseek-v3",          # adversarial (no search bias)
            "systemic":        "sonar-deep-research",  # evidence-grounded systemic
            "minimalist":      "sonar",                # fast, cited
            "scoring":         "sonar-pro",            # fact-checks all candidates
            "stress_testing":  "grok-4",               # real-time adversarial
            "synthesis":       "sonar-deep-research",  # fully grounded synthesis
        },
        notes=[
            "WARNING: Sonar models add search latency (~2-5x slower)",
            "Each Sonar call includes citations — synthesis is verifiable",
            "Deep Research performs 20-30 web searches per call",
            "Best for: market research, scientific questions, current events",
            "Not ideal for: pure reasoning/math/logic problems",
        ],
        required_env_vars=["PERPLEXITY_API_KEY", "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY", "XAI_API_KEY"],
        # sonar-pro is primary — it has no auto-fallback. Sonar models produce prose+citations,
        # not clean JSON. All Sonar-based roles need an explicit JSON-capable fallback.
        fallback_routing={
            "classification":  "claude-sonnet",    # sonar citation output → JSON-safe
            "constructive":    "claude-sonnet",    # sonar-deep-research fails → JSON-safe
            "systemic":        "claude-sonnet",    # sonar-deep-research fails → JSON-safe
            "minimalist":      "claude-sonnet",    # sonar fails → reliable JSON
            "scoring":         "claude-sonnet",    # sonar-pro = primary → explicit fallback
            "stress_testing":  "deepseek-v3",      # grok-4 fails → adversarial fallback
            "synthesis":       "claude-sonnet",    # sonar-deep-research fails → JSON prose
        },
    ),

    # ────────────────────────────────────────────────────────────────
    # 7. DEBATE / MULTI-AGENT — Two models produce solutions, third judges
    # ────────────────────────────────────────────────────────────────
    "debate": PipelinePreset(
        name="Debate / Multi-Agent",
        description=(
            "Two models (A & B) generate independent solutions. "
            "A third model (Judge) evaluates and selects the best. "
            "Ideal for complex decisions requiring multiple perspectives."
        ),
        primary_id="claude-sonnet",
        routing={
            "classification":  "gemini-flash",     # fast classification
            "decomposition":   "claude-sonnet",    # balanced structure
            "constructive":    "gpt-5",            # Model A: constructive solution
            "destructive":     "claude-opus",      # Model B: critical solution
            "systemic":        "claude-opus",      # Judge: evaluates both
            "minimalist":      "claude-sonnet",    # Judge: selects best
            "scoring":         "claude-opus",      # Judge: scores both
            "stress_testing":  "claude-opus",      # Judge: stress tests winner
            "synthesis":       "claude-sonnet",    # Final synthesis
        },
        notes=[
            "Model A (GPT-5) and Model B (Claude Opus) generate competing solutions",
            "Claude Opus acts as Judge throughout phases 2-4",
            "Best for: strategic decisions, policy questions, architectural choices",
            "Higher cost but produces more robust solutions through competition",
        ],
        required_env_vars=["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY"],
        fallback_routing={
            "constructive": "claude-opus",         # gpt-5 fails → best available Model A
        },
    ),

    # ────────────────────────────────────────────────────────────────
    # 8. EVOLUTIONARY — Generate N solutions, critique, select best, refine
    # ────────────────────────────────────────────────────────────────
    "evolutionary": PipelinePreset(
        name="Evolutionary Loop",
        description=(
            "Generates multiple solutions, critiques each, selects best, and refines. "
            "Repeats for up to 5 iterations or until score > 8/10. "
            "Genetic optimization for complex problems."
        ),
        primary_id="claude-opus",
        routing={
            "classification":  "gemini-flash",     # fast classification
            "decomposition":   "claude-sonnet",    # structure
            "constructive":    "claude-opus",      # Generator: produce solutions
            "destructive":     "claude-opus",      # Critic: critique solutions
            "systemic":        "claude-opus",      # Judge: score solutions
            "minimalist":      "claude-sonnet",    # Refiner: simplify best solution
            "scoring":         "claude-opus",      # Judge: evaluate refinement
            "stress_testing":  "claude-opus",      # Stress test final
            "synthesis":       "claude-opus",      # Final output
        },
        notes=[
            "Phase 2 generates 4 candidate solutions in parallel",
            "Phase 3 critiques and scores all candidates",
            "Phase 4 stress tests the best candidate",
            "Phase 5 can trigger refinement loop (max 5 iterations)",
            "Stop conditions: score > 8/10 OR improvement < threshold OR max iterations",
            "Best for: optimization problems, design challenges, complex reasoning",
            "Higher cost but produces optimized solutions through iteration",
        ],
        required_env_vars=["ANTHROPIC_API_KEY", "GOOGLE_API_KEY"],
    ),

    # ────────────────────────────────────────────────────────────────
    # 9. SINGLE MODEL — testing / minimal setup
    # ────────────────────────────────────────────────────────────────
    "claude-only": PipelinePreset(
        name="Claude Only",
        description=(
            "All phases run on Claude Sonnet. "
            "Minimal setup — one API key required. "
            "Best for getting started or when only Anthropic access is available."
        ),
        primary_id="claude-sonnet",
        routing={},
        notes=[
            "Single-provider preset — no cross-lab diversity",
            "Reliable JSON output — no parsing surprises",
            "Best for: quick analysis, testing, single-key environments",
        ],
        required_env_vars=["ANTHROPIC_API_KEY"],
    ),

    "deepseek-only": PipelinePreset(
        name="DeepSeek Only",
        description=(
            "All phases run on DeepSeek V3. "
            "Cost-efficient Chinese open-source model. "
            "Requires only DEEPSEEK_API_KEY."
        ),
        primary_id="deepseek-v3",
        routing={},
        notes=[
            "Single-provider preset — no cross-lab diversity",
            "JSON parsing may be less reliable than Claude",
            "Best for: cost-sensitive runs, testing DeepSeek integration",
            "WARNING: JSON output quality is unverified — use --sequential if issues arise",
        ],
        required_env_vars=["DEEPSEEK_API_KEY"],
    ),

    # ────────────────────────────────────────────────────────────────
    # BUDGET TIERS — Cross-lab cheap (DeepSeek + Qwen [+ GLM])
    # ────────────────────────────────────────────────────────────────

    "basic-budget": PipelinePreset(
        name="Basic — Cost Efficient",
        description=(
            "Standard 6-phase pipeline using cheapest cross-lab models. "
            "DeepSeek (reasoning) + Qwen (cross-lab scoring). "
            "2 API keys. Pennies per run."
        ),
        primary_id="deepseek-v3",
        routing={
            "classification":  "qwen3-turbo",   # cheapest, fast
            "decomposition":   "deepseek-v3",   # calibrated structure
            "constructive":    "deepseek-v3",   # RL-trained generation
            "destructive":     "qwen3-max",     # cross-lab adversarial
            "systemic":        "deepseek-v3",   # long-range causal
            "minimalist":      "qwen3-turbo",   # cheap refiner
            "scoring":         "qwen3-max",     # different lab = unbiased scoring
            "stress_testing":  "deepseek-v3",
            "synthesis":       "deepseek-v3",
        },
        notes=[
            "DeepSeek + Qwen: different labs, different training = genuine diversity",
            "qwen3-turbo at ~$0.03/M is the cheapest capable model in registry",
            "Full run estimated at <$0.02 total",
        ],
        required_env_vars=["DEEPSEEK_API_KEY", "DASHSCOPE_API_KEY"],
    ),

    "evolutionary-budget": PipelinePreset(
        name="Evolutionary — Cost Efficient",
        description=(
            "Iterative refinement loop using cheap cross-lab models. "
            "DeepSeek generates, Qwen critiques (cross-lab avoids echo chamber). "
            "2 API keys."
        ),
        primary_id="deepseek-v3",
        routing={
            "classification":  "qwen3-turbo",   # cheap
            "decomposition":   "deepseek-v3",
            "constructive":    "deepseek-v3",   # Generator: RL-trained breadth
            "destructive":     "qwen3-max",     # Critic: MUST be cross-lab
            "systemic":        "qwen3-max",     # Judge: cross-lab impartiality
            "minimalist":      "qwen3-turbo",   # Refiner: cheap simplification
            "scoring":         "qwen3-max",     # Score from different lab
            "stress_testing":  "deepseek-v3",
            "synthesis":       "deepseek-v3",
        },
        notes=[
            "Critical: constructive=DeepSeek, destructive=Qwen — different labs",
            "Same-lab generator+critic causes echo chamber convergence in the loop",
            "For harder problems: swap destructive to deepseek-r1 (reasoning critic)",
        ],
        required_env_vars=["DEEPSEEK_API_KEY", "DASHSCOPE_API_KEY"],
    ),

    "debate-budget": PipelinePreset(
        name="Debate — Cost Efficient",
        description=(
            "Adversarial debate with 3 cheap cross-lab models. "
            "DeepSeek (Model A) vs Qwen (Model B), judged by GLM. "
            "3 different training lineages, 3 API keys."
        ),
        primary_id="deepseek-v3",
        routing={
            "classification":  "qwen3-turbo",   # cheap
            "decomposition":   "deepseek-v3",
            "constructive":    "deepseek-v3",   # Model A
            "destructive":     "qwen3-max",     # Model B — cross-lab adversary
            "systemic":        "glm-4-air",     # Judge — 3rd neutral lab
            "minimalist":      "qwen3-turbo",
            "scoring":         "glm-4-air",     # Neutral judge scores both sides
            "stress_testing":  "deepseek-v3",
            "synthesis":       "deepseek-v3",
        },
        notes=[
            "3 labs: DeepSeek / Qwen (Alibaba) / GLM (ZhipuAI) — genuine adversarial dynamic",
            "GLM as neutral judge: not invested in either A or B training paradigm",
            "glm-4-air at ~$0.05/M is cheapest viable judge in registry",
        ],
        required_env_vars=["DEEPSEEK_API_KEY", "DASHSCOPE_API_KEY", "ZHIPUAI_API_KEY"],
    ),

    # ────────────────────────────────────────────────────────────────
    # MID-TIER PRESETS — Balanced quality/cost for each method
    # ────────────────────────────────────────────────────────────────

    "debate-balanced": PipelinePreset(
        name="Debate — Balanced",
        description=(
            "Adversarial debate with balanced cost/quality. "
            "Claude Sonnet (Model A) vs DeepSeek (Model B), Opus judges. "
            "Top-tier reasoning without premium pricing."
        ),
        primary_id="claude-sonnet",
        routing={
            "classification":  "claude-sonnet",
            "decomposition":   "claude-sonnet",
            "constructive":    "claude-sonnet",    # Model A: quality reasoning
            "destructive":     "deepseek-v3",      # Model B: adversarial diversity
            "systemic":        "claude-opus",      # Judge: best evaluation
            "minimalist":      "claude-sonnet",
            "scoring":         "claude-opus",      # Judge: confident scoring
            "stress_testing":  "claude-opus",
            "synthesis":       "claude-sonnet",
        },
        notes=[
            "Cross-lab (Anthropic + DeepSeek) for genuine adversarial dynamic",
            "Claude Opus judges both sides: highest quality evaluation",
            "Cost: 2.5x budget tier, but 40% cheaper than premium",
            "Best for: medium-stakes decisions, balanced quality/cost",
        ],
        required_env_vars=["ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY"],
        fallback_routing={
            "constructive": "claude-opus",
        },
    ),

    "evolutionary-balanced": PipelinePreset(
        name="Evolutionary — Balanced",
        description=(
            "Iterative refinement with balanced cost/quality. "
            "Claude Sonnet drives optimization, Opus evaluates. "
            "Genetic algorithm without premium-only pricing."
        ),
        primary_id="claude-sonnet",
        routing={
            "classification":  "claude-sonnet",
            "decomposition":   "claude-sonnet",
            "constructive":    "claude-sonnet",    # Generator: capable creativity
            "destructive":     "deepseek-v3",      # Critic: cross-lab perspective
            "systemic":        "claude-opus",      # Judge: best scorer
            "minimalist":      "claude-sonnet",    # Refiner: efficient simplification
            "scoring":         "claude-opus",      # Judge: confident refinement
            "stress_testing":  "claude-opus",
            "synthesis":       "claude-sonnet",
        },
        notes=[
            "Generator + Critic from different labs avoids echo chamber",
            "Claude Opus judges all scoring/stress phases for highest quality",
            "Supports 5-iteration refinement loop for complex problems",
            "Cost: 2.5x budget tier, competitive with premium",
            "Best for: optimization problems with medium complexity",
        ],
        required_env_vars=["ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY"],
    ),

    "research-balanced": PipelinePreset(
        name="Research — Balanced",
        description=(
            "Evidence-grounded analysis with balanced cost/quality. "
            "Sonar handles search-heavy phases, Claude refines. "
            "Fact-checked synthesis without Sonar Deep Research latency."
        ),
        primary_id="sonar",
        routing={
            "classification":  "sonar",             # fast search classification
            "decomposition":   "claude-sonnet",     # calibrated structure
            "constructive":    "sonar-pro",         # grounded ideas
            "destructive":     "deepseek-v3",       # adversarial (no search bias)
            "systemic":        "claude-sonnet",     # systemic without search latency
            "minimalist":      "sonar",             # fast, cited minimalist take
            "scoring":         "claude-sonnet",     # evaluate candidate quality
            "stress_testing":  "deepseek-v3",       # adversarial testing
            "synthesis":       "sonar-pro",         # fully grounded synthesis with citations
        },
        notes=[
            "Balanced: Sonar for search-critical phases, Claude for reasoning",
            "Avoids Deep Research latency (20-30 web searches) in every phase",
            "Synthesis is fully grounded with web citations",
            "Cost: 2-3x cheaper than full Sonar pipeline",
            "Best for: current events, market research, hybrid fact/reasoning questions",
        ],
        required_env_vars=["PERPLEXITY_API_KEY", "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY"],
        fallback_routing={
            "classification":  "claude-sonnet",
            "constructive":    "claude-sonnet",
            "minimalist":      "claude-sonnet",
            "stress_testing":  "claude-sonnet",
            "synthesis":       "claude-sonnet",
        },
    ),

    "research-budget": PipelinePreset(
        name="Research — Cost Efficient",
        description=(
            "Evidence-grounded analysis with minimal cost. "
            "Sonar for search phases only, DeepSeek for reasoning. "
            "Single web-search provider with cross-lab diversity."
        ),
        primary_id="sonar",
        routing={
            "classification":  "sonar",             # fast search classification
            "decomposition":   "deepseek-v3",       # cost-efficient structure
            "constructive":    "deepseek-v3",       # cost-efficient generation
            "destructive":     "qwen3-max",         # cross-lab adversarial
            "systemic":        "deepseek-v3",       # long-range reasoning
            "minimalist":      "qwen3-turbo",       # cheapest refiner
            "scoring":         "qwen3-max",         # cross-lab scoring
            "stress_testing":  "deepseek-v3",       # adversarial testing
            "synthesis":       "sonar",             # basic grounded synthesis
        },
        notes=[
            "Sonar only in classification + synthesis for minimum search cost",
            "DeepSeek + Qwen for all reasoning: different labs, different biases",
            "Trade-off: less search depth than balanced/premium tiers",
            "Cost: ~3x cheaper than balanced research tier",
            "Best for: cost-sensitive research, fact-checking without deep dives",
        ],
        required_env_vars=["PERPLEXITY_API_KEY", "DEEPSEEK_API_KEY", "DASHSCOPE_API_KEY"],
        fallback_routing={
            "classification":  "deepseek-v3",
            "synthesis":       "deepseek-v3",
        },
    ),

    # ─────────────────────────────────────────────────────────────────
    # B1: PRE-MORTEM ANALYSIS
    # ─────────────────────────────────────────────────────────────────
    "pre-mortem-budget": PipelinePreset(
        name="Pre-Mortem (Budget)",
        description=(
            "Prospective failure analysis — budget tier. "
            "Failure narrative → root cause → early signals → hardened redesign. "
            "Gary Klein (1989) methodology."
        ),
        primary_id="deepseek-v3",
        routing={
            "destructive":    "deepseek-v3",
            "scoring":        "deepseek-v3",
            "synthesis":      "deepseek-v3",
        },
        required_env_vars=["DEEPSEEK_API_KEY"],
    ),
    "pre-mortem-premium": PipelinePreset(
        name="Pre-Mortem (Premium)",
        description=(
            "Prospective failure analysis — premium tier with Claude Sonnet. "
            "Four-phase pre-mortem: failure narrative → root cause → early signals → hardened redesign."
        ),
        primary_id="claude-sonnet",
        routing={
            "destructive":    "claude-sonnet",
            "scoring":        "claude-sonnet",
            "synthesis":      "claude-sonnet",
        },
        required_env_vars=["ANTHROPIC_API_KEY"],
    ),

    # ─────────────────────────────────────────────────────────────────
    # B2: BAYESIAN REASONING
    # ─────────────────────────────────────────────────────────────────
    "bayesian-budget": PipelinePreset(
        name="Bayesian Reasoning (Budget)",
        description=(
            "Four-phase Bayesian epistemology — budget tier. "
            "Prior elicitation → likelihood assessment → posterior update → sensitivity analysis. "
            "Jaynes (2003) methodology."
        ),
        primary_id="deepseek-v3",
        routing={
            "constructive":   "deepseek-v3",
            "destructive":    "deepseek-v3",
            "scoring":        "deepseek-v3",
            "synthesis":      "deepseek-v3",
        },
        required_env_vars=["DEEPSEEK_API_KEY"],
    ),
    "bayesian-premium": PipelinePreset(
        name="Bayesian Reasoning (Premium)",
        description=(
            "Four-phase Bayesian epistemology — premium tier with Claude Sonnet. "
            "Prior elicitation → likelihood assessment → posterior update → sensitivity analysis."
        ),
        primary_id="claude-sonnet",
        routing={
            "constructive":   "claude-sonnet",
            "destructive":    "claude-sonnet",
            "scoring":        "claude-sonnet",
            "synthesis":      "claude-sonnet",
        },
        required_env_vars=["ANTHROPIC_API_KEY"],
    ),

    # ─────────────────────────────────────────────────────────────────
    # B3: DIALECTICAL REASONING
    # ─────────────────────────────────────────────────────────────────
    "dialectical-budget": PipelinePreset(
        name="Dialectical Reasoning (Budget)",
        description=(
            "Hegelian dialectic — budget tier. "
            "Thesis → antithesis → contradiction analysis → Aufhebung. "
            "Qualitative transcendence, not compromise."
        ),
        primary_id="deepseek-v3",
        routing={
            "constructive":   "deepseek-v3",
            "destructive":    "deepseek-v3",
            "scoring":        "deepseek-v3",
            "synthesis":      "deepseek-v3",
        },
        required_env_vars=["DEEPSEEK_API_KEY"],
    ),
    "dialectical-premium": PipelinePreset(
        name="Dialectical Reasoning (Premium)",
        description=(
            "Hegelian dialectic — premium tier with Claude Sonnet. "
            "Thesis → antithesis → contradiction analysis → Aufhebung. "
            "Genuine philosophical transcendence of the thesis-antithesis."
        ),
        primary_id="claude-sonnet",
        routing={
            "constructive":   "claude-sonnet",
            "destructive":    "claude-sonnet",
            "scoring":        "claude-sonnet",
            "synthesis":      "claude-sonnet",
        },
        required_env_vars=["ANTHROPIC_API_KEY"],
    ),
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
    Build a ProviderRouter from a custom role→model_id dict.
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
