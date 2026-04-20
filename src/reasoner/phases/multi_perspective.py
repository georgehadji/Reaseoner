from __future__ import annotations
import json
from reasoner.models import PipelineState
from reasoner.core.constants import TRUNCATION
from reasoner.phases._shared import get_language_instruction, _followup_context, _wrap_user_input

PERSPECTIVE_SYSTEMS = {
    "constructive": "Respond in the same language as the user's problem. Build the strongest, most comprehensive solution. Analyze from first principles, cite historical precedents where relevant, and address 2nd-order consequences. Minimum 4 paragraphs. JSON only.",
    "destructive": "Respond in the same language as the user's problem. Find every flaw in the proposed approach or subject matter. Focus exclusively on substantive weaknesses, risks, and incorrect assumptions. Do NOT criticize the prompt's language, grammar, formatting, or mixed languages. JSON only.",
    "systemic": "Respond in the same language as the user's problem. Find 2nd/3rd-order effects. JSON only.",
    "minimalist": "Respond in the same language as the user's problem. Apply Occam's Razor. Simplest 80% solution. JSON only.",
}

def perspective_prompt(state: PipelineState, perspective: str) -> str:
    context = {"problem": _wrap_user_input(state.problem[:TRUNCATION.PROMPT])}
    if state.decomposition:
        context["chain"] = len(state.decomposition.get("causal_chain", []))
    if state.reflexion_memory:
        context["memory"] = state.reflexion_memory[:TRUNCATION.MEMORY]
    followup = _followup_context(state)
    
    return f'{get_language_instruction(state)}\n\nContext: {json.dumps(context)}{followup}\n\nAnalyze from {perspective} perspective.\n\nYou MUST return EXACTLY this JSON structure with no additional keys. Put all analysis inside "core_analysis" as a single string (3-6 paragraphs). Label factual claims inline with [VERIFIED], [HYPOTHESIS], or [UNKNOWN].\n\nJSON: {{"perspective": "{perspective}", "core_analysis": "<your detailed analysis with inline epistemic labels>", "key_insights": ["<insight 1>", "<insight 2>", "<insight 3>"]}}'

CRITIQUE_SYSTEM = "You are an analytical assistant. Score solutions honestly. Output ONLY valid JSON."

def critique_prompt(state: PipelineState) -> str:
    candidates_summary = [
        {"perspective": c.perspective.value, "one_liner": c.content[:TRUNCATION.API_STORAGE], "key_insights": c.key_insights[:TRUNCATION.MEMORY]}
        for c in state.candidates
    ]
    return f'{get_language_instruction(state)}\n\nProblem: {_wrap_user_input(state.problem)}\n\nEvaluate these candidates:\n{json.dumps(candidates_summary, indent=2)}\n\nScore each 0-10 (logical_consistency, evidence_support, etc.) and provide a "steel_man" argument for the weakest.\n\nCRITICAL SCORING: A new critical scoring dimension is CONFIDENCE vs ACCURACY. It is better to state \'UNKNOWN\' or express low confidence than to guess confidently and be wrong. If a candidate makes a claim with high confidence that is factually incorrect or unsubstantiated, apply a significant **negative penalty** (0.0-10.0) to its score. Reward honest uncertainty.\n\nOutput JSON: {{"scores": [{{"perspective": "<p_val>", "logical_consistency": <0-10>, "confidence_vs_accuracy_penalty": <0.0-10.0>, "steel_man": "<arg>"}}]}}'

STRESS_SYSTEM = "You are an analytical assistant. Simulate adversarial conditions. Be specific about real-world failure mechanics. Output ONLY valid JSON."

def stress_test_prompt(state: PipelineState) -> str:
    top_candidates_summary = [
        {"perspective": c.perspective.value, "one_liner": c.content[:TRUNCATION.ASSUMPTION]}
        for c in state.top_candidates
    ]
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Test these solutions under optimal, constraint_violation, and adversarial scenarios:\n'
        f'{json.dumps(top_candidates_summary, indent=2)}\n\n'
        f'Describe concrete real-world failure mechanics (e.g., supply-chain collapse, regulatory shutdown, market crash). '
        f'Do NOT describe LLM processing errors like truncation, formatting issues, length limits, or off-topic responses. '
        f'Output JSON: {{"stress_tests": [{{"scenario": "<name>", "survival_rate": <0.0-1.0>, "failure_mode": "<desc>"}}]}}'
    )
