# Author: Georgios-Chrysovalantis Chatzivantsidis
"""
ARA Pipeline - Phase Prompts
Each prompt is a self-contained inference unit with explicit output format.
This file is refactored for a Dynamic Pipeline Orchestrator, containing
specialized prompts for each reasoning method to improve token efficiency.
"""

from __future__ import annotations
import json
from reasoner.models import PipelineState, PerspectiveType
from reasoner.core.constants import JSON_ONLY_FOOTER, TRUNCATION, DEFAULT_SEARCH_RESULTS

# ─────────────────────────────────────────────────────────────────────
# UNIVERSAL HELPERS
# ─────────────────────────────────────────────────────────────────────

import re

def detect_language(text: str) -> str:
    """Simple language detection based on character patterns."""
    text = text.lower()
    sample = text[:TRUNCATION.PROBLEM]

    # Greek (full Greek and Coptic block for better coverage)
    if re.search(r'[\u0370-\u03FF]', sample):
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
    
    # Turkish (distinctive characters: ı, ğ, ç, ş — checked first because ü/ö can overlap with German)
    turkish_exclusive = 'ığıçış'
    if any(c in text for c in turkish_exclusive):
        return "Turkish"
    
    # German (exclusive characters: ä, ö, ß; ü is shared with Spanish)
    german_exclusive = 'äöß'
    if any(c in text for c in german_exclusive):
        return "German"
    
    # Spanish (common Spanish-specific characters)
    spanish_chars = 'áéíóúüñ¿¡'
    if any(c in text for c in spanish_chars):
        return "Spanish"
    
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
        "Spanish": "Responde en español.",
        "German": "Antworte auf Deutsch.",
        "Turkish": "Türkçe cevap ver.",
    }
    return lang_map.get(state.language, "Respond in English.")


def _followup_context(state: PipelineState) -> str:
    """Build a compact follow-up context block for injection into prompts."""
    if not state.conversation_history:
        return ""
    history_text = ""
    for turn in state.conversation_history[-6:]:
        role = turn.get("role", "user").capitalize()
        content = turn.get("content", "")
        history_text += f"{role}: {_wrap_user_input(content)}\n"
    ctx = f"\n---\nCONVERSATION HISTORY (Turn {state.turn_number}):\n{history_text}"
    if state.previous_synthesis:
        ctx += f"PREVIOUS SYNTHESIS:\n{state.previous_synthesis[:TRUNCATION.LARGE_CONTENT]}\n"
    ctx += "---\n"
    return ctx


def _wrap_user_input(text: str) -> str:
    """Wrap user-controlled text in explicit delimiters."""
    return f"<<<USER_INPUT>>>\n{text}\n<<<END_USER_INPUT>>>"


def _wrap_external_content(text: str) -> str:
    """Wrap external/untrusted content in explicit delimiters."""
    return f"<<<EXTERNAL_CONTENT>>>\n{text}\n<<<END_EXTERNAL_CONTENT>>>"

# ─────────────────────────────────────────────────────────────────────
# QUERY DISAMBIGUATION (Optional Pre-Phase)
# ─────────────────────────────────────────────────────────────────────
DISAMBIGUATION_SYSTEM = "You are an analytical assistant. Detect whether a problem is ambiguous and could be interpreted in multiple ways. Output ONLY valid JSON."

def disambiguation_prompt(problem: str, task_type: str | None) -> str:
    task_hint = f"Task type: {task_type}. " if task_type else ""
    return (
        f'Analyze whether the following problem is ambiguous or could be interpreted in multiple ways. '
        f'{task_hint}If ambiguous, explain why and provide a clearer rewritten version. If clear, state that it is unambiguous.\n\n'
        f'Problem: {_wrap_user_input(problem)}\n\n'
        f'Output JSON: {{"was_ambiguous": true/false, "rewritten_query": "<clearest version>", "reasoning": "<why>"}}'
    )

# ─────────────────────────────────────────────────────────────────────
# PROMPT ENHANCEMENT (Optional Pre-Phase)
# ─────────────────────────────────────────────────────────────────────
PROMPT_ENHANCEMENT_SYSTEM = "You are an analytical assistant. Rewrite the user's problem to make it clearer, more specific, and easier for an AI reasoning system to solve. Preserve the original intent, tone, and language. Output ONLY valid JSON."

def prompt_enhancement_prompt(problem: str, language: str) -> str:
    lang_instruction = get_language_instruction(PipelineState(problem="", language=language))
    return f'{lang_instruction}\n\nOriginal Problem:\n{_wrap_user_input(problem)}\n\nRewrite this problem to be clearer, more specific, and easier for a multi-step AI reasoning pipeline to solve. Preserve the original language and intent.\n\nOutput JSON: {{"enhanced_problem": "<rewritten problem>", "improvements": ["<what was improved>"]}}'

# ─────────────────────────────────────────────────────────────────────
# METHOD: MULTI-PERSPECTIVE & SHARED PHASES
# ─────────────────────────────────────────────────────────────────────

# PHASE 0: CLASSIFICATION (Shared)
# TOKEN OPTIMIZATION: Compressed from 77 to 47 chars (-39%)
CLASSIFICATION_SYSTEM = "Classify task type. JSON only."
def classification_prompt(problem: str, language: str, state: PipelineState | None = None) -> str:
    lang_instruction = get_language_instruction(PipelineState(problem="", language=language))
    followup = _followup_context(state) if state else ""
    return (
        f'{lang_instruction}\n\nProblem:\n{_wrap_user_input(problem)}{followup}\n\n'
        f'Choose exactly ONE task type from: analytical, strategic, creative, technical, predictive, hybrid. '
        f'JSON: {{"task_type": "analytical", "rationale": "<why>", "language": "{language}"}}'
    )

# PHASE 1: DECOMPOSITION (Shared)
# TOKEN OPTIMIZATION: Compressed from 104 to 62 chars (-40%)
DECOMPOSITION_SYSTEM = "Decompose problem into sub-problems. JSON only."
def decomposition_prompt(state: PipelineState) -> str:
    # TOKEN OPTIMIZATION: Condensed prompt structure
    is_jury = "jury" in (state.preset_name or "")
    jury_instr = " Add jury_guidelines." if is_jury else ""
    # TOKEN OPTIMIZATION: Omit verbose context, use compact format
    web_context = f"\nWeb: {state.web_discovery_results[:TRUNCATION.KEY_INSIGHTS]}" if state.web_discovery_results else ""
    followup = _followup_context(state)
    
    return f'''{get_language_instruction(state)}

Problem: {_wrap_user_input(state.problem)}{web_context}{followup}
Decompose.{jury_instr}

JSON: {{"causal_chain": [{{"step": 1, "action": "<action>", "produces": ["<output>"]}}], "assumptions": [{{"text": "<assumption>", "label": "VERIFIED|HYPOTHESIS|UNKNOWN", "rationale": "<why this label>", "source_hint": "<source name or URL if VERIFIED>"}}], "failure_modes": ["<failure>"], "critical_sources": [{{"url": "<URL>", "reason": "<why it matters>"}}]}}

Rules: Max 5 steps. Surface assumptions with rationale. VERIFIED assumptions MUST cite a source_hint. If web results exist, list 1-2 critical_sources. Be specific.'''

# PERSPECTIVE ANALYSIS (Multi-Perspective, Iterative)
# TOKEN OPTIMIZATION: Compressed perspective systems (-35%)
PERSPECTIVE_SYSTEMS = {
    "constructive": "Respond in the same language as the user's problem. Build the strongest, most comprehensive solution. Analyze from first principles, cite historical precedents where relevant, and address 2nd-order consequences. Minimum 4 paragraphs. JSON only.",
    "destructive": "Respond in the same language as the user's problem. Find every flaw in the proposed approach or subject matter. Focus exclusively on substantive weaknesses, risks, and incorrect assumptions. Do NOT criticize the prompt's language, grammar, formatting, or mixed languages. JSON only.",
    "systemic": "Respond in the same language as the user's problem. Find 2nd/3rd-order effects. JSON only.",
    "minimalist": "Respond in the same language as the user's problem. Apply Occam's Razor. Simplest 80% solution. JSON only.",
}
def perspective_prompt(state: PipelineState, perspective: str) -> str:
    # TOKEN OPTIMIZATION: Minimal context, compact format
    context = {"problem": _wrap_user_input(state.problem[:TRUNCATION.PROMPT])}  # Truncate problem
    if state.decomposition:
        context["chain"] = len(state.decomposition.get("causal_chain", []))
    if state.reflexion_memory:
        context["memory"] = state.reflexion_memory[:TRUNCATION.MEMORY]  # Top 2 only
    followup = _followup_context(state)
    
    return f'{get_language_instruction(state)}\n\nContext: {json.dumps(context)}{followup}\n\nAnalyze from {perspective} perspective.\n\nYou MUST return EXACTLY this JSON structure with no additional keys. Put all analysis inside "core_analysis" as a single string (3-6 paragraphs). Label factual claims inline with [VERIFIED], [HYPOTHESIS], or [UNKNOWN].\n\nJSON: {{"perspective": "{perspective}", "core_analysis": "<your detailed analysis with inline epistemic labels>", "key_insights": ["<insight 1>", "<insight 2>", "<insight 3>"]}}'

# CRITIQUE (Multi-Perspective, Iterative)
CRITIQUE_SYSTEM = "You are an analytical assistant. Score solutions honestly. Output ONLY valid JSON."
def critique_prompt(state: PipelineState) -> str:
    # TOKEN OPTIMIZATION: Use condensed candidate summary (200 chars instead of 400)
    candidates_summary = [
        {"perspective": c.perspective.value, "one_liner": c.content[:TRUNCATION.API_STORAGE], "key_insights": c.key_insights[:TRUNCATION.MEMORY]}
        for c in state.candidates
    ]
    return f'{get_language_instruction(state)}\n\nProblem: {_wrap_user_input(state.problem)}\n\nEvaluate these candidates:\n{json.dumps(candidates_summary, indent=2)}\n\nScore each 0-10 (logical_consistency, evidence_support, etc.) and provide a "steel_man" argument for the weakest.\n\nCRITICAL SCORING: A new critical scoring dimension is CONFIDENCE vs ACCURACY. It is better to state \'UNKNOWN\' or express low confidence than to guess confidently and be wrong. If a candidate makes a claim with high confidence that is factually incorrect or unsubstantiated, apply a significant **negative penalty** (0.0-10.0) to its score. Reward honest uncertainty.\n\nOutput JSON: {{"scores": [{{"perspective": "<p_val>", "logical_consistency": <0-10>, "confidence_vs_accuracy_penalty": <0.0-10.0>, "steel_man": "<arg>"}}]}}'

# STRESS TEST (Multi-Perspective, Scientific)
STRESS_SYSTEM = "You are an analytical assistant. Simulate adversarial conditions. Be specific about real-world failure mechanics. Output ONLY valid JSON."
def stress_test_prompt(state: PipelineState) -> str:
    # TOKEN OPTIMIZATION: Use condensed top candidates summary (150 chars instead of 400)
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

# SYNTHESIS (All Methods)
SYNTHESIS_SYSTEM = """You are an analytical assistant. Integrate insights honestly. Acknowledge uncertainty.

LANGUAGE RULE (CRITICAL):
- The user has explicitly requested a specific language at the start of the prompt.
- Your ENTIRE response — both the prose inside [SOLUTION] tags AND all JSON string values — MUST be written in that requested language.
- Do NOT use English unless the user explicitly asked for English.

FORMAT RULES:
- Use this exact format: [SOLUTION]...prose with citations like [Title](url)...[/SOLUTION] followed by a JSON block in ```json...```
- If you cannot produce the [SOLUTION] tag, return ONLY the JSON block; the pipeline will synthesize prose for you.
- Output valid JSON inside the fence with fields: critical_insights, action_blueprint, open_questions, claim_labels, meta_audit, sources.

CITATION REQUIREMENTS:
- When referencing information from web sources, include citations in your response
- Use format: [source_title](url) after each claim from a source
- You MUST only cite sources listed in the WEB SOURCES section above. Do not invent or reuse URLs from memory.
- Include all sources used in a "sources" array in the JSON output
- If no sources were used, set sources to empty array []

ACTION BLUEPRINT RULES:
- Each item MUST be an object with keys: step, action, time_horizon, go_criteria, fallback.
- Do not use "?" or other placeholder keys. If you cannot produce a concrete action, return an empty list.

META AUDIT REQUIREMENTS:
- Only include meta_audit if you have genuine audit data from a real review process
- If no real audit data exists, set every meta_audit field to an empty string
- Do NOT invent dates, scores, or review statuses

CIRCUIT BREAKER:
- If you could not find reliable sources or the context is contaminated, say so explicitly.
- Do NOT synthesize confident answers from UNVERIFIED or missing data.
- Flag uncertainty honestly rather than hallucinating certainty."""

def synthesis_prompt(state: PipelineState) -> str:
    # Generic prompt that works for all methods by summarizing their final state
    final_context = state.to_context_dict()
    # To save tokens, we heavily truncate and summarize for the final step
    if 'candidates' in final_context:
        final_context['candidates'] = [{"perspective": c['perspective'], "insights": c['key_insights']} for c in final_context['candidates']]

    # Include structured deep-read sources for citation
    sources_info = ""
    if state.vetted_context:
        deep_sources = []
        total_chars = 0
        max_chars = TRUNCATION.LARGE_CONTENT
        for r in state.vetted_context[:DEFAULT_SEARCH_RESULTS]:
            entry = {
                "title": r.get("title", "Unknown"),
                "url": r.get("url", ""),
                "summary": r.get("summary", ""),
                "key_facts": (r.get("key_facts") or [])[:TRUNCATION.KEY_INSIGHTS],
                "relevant_quotes": (r.get("relevant_quotes") or [])[:TRUNCATION.MEMORY],
                "vetting_flags": (r.get("vetting_flags") or [])[:TRUNCATION.MEMORY],
            }
            entry_text = json.dumps(entry)
            if total_chars + len(entry_text) > max_chars:
                break
            total_chars += len(entry_text)
            deep_sources.append(entry)
        sources_info = "\nWEB SOURCES (with extracted summaries):\n" + json.dumps(deep_sources, indent=2)
    elif state.web_discovery_results:
        # Fallback to legacy bare titles/URLs
        sources_info = "\nWEB SOURCES (for citations):\n" + json.dumps([
            {"title": r.get("title", "Unknown"), "url": r.get("url", "")}
            for r in state.web_discovery_results[:DEFAULT_SEARCH_RESULTS]
        ], indent=2)

    # SECURITY: Use a generic synthesis instruction to avoid revealing the reasoning method
    method_hint = "Synthesize the best possible solution."
    followup = _followup_context(state)
    quality_note = f"\nCONTEXT QUALITY: {state.context_quality}\n" if state.context_quality and state.context_quality != "unknown" else ""

    return f'{get_language_instruction(state)}\n\nFinal Context:\n{_wrap_external_content(json.dumps(final_context, indent=2))}\n{_wrap_external_content(sources_info)}{followup}{quality_note}\n\n{method_hint}\n\nUse this exact format: [SOLUTION]...prose with citations like [Title](url)...[/SOLUTION] ```json...``` with fields: critical_insights, action_blueprint, open_questions, claim_labels, meta_audit, sources.'

# ─────────────────────────────────────────────────────────────────────
# METHOD: DEBATE
# ─────────────────────────────────────────────────────────────────────

DEBATE_OPENING_SYSTEM = "You are an analytical assistant. Present a strong, logical opening statement. Output ONLY valid JSON."
def debate_opening_prompt(state: PipelineState, side: str) -> str:
    return f'{get_language_instruction(state)}\n\nProblem: {_wrap_user_input(state.problem)}\n\nYou are Side {side}. Present your opening statement.\n\nOutput JSON: {{"side": "{side}", "content": "<your statement>", "key_claims": ["<claim 1>"]}}'

DEBATE_REBUTTAL_SYSTEM = "You are an analytical assistant. Attack your opponent\'s logic and defend your own. Output ONLY valid JSON."
def debate_rebuttal_prompt(state: PipelineState, side: str, opponent_statement: str) -> str:
    return f'{get_language_instruction(state)}\n\nYour opponent\'s statement:\n{opponent_statement}\n\nYou are Side {side}. Present your rebuttal.\n\nOutput JSON: {{"side": "{side}", "rebuttal_content": "<your rebuttal>", "target_flaws": ["<flaw 1>"]}}'

DEBATE_JUDGE_SYSTEM = "You are an analytical assistant. Evaluate the debate and render a verdict. Output ONLY valid JSON."
def debate_judge_prompt(state: PipelineState) -> str:
    # Only the debate transcript is needed, saving tokens
    return f'{get_language_instruction(state)}\n\nDebate Transcript:\n{json.dumps(state.debate_rounds, indent=2)}\n\nScore both sides and declare a winner.\n\nOutput JSON: {{"scores": ..., "verdict_rationale": "..."}}'

# ─────────────────────────────────────────────────────────────────────
# METHOD: JURY (ORCHESTRATED)
# ─────────────────────────────────────────────────────────────────────

JURY_GENERATOR_SYSTEM = "You are an analytical assistant. Produce your best possible solution. Output ONLY valid JSON."
def jury_generator_prompt(state: PipelineState, generator_id: str) -> str:
    return f'{get_language_instruction(state)}\n\nProblem: {_wrap_user_input(state.problem)}\nDecomposition:\n{json.dumps(state.decomposition, indent=2)}\n\nYou are {generator_id}. Generate a solution.\n\nOutput JSON: {{"generator_id": "{generator_id}", "solution": "<your solution>", "key_claims": [...]}}'

JURY_CRITIC_SYSTEM = "You are an analytical assistant. Score each candidate against the provided guidelines. Output ONLY valid JSON."
def jury_critic_prompt(state: PipelineState) -> str:
    # Only pass summaries, not full text, to save tokens
    candidates_summary = [{"generator_id": c.generator_id, "approach": c.approach_summary} for c in state.generation_candidates]
    return f'{get_language_instruction(state)}\n\nJury Guidelines:\n{json.dumps(state.jury_guidelines)}\n\nCandidates:\n{json.dumps(candidates_summary, indent=2)}\n\nScore each candidate on factuality, reasoning, completeness, helpfulness.\n\nCRITICAL SCORING: A new critical scoring dimension is CONFIDENCE vs ACCURACY. It is better to state \'UNKNOWN\' or express low confidence than to guess confidently and be wrong. If a candidate makes a claim with high confidence that is factually incorrect or unsubstantiated, apply a significant **negative penalty** (0.0-10.0) to its score. Reward honest uncertainty.\n\nOutput JSON: {{"critic_id": "...", "candidate_scores": {{...}}, "confidence_vs_accuracy_penalty": <0.0-10.0>}}}}'

JURY_VERIFIER_SYSTEM = "You are an analytical assistant. Verify these claims. Output ONLY valid JSON."
def jury_verifier_prompt(state: PipelineState) -> str:
    all_claims = [{"claim": claim, "source": gc.generator_id} for gc in state.generation_candidates for claim in gc.key_claims]
    return f'{get_language_instruction(state)}\n\nVerify these claims:\n{json.dumps(all_claims, indent=2)}\n\nOutput JSON: {{"verifications": [{{"claim": "...", "verdict": "VERIFIED|...", "evidence": "..."}}]}}'

JURY_META_EVAL_SYSTEM = "You are an analytical assistant. Assess reliability and bias. Output ONLY valid JSON."
def jury_meta_eval_prompt(state: PipelineState) -> str:
    return f'{get_language_instruction(state)}\n\nEvaluate the critics based on their scores:\n{json.dumps(state.critic_scores, indent=2)}\n\nAssess critic reliability, bias, and agreement rate.\n\nOutput JSON: {{"critic_reliability": {{...}}, "meta_insight": "..."}}'

# ─────────────────────────────────────────────────────────────────────
# METHOD: SCIENTIFIC
# ─────────────────────────────────────────────────────────────────────

SCIENTIFIC_HYPOTHESIS_SYSTEM = "You are an analytical assistant. Generate falsifiable hypotheses from observations. Output ONLY valid JSON."
def scientific_hypothesis_prompt(state: PipelineState) -> str:
    return f'{get_language_instruction(state)}\n\nObservations: {_wrap_user_input(state.problem)}\n\nGenerate 3 competing hypotheses.\n\nOutput JSON: {{"hypotheses": [{{"id": "H1", "statement": "...", "falsifiability": "..."}}]}}'

SCIENTIFIC_TEST_SYSTEM = "You are an analytical assistant. Design mental experiments to falsify hypotheses. Output ONLY valid JSON."
def scientific_test_prompt(state: PipelineState) -> str:
    return f'{get_language_instruction(state)}\n\nHypotheses:\n{json.dumps(state.scientific_state["hypotheses"], indent=2)}\n\nFor each, describe a test and predict the result (SUPPORTED, WEAKENED, FALSIFIED).\n\nOutput JSON: {{"test_results": [{{"hypothesis_id": "H1", "experiment": "...", "result": "..."}}]}}'

# ─────────────────────────────────────────────────────────────────────
# METHOD: SOCRATIC
# ─────────────────────────────────────────────────────────────────────

SOCRATIC_QUESTION_SYSTEM = "You are an analytical assistant. Ask probing questions to expose contradictions. Do not answer. Output ONLY valid JSON."
def socratic_question_prompt(state: PipelineState) -> str:
    return f'{get_language_instruction(state)}\n\nProblem: {_wrap_user_input(state.problem)}\n\nGenerate 3-4 questions to challenge its assumptions.\n\nOutput JSON: {{"questions": [{{"id": "Q1", "text": "...", "target_assumption": "..."}}]}}'

SOCRATIC_ANSWER_SYSTEM = "You are an analytical assistant. Answer honestly and identify where your logic breaks. Output ONLY valid JSON."
def socratic_answer_prompt(state: PipelineState) -> str:
    return f'{get_language_instruction(state)}\n\nSocratic Questions:\n{json.dumps(state.socratic_state["questions"], indent=2)}\n\nAttempt to answer, noting any contradictions (\'aporia\').\n\nOutput JSON: {{"answers": [{{"question_id": "Q1", "answer": "...", "contradiction_found": "..."}}]}}'

# ─────────────────────────────────────────────────────────────────────
# METHOD: RESEARCH (Deep Iterative Search)
# ─────────────────────────────────────────────────────────────────────

DEEP_RESEARCH_SYSTEM = "You are an analytical assistant. Gather comprehensive information to solve the user's problem. You can issue search queries or declare that you have enough information. Output ONLY valid JSON."
def deep_research_prompt(state: PipelineState, current_knowledge: list[dict], iteration: int, max_iterations: int) -> str:
    knowledge_str = json.dumps(current_knowledge, indent=2) if current_knowledge else "No information gathered yet."
    return f'{get_language_instruction(state)}\n\nProblem: {_wrap_user_input(state.problem)}\n\nIteration: {iteration} of {max_iterations}\n\nCurrent Knowledge Gathered:\n{knowledge_str}\n\nAnalyze the current knowledge. If you need more information to fully answer the problem, generate up to 3 highly specific, SEO-friendly search queries. If you have enough information, or if you have reached the maximum iterations, set the action to "done".\n\nOutput JSON: {{"action": "search|done", "queries": ["<query1>", "<query2>"], "reasoning": "<why you chose this action>"}}'

# ─────────────────────────────────────────────────────────────────────
# COT DETECTION (for RAG Context Vetting)
# ─────────────────────────────────────────────────────────────────────

COT_DETECTION_SYSTEM = "You are an analytical assistant. Identify potentially unsubstantiated, factually incorrect, or overly speculative statements in the provided text. Output ONLY valid JSON."

def cot_detection_prompt(state: PipelineState, retrieved_text: str) -> str:
    return f'{get_language_instruction(state)}\n\nProblem: {_wrap_user_input(state.problem)}\n\nReview the following retrieved text. Identify any statements that seem potentially unsubstantiated, factually incorrect, or overly speculative. For each identified statement, provide a brief explanation of your reasoning. If no issues are found, return an empty list.\n\nRetrieved Text:\n{retrieved_text}\n\nOutput JSON: {{"flags": [{{"statement": "<problematic statement>", "reasoning": "<why it\'s problematic>"}}]}}'


# ─────────────────────────────────────────────────────────────────────
# ITERATIVE CONTEXT GATHERING (for _phase_context_vetting)
# ─────────────────────────────────────────────────────────────────────

ITERATIVE_CONTEXT_SYSTEM = "You are an analytical assistant. Gather context for a reasoning problem and determine if you have enough information or if more searches are needed. Output ONLY valid JSON."

def iterative_context_prompt(state: PipelineState, current_results: list[dict], iteration: int, max_iterations: int) -> str:
    results_str = json.dumps(current_results, indent=2) if current_results else "No results yet."
    return f'{get_language_instruction(state)}\n\nProblem: {_wrap_user_input(state.problem)}\n\nIteration: {iteration} of {max_iterations}\n\nCurrent Search Results:\n{results_str}\n\nAnalyze the current results. Do you have enough relevant information to provide a comprehensive answer? If yes, set action to "done". If you need more information, provide up to 3 specific search queries to fill the gaps.\n\nOutput JSON: {{"action": "search|done", "queries": ["<query1>", "<query2>"], "reasoning": "<why you need more info or have enough>"}}'


# ─────────────────────────────────────────────────────────────────────
# DEEP READ (for critical source scraping)
# ─────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────
# RECOVERY PATH (cross-verification of high-penalty candidates)
# ─────────────────────────────────────────────────────────────────────

CROSS_VERIFICATION_SYSTEM = "You are an analytical assistant. Identify specific factual errors, unsupported claims, or logical inconsistencies in a proposed solution. Be precise and cite exact problems. Output ONLY valid JSON."

def cross_verification_prompt(state: PipelineState, candidate_solution: dict) -> str:
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Original Problem: {_wrap_user_input(state.problem)}\n\n'
        f'Candidate Solution to Verify:\n{json.dumps(candidate_solution, indent=2)}\n\n'
        f'Identify any claims made with high confidence that are factually incorrect, '
        f'logically unsound, or unsubstantiated. Be specific.\n\n'
        f'Output JSON: {{"verified": <true|false>, "verification_findings": ["<issue1>", "<issue2>"], "summary": "<one sentence>"}}'
    )


# ─────────────────────────────────────────────────────────────────────
# DEEP READ (for critical source scraping)
# ─────────────────────────────────────────────────────────────────────

DEEP_READ_SYSTEM = "You are an analytical assistant. Extract and summarize key information from web pages. Provide a structured summary of the page content relevant to the user's problem. Output ONLY valid JSON."

SHALLOW_READ_SYSTEM = "You are an analytical assistant. Infer the content of a web page from its title and snippet. Provide a brief summary. Output ONLY valid JSON."


def deep_read_prompt(state: PipelineState, url: str, title: str, content: str) -> str:
    trimmed = content[:TRUNCATION.DEEP_READ]
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Original Problem: {_wrap_user_input(state.problem)}\n\n'
        f'Source:\nURL: {url}\nTitle: {title}\n\n'
        f'Page Content (first 8000 chars):\n{_wrap_external_content(trimmed)}\n\n'
        f'Extract the key information from this page that is relevant to the problem. '
        f'If the page is irrelevant, too short, or lacks substantive content, set "summary" to "INSUFFICIENT".\n\n'
        f'Output ONLY valid JSON with this exact structure:\n'
        f'{{\n'
        f'  "summary": "<comprehensive summary or INSUFFICIENT>",\n'
        f'  "key_facts": ["<fact1>", "<fact2>"],\n'
        f'  "relevant_quotes": ["<quote1>"]\n'
        f'}}'
    )


def shallow_read_prompt(state: PipelineState, url: str, title: str, snippet: str) -> str:
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Original Problem: {_wrap_user_input(state.problem)}\n\n'
        f'We could not fetch the full page. Based on the title and snippet below, '
        f'provide a brief summary of what this source likely contains. '
        f'If it seems irrelevant, return "INSUFFICIENT".\n\n'
        f'URL: {url}\n'
        f'Title: {title}\n'
        f'Snippet: {_wrap_external_content(snippet)}\n\n'
        f'Output ONLY valid JSON:\n'
        f'{{\n'
        f'  "summary": "<brief summary or INSUFFICIENT>",\n'
        f'  "key_facts": [],\n'
        f'  "relevant_quotes": []\n'
        f'}}'
    )


# ─────────────────────────────────────────────────────────────────────
# A5: DEBATE — CROSS-EXAMINATION
# ─────────────────────────────────────────────────────────────────────

DEBATE_CROSS_SYSTEM = "You are an analytical assistant. Challenge specific claims with evidence. Be precise and direct. Output ONLY valid JSON."

def debate_cross_examine_prompt(state: PipelineState, side: str, opponent_claims: list) -> str:
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Problem: {_wrap_user_input(state.problem)}\n\n'
        f'You are Side {side}. Your opponent made these claims:\n'
        f'{json.dumps(opponent_claims, indent=2)}\n\n'
        f'Challenge each claim with counter-evidence or logical contradiction.\n\n'
        f'Output JSON: {{"side": "{side}", "challenges": ['
        f'{{"claim": "<claim>", "challenge": "<counter-evidence>", "verdict": "REFUTED|WEAKENED|STANDS"}}]}}'
    )


# ─────────────────────────────────────────────────────────────────────
# B1: PRE-MORTEM ANALYSIS
# ─────────────────────────────────────────────────────────────────────

PRE_MORTEM_FAILURE_SYSTEM = "You are an analytical assistant. Assume failure has already occurred and reconstruct why. Be specific and unflinching. Output ONLY valid JSON."

def pre_mortem_failure_prompt(state: PipelineState) -> str:
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Problem: {_wrap_user_input(state.problem)}\n\n'
        f'It is exactly 1 year later. The solution to this problem catastrophically failed. '
        f'Write the post-mortem as if it already happened. Be vivid, specific, and brutally honest.\n\n'
        f'Output JSON: {{"scenario": "<failure scenario name>", '
        f'"what_happened": "<narrative of the failure>", '
        f'"immediate_triggers": ["<trigger>"], '
        f'"affected_stakeholders": ["<stakeholder>"], '
        f'"severity": "catastrophic|severe|moderate"}}'
    )

PRE_MORTEM_BACKTRACK_SYSTEM = "You are an analytical assistant. Given a failure, identify the single most critical decision that led to it. Output ONLY valid JSON."

def pre_mortem_backtrack_prompt(state: PipelineState) -> str:
    failure = state.pre_mortem_state.get("failure_narrative", {})
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Original Problem: {_wrap_user_input(state.problem)}\n\n'
        f'Post-Mortem:\n{json.dumps(failure, indent=2)}\n\n'
        f'Trace back to the single initial decision that was the pivot point. '
        f'What seemingly reasonable choice, made early, set this failure in motion?\n\n'
        f'Output JSON: {{"pivot_decision": "<the decision>", '
        f'"decision_point": "<when it was made>", '
        f'"why_it_seemed_reasonable": "<the reason>", '
        f'"cascade": ["<cascade step>"]}}'
    )

PRE_MORTEM_SIGNALS_SYSTEM = "You are an analytical assistant. Identify observable signals that would have predicted failure before it happened. Output ONLY valid JSON."

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

PRE_MORTEM_REDESIGN_SYSTEM = "You are an analytical assistant. Redesign the original solution hardened against the identified failure modes. Output ONLY valid JSON."

def pre_mortem_redesign_prompt(state: PipelineState) -> str:
    pm = state.pre_mortem_state
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Problem: {_wrap_user_input(state.problem)}\n\n'
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

BAYESIAN_PRIOR_SYSTEM = "You are an analytical assistant. Elicit prior probability distributions over competing hypotheses. Be explicit about uncertainty. Output ONLY valid JSON."

def bayesian_prior_prompt(state: PipelineState) -> str:
    decomp = state.decomposition or {}
    if isinstance(decomp, dict):
        sub_problems = [step.get("action", "") for step in decomp.get("causal_chain", [])]
    else:
        sub_problems = [sp.description for sp in (decomp.sub_problems if decomp else [])]
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Problem: {_wrap_user_input(state.problem)}\n\n'
        f'Sub-problems:\n{json.dumps(sub_problems, indent=2)}\n\n'
        f'Identify 2-4 competing hypotheses that could explain or solve this problem. '
        f'Assign prior probability P(H) to each (must sum to approximately 1.0). '
        f'Explain your reasoning for each prior.\n\n'
        f'Output JSON: {{"hypotheses": [{{"id": "H1", "statement": "<hypothesis>", '
        f'"prior_probability": 0.4, "reasoning": "<why this prior>"}}]}}'
    )

BAYESIAN_LIKELIHOOD_SYSTEM = "You are an analytical assistant. For each hypothesis, assess the likelihood of key observations. Output ONLY valid JSON."

def bayesian_likelihood_prompt(state: PipelineState) -> str:
    hypotheses = state.bayesian_state.get("hypotheses_with_priors", [])
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Problem: {_wrap_user_input(state.problem)}\n\n'
        f'Hypotheses:\n{json.dumps(hypotheses, indent=2)}\n\n'
        f'Identify 3-5 key observations or pieces of evidence relevant to this problem. '
        f'For each observation, assess P(E|H) and P(E|not-H) for each hypothesis.\n\n'
        f'Output JSON: {{"observations": ["<obs 1>"], "likelihoods": [{{"observation": "<obs>", '
        f'"hypothesis_id": "H1", "p_e_given_h": 0.8, "p_e_given_not_h": 0.2, '
        f'"reasoning": "<why>"}}]}}'
    )

BAYESIAN_POSTERIOR_SYSTEM = "You are an analytical assistant. Apply Bayes' theorem to compute posterior probabilities. Show your reasoning. Output ONLY valid JSON."

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

BAYESIAN_SENSITIVITY_SYSTEM = "You are an analytical assistant. Test which prior assumptions most change the posterior if they are wrong. Output ONLY valid JSON."

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

DIALECTICAL_THESIS_SYSTEM = "You are an analytical assistant. Articulate the strongest possible affirmative position. Be rigorous and committed. Output ONLY valid JSON."

def dialectical_thesis_prompt(state: PipelineState) -> str:
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Problem: {_wrap_user_input(state.problem)}\n\n'
        f'Articulate the strongest possible affirmative thesis position. '
        f'Be fully committed — this is the strongest case FOR one approach, not a balanced view.\n\n'
        f'Output JSON: {{"thesis": "<strongest affirmative position>", '
        f'"key_commitments": ["<commitment 1>"], '
        f'"assumptions": ["<assumption>"]}}'
    )

DIALECTICAL_ANTITHESIS_SYSTEM = "You are an analytical assistant. Expose the internal contradictions of a thesis. Negate its commitments rigorously. Output ONLY valid JSON."

def dialectical_antithesis_prompt(state: PipelineState) -> str:
    thesis = state.dialectical_state.get("thesis", "")
    commitments = state.dialectical_state.get("key_commitments", [])
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Problem: {_wrap_user_input(state.problem)}\n\n'
        f'Thesis: {thesis}\n\n'
        f'Key Commitments: {json.dumps(commitments, indent=2)}\n\n'
        f'Expose the internal contradictions of this thesis. '
        f'Negate each commitment. Show why this position is untenable.\n\n'
        f'Output JSON: {{"antithesis": "<negation of thesis>", '
        f'"contradictions_exposed": ["<contradiction in thesis>"], '
        f'"negated_commitments": [{{"commitment": "<c>", "negation": "<n>"}}]}}'
    )

DIALECTICAL_CONTRADICTIONS_SYSTEM = "You are an analytical assistant. Classify which contradictions are truly irreconcilable and which can be transcended at a higher level. Output ONLY valid JSON."

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

DIALECTICAL_AUFHEBUNG_SYSTEM = "You are an analytical assistant. Achieve qualitative transcendence, NOT compromise. Preserve the truths of both positions at a higher level. Output ONLY valid JSON."

def dialectical_aufhebung_prompt(state: PipelineState) -> str:
    d = state.dialectical_state
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Problem: {_wrap_user_input(state.problem)}\n\n'
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


# ─────────────────────────────────────────────────────────────────────
# B4: ANALOGICAL REASONING (Structure-Mapping Theory, TRIZ, Biomimicry)
# ─────────────────────────────────────────────────────────────────────

ANALOGICAL_ABSTRACTION_SYSTEM = (
    "You are a structural abstraction expert trained in Gentner's structure-mapping theory. "
    "Extract the deep, domain-independent structure of a problem. "
    "Focus on constraints, objectives, actors, and dynamics — not surface features. " + JSON_ONLY_FOOTER
)


def analogical_abstraction_prompt(state: PipelineState) -> str:
    decomp = state.decomposition or {}
    if isinstance(decomp, dict):
        sub_problems = [step.get("action", "") for step in decomp.get("causal_chain", [])]
    else:
        sub_problems = [sp.description for sp in (decomp.sub_problems if decomp else [])]
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Problem: {_wrap_user_input(state.problem)}\n\n'
        f'Sub-problems:\n{json.dumps(sub_problems, indent=2)}\n\n'
        f'Extract the abstract structural signature of this problem, ignoring domain-specific surface features. '
        f'Identify the deep constraints, objectives, actors, and core dynamics.\n\n'
        f'Output JSON: {{"abstract_structure": "<structural description>", '
        f'"constraints": ["<constraint>"], '
        f'"objectives": ["<objective>"], '
        f'"actors": ["<actor/agent>"], '
        f'"core_dynamics": ["<dynamic/tension>"], '
        f'"structural_type": "<optimization|resource_allocation|coordination|competition|emergent|etc>"}}'
    )


ANALOGICAL_DOMAIN_SEARCH_SYSTEM = (
    "You are an expert in cross-domain pattern recognition — spanning biology, physics, engineering, "
    "economics, military history, computer science, and social systems. "
    "Given an abstract problem structure, identify domains where an isomorphic problem has already been solved. " + JSON_ONLY_FOOTER
)


def analogical_domain_search_prompt(state: PipelineState) -> str:
    a = state.analogical_state
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Problem: {_wrap_user_input(state.problem)}\n\n'
        f'Abstract structure: {a.get("abstract_structure", "")}\n'
        f'Structural type: {a.get("structural_type", "")}\n'
        f'Core dynamics: {json.dumps(a.get("core_dynamics", []), indent=2)}\n\n'
        f'Search for domains (biology, physics, engineering, military, economics, computer science, history, social systems) '
        f'where an isomorphic problem — same abstract structure — has been solved. '
        f'Rank by structural relevance, not surface similarity.\n\n'
        f'Output JSON: {{"source_domains": [{{'
        f'"domain": "<field name>", '
        f'"solved_problem": "<problem solved in that domain>", '
        f'"key_mechanism": "<the mechanism that solved it>", '
        f'"historical_example": "<specific example>", '
        f'"relevance_score": "<high|medium|low>", '
        f'"structural_fit": "<why the structures match>"'
        f'}}]}}'
    )


ANALOGICAL_MAPPING_SYSTEM = (
    "You are a structure-mapping theorist. "
    "Map the source domain's solution elements onto the target problem's elements. "
    "Identify object-attribute mappings, relational mappings, and higher-order relational mappings. " + JSON_ONLY_FOOTER
)


def analogical_mapping_prompt(state: PipelineState) -> str:
    a = state.analogical_state
    domains = a.get("source_domains", [])
    best_domain = domains[0] if domains else {}
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Target problem: {_wrap_user_input(state.problem)}\n\n'
        f'Abstract structure: {a.get("abstract_structure", "")}\n'
        f'Constraints: {json.dumps(a.get("constraints", []), indent=2)}\n'
        f'Objectives: {json.dumps(a.get("objectives", []), indent=2)}\n\n'
        f'Best source domain: {json.dumps(best_domain, indent=2)}\n\n'
        f'Map each element of the source domain solution onto the target problem. '
        f'Classify each mapping as: object (entity-to-entity), relational (relation-to-relation), '
        f'or higher-order (system-level pattern). '
        f'Flag any elements that do NOT map cleanly.\n\n'
        f'Output JSON: {{"analogy_mappings": [{{'
        f'"source_element": "<element in source domain>", '
        f'"target_element": "<corresponding element in target problem>", '
        f'"mapping_type": "<object|relational|higher-order>", '
        f'"confidence": "<high|medium|low>", '
        f'"mapping_rationale": "<why these correspond>"'
        f'}}], '
        f'"unmapped_elements": ["<source element with no clean target>"], '
        f'"mapping_quality": "<strong|partial|weak>"}}'
    )


ANALOGICAL_TRANSFER_SYSTEM = (
    "You are an expert in cross-domain knowledge transfer and TRIZ-style contradiction resolution. "
    "Take an analogical mapping and produce a concrete adapted solution for the target problem. "
    "Be explicit about what transfers cleanly, what must be adapted, and where the analogy breaks. " + JSON_ONLY_FOOTER
)


def analogical_transfer_prompt(state: PipelineState) -> str:
    a = state.analogical_state
    domains = a.get("source_domains", [])
    best_domain = domains[0] if domains else {}
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Target problem: {_wrap_user_input(state.problem)}\n\n'
        f'Source domain: {best_domain.get("domain", "")} — {best_domain.get("key_mechanism", "")}\n\n'
        f'Analogy mappings:\n{json.dumps(a.get("analogy_mappings", []), indent=2)}\n\n'
        f'Unmapped elements: {json.dumps(a.get("unmapped_elements", []), indent=2)}\n\n'
        f'Now perform the transfer: adapt the source mechanism to the target problem. '
        f'Be concrete — state the actual proposed solution, not just that "it could be applied". '
        f'Then explicitly state where the analogy breaks (unmapped elements, domain constraints that do not transfer).\n\n'
        f'Output JSON: {{'
        f'"transferred_solution": "<the concrete adapted solution>", '
        f'"transfer_steps": ["<step 1>", "<step 2>"], '
        f'"adaptations_required": ["<what must change vs. source domain>"], '
        f'"broken_analogies": ["<where the analogy fails and why>"], '
        f'"confidence": "<high|medium|low>", '
        f'"caveats": ["<important caveat>"]}}'
    )


# ─────────────────────────────────────────────────────────────────────
# B5: DELPHI METHOD (Dalkey & Helmer, 1963)
# ─────────────────────────────────────────────────────────────────────

DELPHI_EXPERT_SYSTEM = (
    "You are an independent expert forecaster. Make your estimate without knowing what other experts think. "
    "Be specific and provide a numeric estimate where possible. " + JSON_ONLY_FOOTER
)


def delphi_round1_prompt(state: "PipelineState", expert_num: int) -> str:
    decomp = state.decomposition or {}
    if isinstance(decomp, dict):
        sub_problems = [step.get("action", "") for step in decomp.get("causal_chain", [])]
    else:
        sub_problems = [sp.description for sp in (decomp.sub_problems if decomp else [])]
    return (
        f'{get_language_instruction(state)}\n\n'
        f'You are Expert {expert_num} of 4 independent forecasters.\n\n'
        f'Problem: {_wrap_user_input(state.problem)}\n\n'
        f'Sub-problems:\n{json.dumps(sub_problems, indent=2)}\n\n'
        f'Provide your independent estimate/forecast. If numeric, provide a specific number. '
        f'Explain your reasoning. Do NOT anchor to any consensus — you are working independently.\n\n'
        f'Output JSON: {{"estimate_value": <number or null if qualitative>, '
        f'"estimate_label": "<your estimate in words>", '
        f'"confidence": "high|medium|low", '
        f'"key_assumptions": ["<assumption>"], '
        f'"reasoning": "<why you believe this>"}}'
    )


DELPHI_AGGREGATION_SYSTEM = (
    "You are a statistical aggregator. Combine expert estimates into a summary with median, IQR, and outlier identification. "
    "Be objective. Output ONLY valid JSON."
)


def delphi_aggregation_prompt(state: "PipelineState") -> str:
    estimates = state.delphi_state.get("round_1_estimates", [])
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Problem: {_wrap_user_input(state.problem)}\n\n'
        f'Expert estimates (anonymous — do not reveal which expert said what in outputs):\n'
        f'{json.dumps(estimates, indent=2)}\n\n'
        f'Aggregate these estimates. Identify: the central tendency (median or modal theme), '
        f'the spread (range or IQR), and which estimate is most different from the others.\n\n'
        f'Output JSON: {{"median": null, "iqr": null, '
        f'"central_theme": "<qualitative central estimate>", '
        f'"spread": "<qualitative description of disagreement>", '
        f'"outlier_expert": "<expert_1|expert_2|expert_3|expert_4>", '
        f'"outlier_reasoning": "<why this estimate is an outlier>"}}'
    )


DELPHI_REVISION_SYSTEM = (
    "You are an expert revising your estimate after seeing anonymous aggregated results. "
    "You may revise toward consensus or defend your original position with reasoning. " + JSON_ONLY_FOOTER
)


def delphi_round2_prompt(state: "PipelineState", expert_id: str) -> str:
    stats = state.delphi_state.get("aggregated_stats", {})
    original = next(
        (e for e in state.delphi_state.get("round_1_estimates", []) if e.get("expert_id") == expert_id),
        {}
    )
    return (
        f'{get_language_instruction(state)}\n\n'
        f'You are {expert_id}. You previously estimated: {original.get("estimate_label", "unknown")}\n\n'
        f'Anonymous group statistics:\n'
        f'- Median: {stats.get("median", stats.get("central_theme", "unknown"))}\n'
        f'- Spread (IQR): {stats.get("iqr", stats.get("spread", "unknown"))}\n\n'
        f'You can see the group median. '
        f'Do you revise your estimate, or do you defend your original position?\n\n'
        f'Output JSON: {{"revised_estimate": <number or null>, '
        f'"revised_label": "<your revised estimate in words>", '
        f'"position": "revised|maintained", '
        f'"rationale": "<why you revised or maintained>", '
        f'"remaining_uncertainty": "<what would change your estimate>"}}'
    )


DELPHI_CONVERGENCE_SYSTEM = (
    "You are a Delphi facilitator checking if expert estimates have converged to consensus. " + JSON_ONLY_FOOTER
)


def delphi_convergence_prompt(state: "PipelineState") -> str:
    r2 = state.delphi_state.get("round_2_estimates", [])
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Round 2 estimates:\n{json.dumps(r2, indent=2)}\n\n'
        f'Have the experts converged to a consensus? '
        f'Convergence means the estimates are close enough to support a single recommendation.\n\n'
        f'Output JSON: {{"converged": "<true|false>", '
        f'"consensus_label": "<the converged estimate if converged>", '
        f'"remaining_disagreement": "<what experts still disagree on>", '
        f'"convergence_quality": "strong|moderate|weak"}}'
    )


DELPHI_DISSENT_SYSTEM = (
    "You are the outlier expert. Document your dissenting rationale explicitly and professionally. "
    "Explain what the consensus is missing. Output ONLY valid JSON."
)


def delphi_dissent_prompt(state: "PipelineState") -> str:
    stats = state.delphi_state.get("aggregated_stats", {})
    consensus = state.delphi_state.get("consensus", {})
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Problem: {_wrap_user_input(state.problem)}\n\n'
        f'Group consensus: {consensus.get("median", consensus.get("consensus_label", "unknown"))}\n'
        f'Your estimate differs from the group median by: {stats.get("outlier_distance", stats.get("iqr", "unknown"))} units.\n\n'
        f'As the outlier expert, document your dissenting rationale. '
        f'What does the consensus miss? What evidence supports your position?\n\n'
        f'Output JSON: {{"dissenting_estimate": "<your position>", '
        f'"what_consensus_misses": ["<missing factor>"], '
        f'"evidence_for_dissent": ["<evidence>"], '
        f'"conditions_for_revision": "<what would change your mind>", '
        f'"minority_report": "<1-2 sentence professional dissent statement>"}}'
    )


# ═══════════════════════════════════════════════════════════════════════
# v2.2 NEW METHODS: Chain-of-Verification (CoVe)
# ═══════════════════════════════════════════════════════════════════════

COVE_DRAFT_SYSTEM = (
    "You are a knowledgeable analyst. Draft a comprehensive initial answer to the problem. "
    "Break your answer into explicit, verifiable claims. " + JSON_ONLY_FOOTER
)


def cove_draft_prompt(state: PipelineState) -> str:
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Problem: {_wrap_user_input(state.problem)}\n\n'
        f'Draft an initial answer. Break it into explicit claims that can be independently verified. '
        f'For each claim, assign a confidence score (0.0-1.0).\n\n'
        f'Output JSON: {{"draft_answer": "<full answer text>", '
        f'"claims": [{{"claim": "<claim text>", "confidence": 0.8}}]}}'
    )


COVE_VERIFY_SYSTEM = (
    "You are a skeptical fact-checker. Given a draft answer with claims, generate specific, "
    "independent verification questions for EACH claim. Do not trust the original answer. " + JSON_ONLY_FOOTER
)


def cove_verify_prompt(state: PipelineState) -> str:
    draft = state.cove_state.get("draft_answer", "")
    claims = state.cove_state.get("claims", [])
    claims_json = json.dumps(claims, indent=2) if claims else "[]"
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Original Problem: {_wrap_user_input(state.problem)}\n\n'
        f'Draft Answer:\n{_wrap_external_content(draft)}\n\n'
        f'Claims to verify:\n{claims_json}\n\n'
        f'For EACH claim above, generate 1-2 specific verification questions that would '
        f'independently test whether the claim is true. The questions must be answerable '
        f'without referring to the draft answer.\n\n'
        f'Output JSON: {{"verification_questions": [{{'
        f'"question": "<verification question>", '
        f'"target_claim": "<claim being tested>", '
        f'"expected_evidence_type": "<fact|statistic|authority|logic>"'
        f'}}]}}'
    )


COVE_ANSWER_SYSTEM = (
    "You are an independent researcher. Answer the verification questions based on your own "
    "knowledge. Do not refer to the draft answer. Be explicit about whether evidence supports "
    "or contradicts each claim. " + JSON_ONLY_FOOTER
)


def cove_answer_prompt(state: PipelineState) -> str:
    questions = state.cove_state.get("verification_questions", [])
    questions_json = json.dumps(questions, indent=2) if questions else "[]"
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Original Problem: {_wrap_user_input(state.problem)}\n\n'
        f'Answer these verification questions INDEPENDENTLY, using your own knowledge. '
        f'Do not refer to any draft answer. For each question, explicitly state whether '
        f'the evidence supports, contradicts, or is insufficient to evaluate the target claim.\n\n'
        f'Questions:\n{questions_json}\n\n'
        f'Output JSON: {{"answers": [{{'
        f'"question": "<question text>", '
        f'"answer": "<your independent answer>", '
        f'"verdict": "<supports|contradicts|insufficient>", '
        f'"confidence": 0.8, '
        f'"reasoning": "<why>"'
        f'}}]}}'
    )


COVE_REVISE_SYSTEM = (
    "You are a careful editor. Given a draft answer and independent verification results, "
    "revise the answer to correct errors, add caveats, and improve accuracy. " + JSON_ONLY_FOOTER
)


def cove_revise_prompt(state: PipelineState) -> str:
    draft = state.cove_state.get("draft_answer", "")
    answers = state.cove_state.get("verification_answers", [])
    answers_json = json.dumps(answers, indent=2) if answers else "[]"
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Original Problem: {_wrap_user_input(state.problem)}\n\n'
        f'Draft Answer:\n{_wrap_external_content(draft)}\n\n'
        f'Independent Verification Results:\n{_wrap_external_content(answers_json)}\n\n'
        f'Revise the draft answer based on the verification results. '
        f'Correct any contradicted claims, add caveats for insufficient evidence, '
        f'and strengthen supported claims. Document what changed and why.\n\n'
        f'Output JSON: {{"revised_answer": "<revised full answer>", '
        f'"changes_made": ["<change description>"], '
        f'"remaining_uncertainties": ["<uncertainty>"], '
        f'"upgraded_claims": ["<claim that was strengthened>"], '
        f'"retracted_claims": ["<claim that was removed or corrected>"]}}'
    )


# ═══════════════════════════════════════════════════════════════════════
# v2.2 NEW METHODS: Skeleton-of-Thought (SoT)
# ═══════════════════════════════════════════════════════════════════════

SOT_SKELETON_SYSTEM = (
    "You are an expert problem decomposer. Generate a skeleton outline of sub-problems "
    "that collectively solve the main problem. Each sub-problem should be independent "
    "and solvable in parallel. " + JSON_ONLY_FOOTER
)


def sot_skeleton_prompt(state: PipelineState) -> str:
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Problem: {_wrap_user_input(state.problem)}\n\n'
        f'Decompose this problem into 3-5 sub-problems that can be solved independently '
        f'and in parallel. Each sub-problem should have a clear scope, inputs, and expected output. '
        f'The sub-problems should collectively cover all aspects of the main problem.\n\n'
        f'Output JSON: {{"sub_problems": [{{'
        f'"id": "1", '
        f'"description": "<sub-problem>", '
        f'"inputs": ["<input>"], '
        f'"expected_output": "<output description>", '
        f'"rationale": "<why this decomposition>"'
        f'}}]}}'
    )


SOT_SOLVE_SYSTEM = (
    "You are a specialist solver. Solve the assigned sub-problem thoroughly and concisely. "
    + JSON_ONLY_FOOTER
)


def sot_solve_prompt(state: PipelineState, sub_problem: dict) -> str:
    skeleton = state.sot_state.get("sub_problems", [])
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Original Problem: {_wrap_user_input(state.problem)}\n\n'
        f'Full Skeleton: {json.dumps(skeleton, indent=2)}\n\n'
        f'YOUR ASSIGNED SUB-PROBLEM:\n'
        f'ID: {sub_problem.get("id", "?")}\n'
        f'Description: {sub_problem.get("description", "")}\n'
        f'Inputs: {json.dumps(sub_problem.get("inputs", []))}\n'
        f'Expected Output: {sub_problem.get("expected_output", "")}\n\n'
        f'Solve this sub-problem thoroughly. Your solution will be combined with others '
        f'to form the complete answer.\n\n'
        f'Output JSON: {{"sub_problem_id": "{sub_problem.get("id", "")}", '
        f'"solution": "<detailed solution>", '
        f'"key_insights": ["<insight>"], '
        f'"assumptions": ["<assumption>"]}}'
    )


SOT_ASSEMBLE_SYSTEM = (
    "You are a master synthesizer. Combine multiple sub-problem solutions into a coherent, "
    "unified answer. Ensure smooth transitions and resolve any contradictions. " + JSON_ONLY_FOOTER
)


def sot_assemble_prompt(state: PipelineState) -> str:
    solutions = state.sot_state.get("solutions", [])
    solutions_json = json.dumps(solutions, indent=2) if solutions else "[]"
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Original Problem: {_wrap_user_input(state.problem)}\n\n'
        f'Sub-problem Solutions:\n{_wrap_external_content(solutions_json)}\n\n'
        f'Assemble these sub-problem solutions into a single, coherent, comprehensive answer. '
        f'Ensure smooth transitions between sections, resolve any contradictions, '
        f'and maintain logical flow. The assembled answer should stand alone.\n\n'
        f'Output JSON: {{"assembled_answer": "<full unified answer>", '
        f'"transitions": ["<how sections connect>"], '
        f'"resolved_conflicts": ["<conflict and resolution>"], '
        f'"meta_observation": "<insight about the whole>"}}'
    )


# ═══════════════════════════════════════════════════════════════════════
# v2.2 NEW METHODS: Tree-of-Thoughts (ToT)
# ═══════════════════════════════════════════════════════════════════════

TOT_DECOMPOSE_SYSTEM = (
    "You are a strategic planner. Decompose the problem into sequential decision points. "
    + JSON_ONLY_FOOTER
)


def tot_decompose_prompt(state: PipelineState) -> str:
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Problem: {_wrap_user_input(state.problem)}\n\n'
        f'Identify the key sequential decision points in this problem. '
        f'Each decision point should have 2-3 possible candidate actions. '
        f'Limit to at most 3 decision points to control token cost.\n\n'
        f'Output JSON: {{"decision_points": [{{'
        f'"id": "dp1", '
        f'"description": "<what decision must be made>", '
        f'"candidates": [{{"action": "<action>", "rationale": "<why>"}}]'
        f'}}]}}'
    )


TOT_GENERATE_SYSTEM = (
    "You are a creative strategist. Generate diverse candidate next-steps for the given decision point. "
    + JSON_ONLY_FOOTER
)


def tot_generate_prompt(state: PipelineState, decision_point: dict) -> str:
    path_so_far = state.tot_state.get("current_path", [])
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Problem: {_wrap_user_input(state.problem)}\n\n'
        f'Decisions made so far: {json.dumps(path_so_far, indent=2)}\n\n'
        f'Current Decision Point: {decision_point.get("description", "")}\n\n'
        f'Generate 2-3 diverse, high-quality candidate actions for this decision point. '
        f'Each candidate should represent a genuinely different strategic direction.\n\n'
        f'Output JSON: {{"candidates": [{{'
        f'"candidate_id": "c1", '
        f'"action": "<action description>", '
        f'"expected_outcome": "<what happens>", '
        f'"risks": ["<risk>"], '
        f'"prerequisites": ["<prerequisite>"]'
        f'}}]}}'
    )


TOT_EVALUATE_SYSTEM = (
    "You are a critical evaluator. Score each candidate action on multiple dimensions. "
    + JSON_ONLY_FOOTER
)


def tot_evaluate_prompt(state: PipelineState, candidates: list) -> str:
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Problem: {_wrap_user_input(state.problem)}\n\n'
        f'Candidate Actions:\n{json.dumps(candidates, indent=2)}\n\n'
        f'Evaluate EACH candidate on a scale of 0-10 for: '
        f'feasibility, expected_value, risk_level (lower is better), and alignment_with_goal. '
        f'Recommend the best candidate and explain why.\n\n'
        f'Output JSON: {{"evaluations": [{{'
        f'"candidate_id": "c1", '
        f'"feasibility": 8, '
        f'"expected_value": 7, '
        f'"risk_level": 4, '
        f'"alignment_with_goal": 9, '
        f'"score": 7.5, '
        f'"verdict": "<proceed|reject|caution>"'
        f'}}], '
        f'"best_candidate": "<candidate_id>", '
        f'"recommendation": "<explanation>"}}'
    )


TOT_BACKTRACK_SYSTEM = (
    "You are a strategic analyst. Given evaluation results, decide whether to proceed, "
    "backtrack, or terminate. " + JSON_ONLY_FOOTER
)


def tot_backtrack_prompt(state: PipelineState) -> str:
    path = state.tot_state.get("current_path", [])
    evaluations = state.tot_state.get("evaluations", [])
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Problem: {_wrap_user_input(state.problem)}\n\n'
        f'Current path: {json.dumps(path, indent=2)}\n\n'
        f'Evaluations: {json.dumps(evaluations, indent=2)}\n\n'
        f'Based on the evaluations, decide: (1) CONTINUE with the best candidate, '
        f'(2) BACKTRACK to a previous decision point and try a different branch, or '
        f'(3) TERMINATE with the current path as the final solution. '
        f'Provide reasoning.\n\n'
        f'Output JSON: {{"decision": "<continue|backtrack|terminate>", '
        f'"target_decision_point": "<if backtracking, which dp>", '
        f'"reasoning": "<why>", '
        f'"final_path": ["<action>"], '
        f'"confidence": 0.8}}'
    )


# ═══════════════════════════════════════════════════════════════════════
# v2.2 NEW METHODS: Program-of-Thoughts (PoT)
# ═══════════════════════════════════════════════════════════════════════

POT_GENERATE_SYSTEM = (
    "You are an expert programmer. Generate Python code to solve the given quantitative problem. "
    "The code should be self-contained, use only standard library, and include comments. "
    + JSON_ONLY_FOOTER
)


def pot_generate_prompt(state: PipelineState) -> str:
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Problem: {_wrap_user_input(state.problem)}\n\n'
        f'Write Python code to solve this problem computationally. '
        f'The code must be self-contained, use only Python standard library, '
        f'and handle edge cases. Include print statements for the final result. '
        f'Also provide a brief explanation of the approach.\n\n'
        f'Output JSON: {{"code": "<python code as string>", '
        f'"explanation": "<approach explanation>", '
        f'"expected_output_type": "<number|list|dict|boolean>"}}'
    )


POT_EXECUTE_SYSTEM = (
    "You are a code execution engine. Simulate or describe the execution of the given Python code. "
    "If actual execution is unavailable, trace through the code logically and produce the output. "
    + JSON_ONLY_FOOTER
)


def pot_execute_prompt(state: PipelineState) -> str:
    code = state.pot_state.get("code", "")
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Execute the following Python code and return the exact output. '
        f'If the code has errors, return the error message. '
        f'Trace through the execution step by step if needed.\n\n'
        f'Code:\n```python\n{code}\n```\n\n'
        f'Output JSON: {{"output": "<execution output>", '
        f'"success": true, '
        f'"error": "<error message if any>", '
        f'"intermediate_steps": ["<step result>"]}}'
    )


POT_INTERPRET_SYSTEM = (
    "You are an analytical interpreter. Given code execution results, explain what they mean "
    "in the context of the original problem. " + JSON_ONLY_FOOTER
)


def pot_interpret_prompt(state: PipelineState) -> str:
    code = state.pot_state.get("code", "")
    output = state.pot_state.get("execution_output", "")
    error = state.pot_state.get("execution_error", "")
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Original Problem: {_wrap_user_input(state.problem)}\n\n'
        f'Generated Code:\n```python\n{code}\n```\n\n'
        f'Execution Output:\n{_wrap_external_content(output)}\n\n'
        f'Error (if any): {_wrap_external_content(error)}\n\n'
        f'Interpret the execution results in the context of the original problem. '
        f'Explain what the output means, whether it fully answers the problem, '
        f'and what limitations or caveats exist.\n\n'
        f'Output JSON: {{"interpretation": "<explanation>", '
        f'"answer": "<final answer to the problem>", '
        f'"caveats": ["<caveat>"], '
        f'"confidence": 0.9}}'
    )


# ═══════════════════════════════════════════════════════════════════════
# v2.2 NEW METHODS: Self-Discover
# ═══════════════════════════════════════════════════════════════════════

SD_SELECT_SYSTEM = (
    "You are a meta-reasoning architect. Given a problem, select the reasoning modules "
    "that are most appropriate from the available inventory. " + JSON_ONLY_FOOTER
)


def sd_select_prompt(state: PipelineState) -> str:
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Problem: {_wrap_user_input(state.problem)}\n\n'
        f'Available reasoning modules:\n'
        f'- decomposition: break problem into sub-problems\n'
        f'- verification: fact-check claims\n'
        f'- analogy: find cross-domain parallels\n'
        f'- causal_analysis: identify cause-effect chains\n'
        f'- counterfactual: explore what-if scenarios\n'
        f'- abstraction: extract deep structure\n'
        f'- constraint_satisfaction: respect hard limits\n'
        f'- optimization: find best allocation\n\n'
        f'Select 3-5 modules that are MOST relevant to this problem. '
        f'Explain why each is needed and in what order they should be applied.\n\n'
        f'Output JSON: {{"selected_modules": [{{'
        f'"module": "<module_name>", '
        f'"rationale": "<why needed>", '
        f'"order": 1'
        f'}}], '
        f'"composition_strategy": "<how modules interact>"}}'
    )


SD_ADAPT_SYSTEM = (
    "You are a prompt engineer. Adapt the selected reasoning modules into concrete prompts "
    "and instructions for the current problem. " + JSON_ONLY_FOOTER
)


def sd_adapt_prompt(state: PipelineState) -> str:
    modules = state.self_discover_state.get("selected_modules", [])
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Problem: {_wrap_user_input(state.problem)}\n\n'
        f'Selected Modules: {json.dumps(modules, indent=2)}\n\n'
        f'Adapt each selected module into a concrete instruction or prompt '
        f'specific to this problem. The adapted instructions should be actionable '
        f'and clearly define inputs/outputs for each module.\n\n'
        f'Output JSON: {{"adapted_modules": [{{'
        f'"module": "<module_name>", '
        f'"instruction": "<concrete instruction>", '
        f'"input": "<what this module receives>", '
        f'"output": "<what this module produces>"'
        f'}}]}}'
    )


SD_IMPLEMENT_SYSTEM = (
    "You are an execution engine. Execute the adapted reasoning modules in sequence "
    "and synthesize their outputs into a final answer. " + JSON_ONLY_FOOTER
)


def sd_implement_prompt(state: PipelineState) -> str:
    adapted = state.self_discover_state.get("adapted_modules", [])
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Problem: {_wrap_user_input(state.problem)}\n\n'
        f'Adapted Module Instructions: {json.dumps(adapted, indent=2)}\n\n'
        f'Execute each module in sequence, passing outputs from one to the next. '
        f'After all modules complete, synthesize their collective output into a '
        f'coherent final answer. Document the contribution of each module.\n\n'
        f'Output JSON: {{"module_outputs": [{{'
        f'"module": "<name>", '
        f'"output": "<result>"'
        f'}}], '
        f'"final_answer": "<synthesized answer>", '
        f'"module_attribution": {{"<module>": "<contribution summary>"}}, '
        f'"confidence": 0.85}}'
    )


# ═══════════════════════════════════════════════════════════════════════
# v2.2 POST-SYNTHESIS ENHANCEMENT: Cross-Model Verification
# ═══════════════════════════════════════════════════════════════════════

POST_SYNTHESIS_VERIFY_SYSTEM = (
    "You are an independent fact-checker. Given a synthesized answer, generate verification "
    "questions and evaluate the answer's claims without referring to the original synthesis model. "
    + JSON_ONLY_FOOTER
)


def post_synthesis_verify_prompt(synthesis_text: str, state: PipelineState) -> str:
    return (
        f'{get_language_instruction(state)}\n\n'
        f'Synthesized Answer to Verify:\n{_wrap_external_content(synthesis_text)}\n\n'
        f'Generate 3-5 verification questions for the key claims in this answer. '
        f'Then evaluate each claim independently based on your own knowledge. '
        f'Flag any claims that appear unsupported, contradictory, or overstated.\n\n'
        f'Output JSON: {{"verification_questions": ["<question>"], '
        f'"evaluation": [{{'
        f'"claim": "<claim>", '
        f'"verdict": "<verified|hypothesis|incorrect|uncertain>", '
        f'"confidence": 0.8, '
        f'"notes": "<evaluation notes>"'
        f'}}], '
        f'"recommendations": ["<suggested improvement>"]}}'
    )
