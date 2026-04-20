from __future__ import annotations
import json
from reasoner.models import PipelineState
from reasoner.phases._shared import get_language_instruction, _wrap_user_input

DEEP_RESEARCH_SYSTEM = "You are an analytical assistant. Gather comprehensive information to solve the user's problem. You can issue search queries or declare that you have enough information. Output ONLY valid JSON."

def deep_research_prompt(state: PipelineState, current_knowledge: list[dict], iteration: int, max_iterations: int) -> str:
    knowledge_str = json.dumps(current_knowledge, indent=2) if current_knowledge else "No information gathered yet."
    return f'{get_language_instruction(state)}\n\nProblem: {_wrap_user_input(state.problem)}\n\nIteration: {iteration} of {max_iterations}\n\nCurrent Knowledge Gathered:\n{knowledge_str}\n\nAnalyze the current knowledge. If you need more information to fully answer the problem, generate up to 3 highly specific, SEO-friendly search queries. If you have enough information, or if you have reached the maximum iterations, set the action to "done".\n\nOutput JSON: {{"action": "search|done", "queries": ["<query1>", "<query2>"], "reasoning": "<why you chose this action>"}}'
