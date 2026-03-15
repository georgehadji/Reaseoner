# Author: Georgios-Chrysovalantis Chatzivantsidis
"""
ARA Pipeline - Phase Prompts
Each prompt is a self-contained inference unit with explicit output format.
This file is refactored for a Dynamic Pipeline Orchestrator, containing
specialized prompts for each reasoning method to improve token efficiency.
"""

from __future__ import annotations
import json
from models import PipelineState, PerspectiveType

# ─────────────────────────────────────────────────────────────────────
# UNIVERSAL HELPERS
# ─────────────────────────────────────────────────────────────────────

def detect_language(text: str) -> str:
    """Simple language detection based on character patterns."""
    text = text.lower()
    
    # Greek
    if any(c in text for c in 'αβγδεζηθικλμνξοπρστυφχψω'):
        return "Greek"
    
    # Russian/Cyrillic
    if any(c in text for c in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'):
        return "Russian"
    
    # Arabic
    if any(c in text for c in 'ابتثجحخدذرزسشصضطظعغفقكلمنهوي'):
        return "Arabic"
    
    # Chinese
    if any('\u4e00' <= c <= '\u9fff' for c in text):
        return "Chinese"
    
    # Japanese (Hiragana/Katakana)
    if any('\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff' for c in text):
        return "Japanese"
    
    # Korean (Hangul)
    if any('\uac00' <= c <= '\ud7af' for c in text):
        return "Korean"
    
    return "English"


def get_language_instruction(state: PipelineState) -> str:
    """Returns the 'Respond in X' instruction line."""
    lang_map = {
        "Greek": "Απάντησε στα Ελληνικά.",
        "Russian": "Ответьте на русском языке.",
        "Arabic": "أجب بالعربية.",
        "Chinese": "用中文回答。",
        "Japanese": "日本語で回答してください。",
        "Korean": "한국어로 답변해 주세요.",
    }
    return lang_map.get(state.language, "Respond in English.")

# ─────────────────────────────────────────────────────────────────────
# METHOD: MULTI-PERSPECTIVE & SHARED PHASES
# ─────────────────────────────────────────────────────────────────────

# PHASE 0: CLASSIFICATION (Shared)
CLASSIFICATION_SYSTEM = "You are a task classification expert. Output ONLY valid JSON."
def classification_prompt(problem: str, language: str) -> str:
    lang_instruction = get_language_instruction(PipelineState(problem="", language=language))
    return f'{lang_instruction}\n\nClassify this problem (analytical, strategic, creative, technical, hybrid).\n\nProblem:\n{problem}\n\nOutput JSON: {{"task_type": "<type>", "rationale": "<why>", "language": "{language}"}}'

# PHASE 1: DECOMPOSITION (Shared)
DECOMPOSITION_SYSTEM = "You are an expert problem analyst. Decompose problems with precision. Output ONLY valid JSON."
def decomposition_prompt(state: PipelineState) -> str:
    # This prompt can be complex, so it's kept largely as-is but could be simplified if certain methods don't need all parts.
    # For now, we keep the dynamic parts for Jury/Research.
    is_jury = "jury" in (state.preset_name or "")
    jury_instr = "\nJURY CONSTITUTION: Define 3-5 objective 'jury_guidelines' for evaluating candidates." if is_jury else ""
    web_context = f"\nWEB DISCOVERY RESULTS:\n{json.dumps(state.web_discovery_results, indent=2)}" if state.web_discovery_results else ""
    vetted_flags = f"\nVETTED CONTEXT FLAGS (Potential issues from RAG):\n{json.dumps(state.vetted_context, indent=2)}" if state.vetted_context else ""

    return f'''{get_language_instruction(state)}

Problem: {state.problem}{web_context}{vetted_flags}
Decompose this problem.{jury_instr}

Output JSON:
{{
  "causal_chain": [
    {{
      "step": 1,
      "action": "<atomic step or action>",
      "depends_on": [], 
      "produces": ["<output 1>"],
      "constraints": ["<constraint 1>"]
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
  ],
  "jury_guidelines": ["<principle 1>", "<principle 2>"]
}}

Rules:
- Maximum 5 causal chain steps.
- Every implicit assumption must be surfaced and labeled.
- Failure modes must be specific, not generic.
- The causal chain must logically lead to a solution for the problem.'''

# PERSPECTIVE ANALYSIS (Multi-Perspective, Iterative)
PERSPECTIVE_SYSTEMS = {
    "constructive": "You reason constructively. Find the strongest possible solution. Output ONLY valid JSON.",
    "destructive": "You are a rigorous critic. Find every flaw. Do NOT propose solutions. Output ONLY valid JSON.",
    "systemic": "You think in systems. Identify second and third-order effects. Output ONLY valid JSON.",
    "minimalist": "You apply Occam's Razor aggressively. Find the simplest 80% solution. Output ONLY valid JSON.",
}
def perspective_prompt(state: PipelineState, perspective: str) -> str:
    # Context-aware prompt for token efficiency
    from dataclasses import asdict
    context = {"problem": state.problem, "causal_chain": state.decomposition.get("causal_chain", []) if state.decomposition else []}
    if state.reflexion_memory: # Specific to Iterative method
        context["reflexion_memory"] = state.reflexion_memory
    return f'{get_language_instruction(state)}\n\nContext:\n{json.dumps(context, indent=2)}\n\nAnalyze from the {perspective} perspective.\n\nOutput JSON: {{"perspective": "{perspective}", "core_analysis": "<your analysis>", "key_insights": ["<insight 1>"]}}'

# CRITIQUE (Multi-Perspective, Iterative)
CRITIQUE_SYSTEM = "You are an objective evaluator. Score solutions honestly. Output ONLY valid JSON."
def critique_prompt(state: PipelineState) -> str:
    candidates_summary = [{"perspective": c.perspective.value, "content": c.content[:400]} for c in state.candidates]
    return f'{get_language_instruction(state)}\n\nProblem: {state.problem}\n\nEvaluate these candidates:\n{json.dumps(candidates_summary, indent=2)}\n\nScore each 0-10 (logical_consistency, evidence_support, etc.) and provide a "steel_man" argument for the weakest.\n\nCRITICAL SCORING: A new critical scoring dimension is CONFIDENCE vs ACCURACY. It is better to state \'UNKNOWN\' or express low confidence than to guess confidently and be wrong. If a candidate makes a claim with high confidence that is factually incorrect or unsubstantiated, apply a significant **negative penalty** (0.0-10.0) to its score. Reward honest uncertainty.\n\nOutput JSON: {{"scores": [{{"perspective": "<p_val>", "logical_consistency": <0-10>, "confidence_vs_accuracy_penalty": <0.0-10.0>, "steel_man": "<arg>"}}]}}'

# STRESS TEST (Multi-Perspective, Scientific)
STRESS_SYSTEM = "You simulate adversarial conditions. Be specific about failure mechanics. Output ONLY valid JSON."
def stress_test_prompt(state: PipelineState) -> str:
    top_candidates_summary = [{"perspective": c.perspective.value, "content": c.content[:400]} for c in state.top_candidates]
    return f'{get_language_instruction(state)}\n\nTest these solutions under optimal, constraint_violation, and adversarial scenarios:\n{json.dumps(top_candidates_summary, indent=2)}\n\nOutput JSON: {{"stress_tests": [{{"scenario": "<name>", "survival_rate": <0.0-1.0>, "failure_mode": "<desc>"}}]}}'

# SYNTHESIS (All Methods)
SYNTHESIS_SYSTEM = """You are a master synthesizer. Integrate insights honestly. Acknowledge uncertainty. Output ONLY valid JSON.

CITATION REQUIREMENTS:
- When referencing information from web sources, include citations in your response
- Use format: [source_title](url) after each claim from a source
- Include all sources used in a "sources" array in the JSON output
- If no sources were used, set sources to empty array []"""

def synthesis_prompt(state: PipelineState) -> str:
    # Generic prompt that works for all methods by summarizing their final state
    final_context = state.to_context_dict()
    # To save tokens, we heavily truncate and summarize for the final step
    if 'candidates' in final_context:
        final_context['candidates'] = [{"perspective": c['perspective'], "insights": c['key_insights']} for c in final_context['candidates']]

    # Include web sources for citation
    sources_info = ""
    if state.web_discovery_results:
        sources_info = "\nWEB SOURCES (for citations):\n" + json.dumps([
            {"title": r.get("title", "Unknown"), "url": r.get("url", "")}
            for r in state.web_discovery_results[:10]  # Limit to top 10
        ], indent=2)

    method_hint_map = {
        "debate": "Frame as a judge's ruling.",
        "iterative": "Frame as the optimized solution that survived selection pressure.",
        "research": "Frame as an evidence report, grounding every claim with citations.",
        "jury": "Frame as a jury verdict, weighting results by critic reliability. Cite sources.",
        "scientific": "Frame as a final theory, explaining which hypotheses were supported or falsified.",
        "socratic": "Frame as a philosophical conclusion, summarizing the insights gained from the dialogue."
    }
    method_hint = next((hint for name, hint in method_hint_map.items() if name in (state.preset_name or "")), "Synthesize the best possible solution.")

    return f'{get_language_instruction(state)}\n\nFinal Context:\n{json.dumps(final_context, indent=2)}\n{sources_info}\n\n{method_hint}\n\nUse this exact format: [SOLUTION]...prose with citations like [Title](url)...[/SOLUTION] ```json...``` with fields: critical_insights, action_blueprint, open_questions, claim_labels, meta_audit, sources.'

# ─────────────────────────────────────────────────────────────────────
# METHOD: DEBATE
# ─────────────────────────────────────────────────────────────────────

DEBATE_OPENING_SYSTEM = "You are a debater. Present a strong, logical opening statement. Output ONLY valid JSON."
def debate_opening_prompt(state: PipelineState, side: str) -> str:
    return f'{get_language_instruction(state)}\n\nProblem: {state.problem}\n\nYou are Side {side}. Present your opening statement.\n\nOutput JSON: {{"side": "{side}", "content": "<your statement>", "key_claims": ["<claim 1>"]}}'

DEBATE_REBUTTAL_SYSTEM = "You are a debater. Attack your opponent\'s logic and defend your own. Output ONLY valid JSON."
def debate_rebuttal_prompt(state: PipelineState, side: str, opponent_statement: str) -> str:
    return f'{get_language_instruction(state)}\n\nYour opponent\'s statement:\n{opponent_statement}\n\nYou are Side {side}. Present your rebuttal.\n\nOutput JSON: {{"side": "{side}", "rebuttal_content": "<your rebuttal>", "target_flaws": ["<flaw 1>"]}}'

DEBATE_JUDGE_SYSTEM = "You are an impartial judge. Evaluate the debate and render a verdict. Output ONLY valid JSON."
def debate_judge_prompt(state: PipelineState) -> str:
    # Only the debate transcript is needed, saving tokens
    return f'{get_language_instruction(state)}\n\nDebate Transcript:\n{json.dumps(state.debate_rounds, indent=2)}\n\nScore both sides and declare a winner.\n\nOutput JSON: {{"scores": ..., "verdict_rationale": "..."}}'

# ─────────────────────────────────────────────────────────────────────
# METHOD: JURY (ORCHESTRATED)
# ─────────────────────────────────────────────────────────────────────

JURY_GENERATOR_SYSTEM = "You are an independent solution generator. Produce your best possible solution. Output ONLY valid JSON."
def jury_generator_prompt(state: PipelineState, generator_id: str) -> str:
    return f'{get_language_instruction(state)}\n\nProblem: {state.problem}\nDecomposition:\n{json.dumps(state.decomposition, indent=2)}\n\nYou are {generator_id}. Generate a solution.\n\nOutput JSON: {{"generator_id": "{generator_id}", "solution": "<your solution>", "key_claims": [...]}}'

JURY_CRITIC_SYSTEM = "You are an independent critic. Score each candidate against the provided guidelines. Output ONLY valid JSON."
def jury_critic_prompt(state: PipelineState) -> str:
    # Only pass summaries, not full text, to save tokens
    candidates_summary = [{"generator_id": c.generator_id, "approach": c.approach_summary} for c in state.generation_candidates]
    return f'{get_language_instruction(state)}\n\nJury Guidelines:\n{json.dumps(state.jury_guidelines)}\n\nCandidates:\n{json.dumps(candidates_summary, indent=2)}\n\nScore each candidate on factuality, reasoning, completeness, helpfulness.\n\nCRITICAL SCORING: A new critical scoring dimension is CONFIDENCE vs ACCURACY. It is better to state \'UNKNOWN\' or express low confidence than to guess confidently and be wrong. If a candidate makes a claim with high confidence that is factually incorrect or unsubstantiated, apply a significant **negative penalty** (0.0-10.0) to its score. Reward honest uncertainty.\n\nOutput JSON: {{"critic_id": "...", "candidate_scores": {{...}}, "confidence_vs_accuracy_penalty": <0.0-10.0>}}}}'

JURY_VERIFIER_SYSTEM = "You are a claim verification specialist. Verify these claims. Output ONLY valid JSON."
def jury_verifier_prompt(state: PipelineState) -> str:
    all_claims = [{"claim": claim, "source": gc.generator_id} for gc in state.generation_candidates for claim in gc.key_claims]
    return f'{get_language_instruction(state)}\n\nVerify these claims:\n{json.dumps(all_claims, indent=2)}\n\nOutput JSON: {{"verifications": [{{"claim": "...", "verdict": "VERIFIED|...", "evidence": "..."}}]}}'

JURY_META_EVAL_SYSTEM = "You evaluate the quality of critics. Assess reliability and bias. Output ONLY valid JSON."
def jury_meta_eval_prompt(state: PipelineState) -> str:
    return f'{get_language_instruction(state)}\n\nEvaluate the critics based on their scores:\n{json.dumps(state.critic_scores, indent=2)}\n\nAssess critic reliability, bias, and agreement rate.\n\nOutput JSON: {{"critic_reliability": {{...}}, "meta_insight": "..."}}'

# ─────────────────────────────────────────────────────────────────────
# METHOD: SCIENTIFIC
# ─────────────────────────────────────────────────────────────────────

SCIENTIFIC_HYPOTHESIS_SYSTEM = "You are a scientist. Generate falsifiable hypotheses from observations. Output ONLY valid JSON."
def scientific_hypothesis_prompt(state: PipelineState) -> str:
    return f'{get_language_instruction(state)}\n\nObservations: {state.problem}\n\nGenerate 3 competing hypotheses.\n\nOutput JSON: {{"hypotheses": [{{"id": "H1", "statement": "...", "falsifiability": "..."}}]}}'

SCIENTIFIC_TEST_SYSTEM = "You are an experimentalist. Design mental experiments to falsify hypotheses. Output ONLY valid JSON."
def scientific_test_prompt(state: PipelineState) -> str:
    return f'{get_language_instruction(state)}\n\nHypotheses:\n{json.dumps(state.scientific_state["hypotheses"], indent=2)}\n\nFor each, describe a test and predict the result (SUPPORTED, WEAKENED, FALSIFIED).\n\nOutput JSON: {{"test_results": [{{"hypothesis_id": "H1", "experiment": "...", "result": "..."}}]}}'

# ─────────────────────────────────────────────────────────────────────
# METHOD: SOCRATIC
# ─────────────────────────────────────────────────────────────────────

SOCRATIC_QUESTION_SYSTEM = "You are Socrates. Ask probing questions to expose contradictions. Do not answer. Output ONLY valid JSON."
def socratic_question_prompt(state: PipelineState) -> str:
    return f'{get_language_instruction(state)}\n\nProblem: {state.problem}\n\nGenerate 3-4 questions to challenge its assumptions.\n\nOutput JSON: {{"questions": [{{"id": "Q1", "text": "...", "target_assumption": "..."}}]}}'

SOCRATIC_ANSWER_SYSTEM = "You are a student of dialectic. Answer honestly and identify where your logic breaks. Output ONLY valid JSON."
def socratic_answer_prompt(state: PipelineState) -> str:
    return f'{get_language_instruction(state)}\n\nSocratic Questions:\n{json.dumps(state.socratic_state["questions"], indent=2)}\n\nAttempt to answer, noting any contradictions (\'aporia\').\n\nOutput JSON: {{"answers": [{{"question_id": "Q1", "answer": "...", "contradiction_found": "..."}}]}}'

# ─────────────────────────────────────────────────────────────────────
# METHOD: RESEARCH (Deep Iterative Search)
# ─────────────────────────────────────────────────────────────────────

DEEP_RESEARCH_SYSTEM = "You are an expert research agent. Your goal is to gather comprehensive information to solve the user's problem. You can issue search queries or declare that you have enough information. Output ONLY valid JSON."
def deep_research_prompt(state: PipelineState, current_knowledge: list[dict], iteration: int, max_iterations: int) -> str:
    knowledge_str = json.dumps(current_knowledge, indent=2) if current_knowledge else "No information gathered yet."
    return f'{get_language_instruction(state)}\n\nProblem: {state.problem}\n\nIteration: {iteration} of {max_iterations}\n\nCurrent Knowledge Gathered:\n{knowledge_str}\n\nAnalyze the current knowledge. If you need more information to fully answer the problem, generate up to 3 highly specific, SEO-friendly search queries. If you have enough information, or if you have reached the maximum iterations, set the action to "done".\n\nOutput JSON: {{"action": "search|done", "queries": ["<query1>", "<query2>"], "reasoning": "<why you chose this action>"}}'

# ─────────────────────────────────────────────────────────────────────
# COT DETECTION (for RAG Context Vetting)
# ─────────────────────────────────────────────────────────────────────

COT_DETECTION_SYSTEM = "You are a fact-checker and critical reviewer. Your goal is to identify potentially unsubstantiated, factually incorrect, or overly speculative statements in the provided text. Output ONLY valid JSON."

def cot_detection_prompt(state: PipelineState, retrieved_text: str) -> str:
    return f'{get_language_instruction(state)}\n\nProblem: {state.problem}\n\nReview the following retrieved text. Identify any statements that seem potentially unsubstantiated, factually incorrect, or overly speculative. For each identified statement, provide a brief explanation of your reasoning. If no issues are found, return an empty list.\n\nRetrieved Text:\n{retrieved_text}\n\nOutput JSON: {{"flags": [{{"statement": "<problematic statement>", "reasoning": "<why it\'s problematic>"}}]}}'


# ─────────────────────────────────────────────────────────────────────
# ITERATIVE CONTEXT GATHERING (for _phase_context_vetting)
# ─────────────────────────────────────────────────────────────────────

ITERATIVE_CONTEXT_SYSTEM = "You are an expert research assistant helping gather context for a reasoning problem. Your goal is to determine if you have enough information or if more searches are needed. Output ONLY valid JSON."

def iterative_context_prompt(state: PipelineState, current_results: list[dict], iteration: int, max_iterations: int) -> str:
    results_str = json.dumps(current_results, indent=2) if current_results else "No results yet."
    return f'{get_language_instruction(state)}\n\nProblem: {state.problem}\n\nIteration: {iteration} of {max_iterations}\n\nCurrent Search Results:\n{results_str}\n\nAnalyze the current results. Do you have enough relevant information to provide a comprehensive answer? If yes, set action to "done". If you need more information, provide up to 3 specific search queries to fill the gaps.\n\nOutput JSON: {{"action": "search|done", "queries": ["<query1>", "<query2>"], "reasoning": "<why you need more info or have enough>"}}'


# ─────────────────────────────────────────────────────────────────────
# DEEP READ (for critical source scraping)
# ─────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────
# RECOVERY PATH (cross-verification of high-penalty candidates)
# ─────────────────────────────────────────────────────────────────────

CROSS_VERIFICATION_SYSTEM = "You are a rigorous fact-checker. Identify specific factual errors, unsupported claims, or logical inconsistencies in a proposed solution. Be precise and cite exact problems. Output ONLY valid JSON."

def cross_verification_prompt(state: PipelineState, candidate_solution: dict) -> str:
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Original Problem: {state.problem}\n\n'
        f'Candidate Solution to Verify:\n{json.dumps(candidate_solution, indent=2)}\n\n'
        f'Identify any claims made with high confidence that are factually incorrect, '
        f'logically unsound, or unsubstantiated. Be specific.\n\n'
        f'Output JSON: {{"verified": <true|false>, "verification_findings": ["<issue1>", "<issue2>"], "summary": "<one sentence>"}}'
    )


# ─────────────────────────────────────────────────────────────────────
# DEEP READ (for critical source scraping)
# ─────────────────────────────────────────────────────────────────────

DEEP_READ_SYSTEM = "You are an expert at extracting and summarizing key information from web pages. Your goal is to provide a comprehensive summary of the page content relevant to the user's problem."

def deep_read_prompt(state: PipelineState, url: str, title: str) -> str:
    return f'{get_language_instruction(state)}\n\nOriginal Problem: {state.problem}\n\nURL: {url}\nTitle: {title}\n\nExtract and summarize the key information from this page that is relevant to solving the problem. Focus on facts, data, and evidence. Output ONLY valid JSON.\n\nOutput JSON: {{"summary": "<comprehensive summary>", "key_facts": ["<fact1>", "<fact2>"], "relevant_quotes": ["<quote1>"]}}'


# ─────────────────────────────────────────────────────────────────────
# A5: DEBATE — CROSS-EXAMINATION
# ─────────────────────────────────────────────────────────────────────

DEBATE_CROSS_SYSTEM = "You are cross-examining opposing counsel. Challenge specific claims with evidence. Be precise and direct. Output ONLY valid JSON."

def debate_cross_examine_prompt(state: PipelineState, side: str, opponent_claims: list) -> str:
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Problem: {state.problem}\n\n'
        f'You are Side {side}. Your opponent made these claims:\n'
        f'{json.dumps(opponent_claims, indent=2)}\n\n'
        f'Challenge each claim with counter-evidence or logical contradiction.\n\n'
        f'Output JSON: {{"side": "{side}", "challenges": ['
        f'{{"claim": "<claim>", "challenge": "<counter-evidence>", "verdict": "REFUTED|WEAKENED|STANDS"}}]}}'
    )


# ─────────────────────────────────────────────────────────────────────
# B1: PRE-MORTEM ANALYSIS
# ─────────────────────────────────────────────────────────────────────

PRE_MORTEM_FAILURE_SYSTEM = "You are a post-mortem analyst. Assume failure has already occurred and reconstruct why. Be specific and unflinching. Output ONLY valid JSON."

def pre_mortem_failure_prompt(state: PipelineState) -> str:
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Problem: {state.problem}\n\n'
        f'It is exactly 1 year later. The solution to this problem catastrophically failed. '
        f'Write the post-mortem as if it already happened. Be vivid, specific, and brutally honest.\n\n'
        f'Output JSON: {{"scenario": "<failure scenario name>", '
        f'"what_happened": "<narrative of the failure>", '
        f'"immediate_triggers": ["<trigger>"], '
        f'"affected_stakeholders": ["<stakeholder>"], '
        f'"severity": "catastrophic|severe|moderate"}}'
    )

PRE_MORTEM_BACKTRACK_SYSTEM = "You are a root cause analyst. Given a failure, identify the single most critical decision that led to it. Output ONLY valid JSON."

def pre_mortem_backtrack_prompt(state: PipelineState) -> str:
    failure = state.pre_mortem_state.get("failure_narrative", {})
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Original Problem: {state.problem}\n\n'
        f'Post-Mortem:\n{json.dumps(failure, indent=2)}\n\n'
        f'Trace back to the single initial decision that was the pivot point. '
        f'What seemingly reasonable choice, made early, set this failure in motion?\n\n'
        f'Output JSON: {{"pivot_decision": "<the decision>", '
        f'"decision_point": "<when it was made>", '
        f'"why_it_seemed_reasonable": "<the reason>", '
        f'"cascade": ["<cascade step>"]}}'
    )

PRE_MORTEM_SIGNALS_SYSTEM = "You are an early warning specialist. Identify observable signals that would have predicted failure before it happened. Output ONLY valid JSON."

def pre_mortem_signals_prompt(state: PipelineState) -> str:
    root_cause = state.pre_mortem_state.get("root_cause", {})
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Root Cause:\n{json.dumps(root_cause, indent=2)}\n\n'
        f'What observable signals appeared in the first 30 days after implementation '
        f'that, in hindsight, were early warnings of the coming failure?\n\n'
        f'Output JSON: {{"early_signals": ['
        f'{{"signal": "<observable event>", "day": 1, "how_to_detect": "<measurement>", "action_threshold": "<when to act>"}}], '
        f'"monitoring_cadence": "<frequency>"}}'
    )

PRE_MORTEM_REDESIGN_SYSTEM = "You are a solution architect. Redesign the original solution hardened against the identified failure modes. Output ONLY valid JSON."

def pre_mortem_redesign_prompt(state: PipelineState) -> str:
    pm = state.pre_mortem_state
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Problem: {state.problem}\n\n'
        f'Failure: {json.dumps(pm.get("failure_narrative", {}).get("what_happened", ""), indent=0)}\n'
        f'Root Cause: {json.dumps(pm.get("root_cause", {}).get("pivot_decision", ""), indent=0)}\n'
        f'Early Signals: {json.dumps([s.get("signal") for s in pm.get("early_signals", [])], indent=0)}\n\n'
        f'Redesign the solution to be robust against these failure modes. '
        f'Add specific safeguards, checkpoints, and rollback mechanisms.\n\n'
        f'Output JSON: {{"hardened_solution": "<redesigned approach>", '
        f'"safeguards": ["<specific safeguard>"], '
        f'"checkpoints": [{{"milestone": "<m>", "go_nogo_criterion": "<criterion>"}}], '
        f'"rollback_plan": "<what to do if failing>"}}'
    )


# ─────────────────────────────────────────────────────────────────────
# B2: BAYESIAN REASONING
# ─────────────────────────────────────────────────────────────────────

BAYESIAN_PRIOR_SYSTEM = "You are a Bayesian epistemologist. Elicit prior probability distributions over competing hypotheses. Be explicit about uncertainty. Output ONLY valid JSON."

def bayesian_prior_prompt(state: PipelineState) -> str:
    sub_problems = [sp.description for sp in (state.decomposition.sub_problems if state.decomposition else [])]
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Problem: {state.problem}\n\n'
        f'Sub-problems:\n{json.dumps(sub_problems, indent=2)}\n\n'
        f'Identify 2-4 competing hypotheses that could explain or solve this problem. '
        f'Assign prior probability P(H) to each (must sum to approximately 1.0). '
        f'Explain your reasoning for each prior.\n\n'
        f'Output JSON: {{"hypotheses": [{{"id": "H1", "statement": "<hypothesis>", '
        f'"prior_probability": 0.4, "reasoning": "<why this prior>"}}]}}'
    )

BAYESIAN_LIKELIHOOD_SYSTEM = "You are a Bayesian analyst. For each hypothesis, assess the likelihood of key observations. Output ONLY valid JSON."

def bayesian_likelihood_prompt(state: PipelineState) -> str:
    hypotheses = state.bayesian_state.get("hypotheses_with_priors", [])
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Problem: {state.problem}\n\n'
        f'Hypotheses:\n{json.dumps(hypotheses, indent=2)}\n\n'
        f'Identify 3-5 key observations or pieces of evidence relevant to this problem. '
        f'For each observation, assess P(E|H) and P(E|not-H) for each hypothesis.\n\n'
        f'Output JSON: {{"observations": ["<obs 1>"], "likelihoods": [{{"observation": "<obs>", '
        f'"hypothesis_id": "H1", "p_e_given_h": 0.8, "p_e_given_not_h": 0.2, '
        f'"reasoning": "<why>"}}]}}'
    )

BAYESIAN_POSTERIOR_SYSTEM = "You are a Bayesian statistician. Apply Bayes' theorem to compute posterior probabilities. Show your reasoning. Output ONLY valid JSON."

def bayesian_posterior_prompt(state: PipelineState) -> str:
    hypotheses = state.bayesian_state.get("hypotheses_with_priors", [])
    likelihoods = state.bayesian_state.get("evidence_likelihoods", [])
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Priors:\n{json.dumps(hypotheses, indent=2)}\n\n'
        f'Likelihoods:\n{json.dumps(likelihoods, indent=2)}\n\n'
        f'Apply Bayes rule P(H|E) ∝ P(E|H) × P(H) to compute posterior for each hypothesis '
        f'after observing all evidence. Normalize so posteriors sum to 1.0.\n\n'
        f'Output JSON: {{"posteriors": [{{"hypothesis_id": "H1", "posterior_probability": 0.75, '
        f'"explanation": "<how evidence updated belief>"}}], '
        f'"most_probable": "H1"}}'
    )

BAYESIAN_SENSITIVITY_SYSTEM = "You are a decision analyst. Test which prior assumptions most change the posterior if they are wrong. Output ONLY valid JSON."

def bayesian_sensitivity_prompt(state: PipelineState) -> str:
    hypotheses = state.bayesian_state.get("hypotheses_with_priors", [])
    posteriors = state.bayesian_state.get("posteriors", [])
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Priors:\n{json.dumps(hypotheses, indent=2)}\n\n'
        f'Posteriors:\n{json.dumps(posteriors, indent=2)}\n\n'
        f'For each major prior assumption, assess: if this prior were very different, '
        f'how much would the posterior change? Which assumption is most critical?\n\n'
        f'Output JSON: {{"sensitivity_analysis": [{{"assumption": "<prior assumption>", '
        f'"if_wrong": "<alternative>", "posterior_shift": "small|medium|large", '
        f'"importance": "critical|high|medium"}}], '
        f'"most_sensitive_assumption": "<which assumption>"}}'
    )


# ─────────────────────────────────────────────────────────────────────
# B3: DIALECTICAL REASONING (Hegelian Aufhebung)
# ─────────────────────────────────────────────────────────────────────

DIALECTICAL_THESIS_SYSTEM = "You are articulating a Hegelian thesis: the strongest possible affirmative position. Be rigorous and committed. Output ONLY valid JSON."

def dialectical_thesis_prompt(state: PipelineState) -> str:
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Problem: {state.problem}\n\n'
        f'Articulate the strongest possible affirmative thesis position. '
        f'Be fully committed — this is the strongest case FOR one approach, not a balanced view.\n\n'
        f'Output JSON: {{"thesis": "<strongest affirmative position>", '
        f'"key_commitments": ["<commitment 1>"], '
        f'"assumptions": ["<assumption>"]}}'
    )

DIALECTICAL_ANTITHESIS_SYSTEM = "You are exposing the internal contradictions of a thesis. Negate its commitments rigorously. Output ONLY valid JSON."

def dialectical_antithesis_prompt(state: PipelineState) -> str:
    thesis = state.dialectical_state.get("thesis", "")
    commitments = state.dialectical_state.get("key_commitments", [])
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Problem: {state.problem}\n\n'
        f'Thesis: {thesis}\n\n'
        f'Key Commitments: {json.dumps(commitments, indent=2)}\n\n'
        f'Expose the internal contradictions of this thesis. '
        f'Negate each commitment. Show why this position is untenable.\n\n'
        f'Output JSON: {{"antithesis": "<negation of thesis>", '
        f'"contradictions_exposed": ["<contradiction in thesis>"], '
        f'"negated_commitments": [{{"commitment": "<c>", "negation": "<n>"}}]}}'
    )

DIALECTICAL_CONTRADICTIONS_SYSTEM = "You are a dialectical analyst. Classify which contradictions are truly irreconcilable and which can be transcended at a higher level. Output ONLY valid JSON."

def dialectical_contradictions_prompt(state: PipelineState) -> str:
    thesis = state.dialectical_state.get("thesis", "")
    antithesis = state.dialectical_state.get("antithesis", "")
    contradictions = state.dialectical_state.get("contradictions_exposed", [])
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Thesis: {thesis}\n\nAntithesis: {antithesis}\n\n'
        f'Contradictions: {json.dumps(contradictions, indent=2)}\n\n'
        f'Classify each contradiction: irreconcilable (cannot coexist) vs '
        f'compatible (can resolve at higher conceptual level). '
        f'Identify synthesis candidates — truths from each side worth preserving.\n\n'
        f'Output JSON: {{"irreconcilable": ["<contradiction>"], '
        f'"compatible": ["<resolves at higher level>"], '
        f'"synthesis_candidates": ["<truth from thesis>", "<truth from antithesis>"]}}'
    )

DIALECTICAL_AUFHEBUNG_SYSTEM = "You are performing Hegelian Aufhebung: qualitative transcendence, NOT compromise. Preserve the truths of both positions at a higher level. Output ONLY valid JSON."

def dialectical_aufhebung_prompt(state: PipelineState) -> str:
    d = state.dialectical_state
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Problem: {state.problem}\n\n'
        f'Thesis: {d.get("thesis", "")}\n'
        f'Antithesis: {d.get("antithesis", "")}\n'
        f'Compatible contradictions: {json.dumps(d.get("compatible", []), indent=2)}\n'
        f'Synthesis candidates: {json.dumps(d.get("synthesis_candidates", []), indent=2)}\n\n'
        f'Perform Aufhebung: a qualitatively higher position that transcends both. '
        f'This is NOT a compromise — it must contain genuine novelty.\n\n'
        f'Output JSON: {{"aufhebung": "<higher position>", '
        f'"preserved_from_thesis": ["<truth kept>"], '
        f'"preserved_from_antithesis": ["<truth kept>"], '
        f'"transcended": "<what was left behind>", '
        f'"new_insights": ["<genuine novelty>"]}}'
    )
