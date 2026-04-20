from __future__ import annotations
import json
from reasoner.models import PipelineState
from reasoner.phases._shared import get_language_instruction, _wrap_user_input

JURY_GENERATOR_SYSTEM = "You are an analytical assistant. Produce your best possible solution. Output ONLY valid JSON."

def jury_generator_prompt(state: PipelineState, generator_id: str) -> str:
    return f'{get_language_instruction(state)}\n\nProblem: {_wrap_user_input(state.problem)}\nDecomposition:\n{json.dumps(state.decomposition, indent=2)}\n\nYou are {generator_id}. Generate a solution.\n\nOutput JSON: {{"generator_id": "{generator_id}", "solution": "<your solution>", "key_claims": [...]}}'

JURY_CRITIC_SYSTEM = "You are an analytical assistant. Score each candidate against the provided guidelines. Output ONLY valid JSON."

def jury_critic_prompt(state: PipelineState) -> str:
    candidates_summary = [{"generator_id": c.generator_id, "approach": c.approach_summary} for c in state.generation_candidates]
    return f'{get_language_instruction(state)}\n\nJury Guidelines:\n{json.dumps(state.jury_guidelines)}\n\nCandidates:\n{json.dumps(candidates_summary, indent=2)}\n\nScore each candidate on factuality, reasoning, completeness, helpfulness.\n\nCRITICAL SCORING: A new critical scoring dimension is CONFIDENCE vs ACCURACY. It is better to state \'UNKNOWN\' or express low confidence than to guess confidently and be wrong. If a candidate makes a claim with high confidence that is factually incorrect or unsubstantiated, apply a significant **negative penalty** (0.0-10.0) to its score. Reward honest uncertainty.\n\nOutput JSON: {{"critic_id": "...", "candidate_scores": {{...}}, "confidence_vs_accuracy_penalty": <0.0-10.0>}}}}'

JURY_VERIFIER_SYSTEM = "You are an analytical assistant. Verify these claims. Output ONLY valid JSON."

def jury_verifier_prompt(state: PipelineState) -> str:
    all_claims = [{"claim": claim, "source": gc.generator_id} for gc in state.generation_candidates for claim in gc.key_claims]
    return f'{get_language_instruction(state)}\n\nVerify these claims:\n{json.dumps(all_claims, indent=2)}\n\nOutput JSON: {{"verifications": [{{"claim": "...", "verdict": "VERIFIED|...", "evidence": "..."}}]}}'

JURY_META_EVAL_SYSTEM = "You are an analytical assistant. Assess reliability and bias. Output ONLY valid JSON."

def jury_meta_eval_prompt(state: PipelineState) -> str:
    return f'{get_language_instruction(state)}\n\nEvaluate the critics based on their scores:\n{json.dumps(state.critic_scores, indent=2)}\n\nAssess critic reliability, bias, and agreement rate.\n\nOutput JSON: {{"critic_reliability": {{...}}, "meta_insight": "..."}}'
