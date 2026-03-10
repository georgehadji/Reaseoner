"""
ARA Pipeline - Phase Prompts
Each prompt is a self-contained inference unit with explicit output format.
"""

from __future__ import annotations

import json
from models import PipelineState, PerspectiveType, ScenarioType


# ─────────────────────────────────────────────────────────────────────
# LANGUAGE DETECTION
# ─────────────────────────────────────────────────────────────────────

def detect_language(text: str) -> str:
    """Detect language from text. Returns language code."""
    # Simple heuristic: check for Greek, Cyrillic, Arabic, Chinese characters
    if any('\u0370' <= c <= '\u03ff' for c in text):  # Greek
        return "Greek"
    if any('\u0400' <= c <= '\u04ff' for c in text):  # Cyrillic
        return "Russian"
    if any('\u0600' <= c <= '\u06ff' for c in text):  # Arabic
        return "Arabic"
    if any('\u4e00' <= c <= '\u9fff' for c in text):  # Chinese
        return "Chinese"
    if any('\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff' for c in text):  # Japanese
        return "Japanese"
    if any('\uac00' <= c <= '\ud7af' for c in text):  # Korean
        return "Korean"
    # Default to English
    return "English"


LANGUAGE_INSTRUCTIONS = {
    "English": "Respond in English.",
    "Greek": "Απάντησε στα Ελληνικά.",
    "Russian": "Ответьте на русском языке.",
    "Arabic": "أجب بالعربية.",
    "Chinese": "用中文回答。",
    "Japanese": "日本語で回答してください。",
    "Korean": "한국어로 답변해 주세요.",
}


def get_language_instruction(language: str) -> str:
    """Get the language instruction for prompts."""
    return LANGUAGE_INSTRUCTIONS.get(language, LANGUAGE_INSTRUCTIONS["English"])


# ─────────────────────────────────────────────
# PHASE 0 — TASK CLASSIFICATION
# ─────────────────────────────────────────────

CLASSIFICATION_SYSTEM = """You are a task classification expert.
Classify problems with precision. Output ONLY valid JSON. No prose, no markdown fences."""

def classification_prompt(problem: str) -> str:
    language = detect_language(problem)
    lang_instruction = get_language_instruction(language)
    
    return f"""{lang_instruction}

Classify this problem into ONE primary type:
- analytical: logic, math, cause-effect, structured reasoning
- strategic: planning, decisions, trade-offs, multi-stakeholder
- creative: generation, design, ideation, open-ended
- technical: code, engineering, scientific methods
- hybrid: significant mix of the above types

Problem:
{problem}

Output JSON:
{{
  "task_type": "<type>",
  "rationale": "<2-3 sentences explaining why>",
  "key_challenges": ["<challenge1>", "<challenge2>", "<challenge3>"],
  "language": "{language}"
}}"""


# ─────────────────────────────────────────────
# PHASE 1 — PROBLEM DECOMPOSITION
# ─────────────────────────────────────────────

DECOMPOSITION_SYSTEM = """You are an expert problem analyst.
Decompose problems with precision. Label every assumption honestly.
Output ONLY valid JSON. No markdown fences."""

def decomposition_prompt(state: PipelineState) -> str:
    lang_instruction = get_language_instruction(state.language)
    return f"""{lang_instruction}

Problem: {state.problem}
Task type: {state.task_type.value if state.task_type else "unknown"}
Key challenges: {state.task_type_rationale}

Decompose this problem. Be rigorous.

Output JSON:
{{
  "sub_problems": [
    {{
      "id": "SP1",
      "description": "<atomic sub-problem>",
      "inputs": ["<input1>"],
      "outputs": ["<output1>"],
      "constraints": ["<constraint1>"]
    }}
  ],
  "assumptions": [
    {{
      "text": "<assumption>",
      "label": "VERIFIED|HYPOTHESIS|UNKNOWN",
      "rationale": "<why this label>"
    }}
  ],
  "failure_modes": [
    "<specific failure mode that makes this problem hard>"
  ]
}}

Rules:
- Maximum 5 sub-problems
- Every implicit assumption must be surfaced and labeled
- Failure modes must be specific, not generic"""


# ─────────────────────────────────────────────
# PHASE 2 — MULTI-PERSPECTIVE ANALYSIS
# ─────────────────────────────────────────────

PERSPECTIVE_SYSTEMS: dict[PerspectiveType, str] = {
    PerspectiveType.CONSTRUCTIVE: """You reason constructively.
Find the strongest possible solution. Focus on what works and why.
Be specific, evidence-grounded, and actionable.
Output ONLY valid JSON.""",

    PerspectiveType.DESTRUCTIVE: """You are a rigorous critic and adversary.
Your sole goal: find every way this problem resists solution.
Attack assumptions, find edge cases, expose hidden failure modes.
Do NOT propose solutions — only identify weaknesses.
Output ONLY valid JSON.""",

    PerspectiveType.SYSTEMIC: """You think in systems.
Identify second and third-order effects. How does any solution interact
with the broader system? What unintended consequences emerge?
Focus on emergent properties and feedback loops.
Output ONLY valid JSON.""",

    PerspectiveType.MINIMALIST: """You apply Occam's Razor aggressively.
Find the simplest solution that addresses ≥80% of the problem.
Cut complexity ruthlessly. What is truly necessary vs what is merely comfortable?
Output ONLY valid JSON.""",
}

def perspective_prompt(state: PipelineState, perspective: PerspectiveType) -> str:
    lang_instruction = get_language_instruction(state.language)
    ctx = state.to_context_dict()
    return f"""{lang_instruction}

Problem: {state.problem}

Sub-problems identified:
{json.dumps(ctx["sub_problems"], indent=2)}

Assumptions:
{json.dumps(ctx["assumptions"], indent=2)}

Analyze from your perspective. Be specific and non-obvious.

Output JSON:
{{
  "perspective": "{perspective.value}",
  "core_analysis": "<your full analysis — 200-400 words>",
  "key_insights": [
    "<non-obvious insight 1>",
    "<non-obvious insight 2>",
    "<non-obvious insight 3>"
  ],
  "critical_finding": "<the single most important thing from your perspective>"
}}"""


# ─────────────────────────────────────────────
# PHASE 3 — CRITIQUE & SCORING
# ─────────────────────────────────────────────

CRITIQUE_SYSTEM = """You are an objective evaluator with high epistemic standards.
Score solutions honestly. Penalize vagueness and unsupported claims.
Output ONLY valid JSON."""

def critique_prompt(state: PipelineState) -> str:
    lang_instruction = get_language_instruction(state.language)
    candidates_json = json.dumps(
        [
            {
                "perspective": c.perspective.value,
                "content": c.content,
                "key_insights": c.key_insights,
            }
            for c in state.candidates
        ],
        indent=2,
    )

    return f"""{lang_instruction}

Problem: {state.problem}

Evaluate these {len(state.candidates)} candidate analyses:

{candidates_json}

For each candidate, score 0-10 on:
- logical_consistency: is the reasoning internally sound?
- evidence_support: are claims verified vs assumed?
- failure_resilience: does it address failure modes?
- feasibility: is it actually implementable?

Also identify:
- bias_flags: list cognitive biases present
- steel_man: strongest possible argument IN FAVOR of the weakest candidate

Output JSON:
{{
  "scores": [
    {{
      "perspective": "<perspective_value>",
      "logical_consistency": <0-10>,
      "evidence_support": <0-10>,
      "failure_resilience": <0-10>,
      "feasibility": <0-10>,
      "bias_flags": ["<bias1>", "<bias2>"],
      "steel_man": "<strongest argument for this perspective>"
    }}
  ],
  "overall_bias_detected": "<systemic bias across all candidates>",
  "pruning_recommendation": ["<keep_perspective1>", "<keep_perspective2>"]
}}"""


# ─────────────────────────────────────────────
# PHASE 4 — STRESS TESTING
# ─────────────────────────────────────────────

STRESS_SYSTEM = """You simulate adversarial conditions and stress scenarios.
Be specific about failure mechanics. Do not be optimistic.
Output ONLY valid JSON."""

def stress_test_prompt(state: PipelineState) -> str:
    lang_instruction = get_language_instruction(state.language)
    ctx = state.to_context_dict()
    top = [c for c in state.candidates if c.perspective.value in
           [s.perspective.value for s in sorted(state.scores, key=lambda x: x.total, reverse=True)[:2]]]

    solution_summary = json.dumps(
        [{"perspective": c.perspective.value, "content": c.content[:600]} for c in top],
        indent=2
    )

    return f"""{lang_instruction}

Problem: {state.problem}

Best candidate solutions:
{solution_summary}

Test these solutions under 3 scenarios:

1. OPTIMAL: All assumptions hold, resources available, cooperation achieved
2. CONSTRAINT_VIOLATION: Core assumptions break. Resources constrained. Partial data.
3. ADVERSARIAL: An intelligent actor actively works to make this solution fail.

For each scenario provide:
- survival_rate: 0.0-1.0 (fraction of solution value that survives)
- failure_mode: exactly what breaks and why
- recovery_path: concrete steps to recover

Output JSON:
{{
  "stress_tests": [
    {{
      "scenario": "optimal|constraint_violation|adversarial",
      "survival_rate": <0.0-1.0>,
      "failure_mode": "<specific failure mechanism>",
      "recovery_path": "<concrete recovery steps>"
    }}
  ],
  "robustness_verdict": "<overall assessment of solution robustness>"
}}"""


# ─────────────────────────────────────────────
# PHASE 5 — SYNTHESIS
# ─────────────────────────────────────────────

SYNTHESIS_SYSTEM = """You are a master synthesizer with high epistemic standards.
Integrate insights honestly. Label every claim. Acknowledge uncertainty.
Produce output that is more valuable than the sum of its parts."""

_METHOD_SYNTHESIS_HINTS: dict[str, str] = {
    "debate":              "Frame your synthesis as a judge's ruling. Acknowledge both sides before declaring the verdict.",
    "debate-budget":       "Frame your synthesis as a judge's ruling. Acknowledge both sides before declaring the verdict.",
    "evolutionary":        "Frame your synthesis as the optimized solution that survived selection pressure. Highlight what was discarded and why.",
    "evolutionary-budget": "Frame your synthesis as the optimized solution that survived selection pressure. Highlight what was discarded and why.",
    "research":            "Frame your synthesis as an evidence report. Ground every claim in the reviewed evidence. Distinguish VERIFIED facts from hypotheses.",
}


def synthesis_prompt(state: PipelineState, preset_name: str | None = None) -> str:
    lang_instruction = get_language_instruction(state.language)
    ctx = state.to_context_dict()
    method_hint = _METHOD_SYNTHESIS_HINTS.get(preset_name or "", "")
    method_directive = f"\nMethod directive: {method_hint}" if method_hint else ""
    return f"""{lang_instruction}

Problem: {state.problem}
Task type: {ctx["task_type"]}

All analyses:
{json.dumps(ctx["candidates"], indent=2)}

Critique scores:
{json.dumps(ctx["scores"], indent=2)}

Stress test results:
{json.dumps(ctx["stress_results"], indent=2)}

Synthesize a final solution that:
1. Survives all three stress scenarios
2. Integrates constructive AND destructive insights
3. Is simpler than the naive first approach
4. Labels every major claim as VERIFIED/HYPOTHESIS/UNKNOWN{method_directive}

Use this exact format — two parts:

[SOLUTION]
Write 400-600 words of plain prose. Direct, clear, actionable.
No JSON, no code blocks inside this section.
[/SOLUTION]

```json
{{
  "critical_insights": [
    "<non-obvious insight that changes how you see the problem>",
    "<insight that only emerged from cross-perspective analysis>",
    "<insight about what NOT to do>",
    "<insight about systemic interactions>",
    "<insight about the simplest path>"
  ],
  "action_blueprint": [
    {{
      "step": 1,
      "action": "<concrete action>",
      "time_horizon": "<immediate|short-term|long-term>",
      "dependencies": ["<dep1>"],
      "go_criteria": "<measurable condition to proceed>",
      "fallback": "<what to do if this step fails>"
    }}
  ],
  "open_questions": [
    "<question that was NOT answered and why>",
    "<assumption that requires external validation>"
  ],
  "claim_labels": {{
    "<key claim 1>": "VERIFIED|HYPOTHESIS|UNKNOWN"
  }},
  "meta_audit": {{
    "most_dangerous_assumption": "<which assumption, if wrong, breaks everything>",
    "dominant_bias": "<the cognitive bias that most affected the analysis>",
    "remaining_uncertainty": "<the biggest unknown that persists>",
    "assumption_failure_impact": "<what changes if the main assumption is wrong>",
    "non_obvious_insight": "<the breakthrough that only emerged from this process>"
  }}
}}
```"""
