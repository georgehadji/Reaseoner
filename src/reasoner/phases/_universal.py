from __future__ import annotations
import json
from reasoner.models import PipelineState
from reasoner.core.constants import JSON_ONLY_FOOTER, TRUNCATION, DEFAULT_SEARCH_RESULTS
from reasoner.phases._shared import (
    detect_language,
    get_language_instruction,
    _followup_context,
    _wrap_user_input,
    _wrap_external_content,
)

DISAMBIGUATION_SYSTEM = "You are an analytical assistant. Detect whether a problem is ambiguous and could be interpreted in multiple ways. Output ONLY valid JSON."

def disambiguation_prompt(problem: str, task_type: str | None) -> str:
    task_hint = f"Task type: {task_type}. " if task_type else ""
    return (
        f'Analyze whether the following problem is ambiguous or could be interpreted in multiple ways. '
        f'{task_hint}If ambiguous, explain why and provide a clearer rewritten version. If clear, state that it is unambiguous.\n\n'
        f'Problem: {_wrap_user_input(problem)}\n\n'
        f'Output JSON: {{"was_ambiguous": true/false, "rewritten_query": "<clearest version>", "reasoning": "<why>"}}'
    )

PROMPT_ENHANCEMENT_SYSTEM = "You are an analytical assistant. Rewrite the user's problem to make it clearer, more specific, and easier for an AI reasoning system to solve. Preserve the original intent, tone, and language. Output ONLY valid JSON."

def prompt_enhancement_prompt(problem: str, language: str) -> str:
    lang_instruction = get_language_instruction(PipelineState(problem="", language=language))
    return f'{lang_instruction}\n\nOriginal Problem:\n{_wrap_user_input(problem)}\n\nRewrite this problem to be clearer, more specific, and easier for a multi-step AI reasoning pipeline to solve. Preserve the original language and intent.\n\nOutput JSON: {{"enhanced_problem": "<rewritten problem>", "improvements": ["<what was improved>"]}}'

CLASSIFICATION_SYSTEM = "Classify task type. JSON only."
def classification_prompt(problem: str, language: str, state: PipelineState | None = None) -> str:
    lang_instruction = get_language_instruction(PipelineState(problem="", language=language))
    followup = _followup_context(state) if state else ""
    return (
        f'{lang_instruction}\n\nProblem:\n{_wrap_user_input(problem)}{followup}\n\n'
        f'Choose exactly ONE task type from: analytical, strategic, creative, technical, predictive, hybrid. '
        f'JSON: {{"task_type": "analytical", "rationale": "<why>", "language": "{language}"}}'
    )

DECOMPOSITION_SYSTEM = "Decompose problem into sub-problems. JSON only."
def decomposition_prompt(state: PipelineState) -> str:
    is_jury = "jury" in (state.preset_name or "")
    jury_instr = " Add jury_guidelines." if is_jury else ""
    web_context = f"\nWeb: {state.web_discovery_results[:TRUNCATION.KEY_INSIGHTS]}" if state.web_discovery_results else ""
    followup = _followup_context(state)
    
    return f'''{get_language_instruction(state)}

Problem: {_wrap_user_input(state.problem)}{web_context}{followup}
Decompose.{jury_instr}

JSON: {{"causal_chain": [{{"step": 1, "action": "<action>", "produces": ["<output>"]}}], "assumptions": [{{"text": "<assumption>", "label": "VERIFIED|HYPOTHESIS|UNKNOWN", "rationale": "<why this label>", "source_hint": "<source name or URL if VERIFIED>"}}], "failure_modes": ["<failure>"], "critical_sources": [{{"url": "<URL>", "reason": "<why it matters>"}}]}}

Rules: Max 5 steps. Surface assumptions with rationale. VERIFIED assumptions MUST cite a source_hint. If web results exist, list 1-2 critical_sources. Be specific.'''

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
    final_context = state.to_context_dict()
    if 'candidates' in final_context:
        final_context['candidates'] = [{"perspective": c['perspective'], "insights": c['key_insights']} for c in final_context['candidates']]

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
        sources_info = "\nWEB SOURCES (for citations):\n" + json.dumps([
            {"title": r.get("title", "Unknown"), "url": r.get("url", "")}
            for r in state.web_discovery_results[:DEFAULT_SEARCH_RESULTS]
        ], indent=2)

    method_hint = "Synthesize the best possible solution."
    followup = _followup_context(state)
    quality_note = f"\nCONTEXT QUALITY: {state.context_quality}\n" if state.context_quality and state.context_quality != "unknown" else ""

    return f'{get_language_instruction(state)}\n\nFinal Context:\n{_wrap_external_content(json.dumps(final_context, indent=2))}\n{_wrap_external_content(sources_info)}{followup}{quality_note}\n\n{method_hint}\n\nUse this exact format: [SOLUTION]...prose with citations like [Title](url)...[/SOLUTION] ```json...``` with fields: critical_insights, action_blueprint, open_questions, claim_labels, meta_audit, sources.'

COT_DETECTION_SYSTEM = "You are an analytical assistant. Identify potentially unsubstantiated, factually incorrect, or overly speculative statements in the provided text. Output ONLY valid JSON."

def cot_detection_prompt(state: PipelineState, retrieved_text: str) -> str:
    return f'{get_language_instruction(state)}\n\nProblem: {_wrap_user_input(state.problem)}\n\nReview the following retrieved text. Identify any statements that seem potentially unsubstantiated, factually incorrect, or overly speculative. For each identified statement, provide a brief explanation of your reasoning. If no issues are found, return an empty list.\n\nRetrieved Text:\n{retrieved_text}\n\nOutput JSON: {{"flags": [{{"statement": "<problematic statement>", "reasoning": "<why it\'s problematic>"}}]}}'

ITERATIVE_CONTEXT_SYSTEM = "You are an analytical assistant. Gather context for a reasoning problem and determine if you have enough information or if more searches are needed. Output ONLY valid JSON."

def iterative_context_prompt(state: PipelineState, current_results: list[dict], iteration: int, max_iterations: int) -> str:
    results_str = json.dumps(current_results, indent=2) if current_results else "No results yet."
    return f'{get_language_instruction(state)}\n\nProblem: {_wrap_user_input(state.problem)}\n\nIteration: {iteration} of {max_iterations}\n\nCurrent Search Results:\n{results_str}\n\nAnalyze the current results. Do you have enough relevant information to provide a comprehensive answer? If yes, set action to "done". If you need more information, provide up to 3 specific search queries to fill the gaps.\n\nOutput JSON: {{"action": "search|done", "queries": ["<query1>", "<query2>"], "reasoning": "<why you need more info or have enough>"}}'

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
