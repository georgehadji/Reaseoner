"""Cognitive architecture mixin for ARAPipeline."""

from __future__ import annotations

import asyncio
import logging

from reasoner.models import PipelineState, SolutionCandidate, PerspectiveType
from reasoner.parsing import extract_json

import reasoner.phases as phases

logger = logging.getLogger(__name__)


class CognitiveMixin:
    """Mixin providing CoVE, SoT, ToT, PoT, and Self-Discover phases."""

    async def _phase_cove_draft(self, state: PipelineState):
        self._log("COVE", "Drafting initial answer...", state)
        raw, _ = await self._call_llm_cached(
            role="cove_draft",
            system_prompt=phases.COVE_DRAFT_SYSTEM,
            user_prompt=phases.cove_draft_prompt(state), state=state)
        data = extract_json(raw)
        state.cove_state["draft_answer"] = data.get("draft_answer", "")
        state.cove_state["claims"] = data.get("claims", [])

    async def _phase_cove_verify(self, state: PipelineState):
        self._log("COVE", "Generating verification questions...", state)
        raw, _ = await self._call_llm_cached(
            role="cove_verify",
            system_prompt=phases.COVE_VERIFY_SYSTEM,
            user_prompt=phases.cove_verify_prompt(state), state=state)
        data = extract_json(raw)
        state.cove_state["verification_questions"] = data.get("verification_questions", [])

    async def _phase_cove_answer(self, state: PipelineState):
        self._log("COVE", "Answering verification questions independently...", state)
        raw, _ = await self._call_llm_cached(
            role="cove_answer",
            system_prompt=phases.COVE_ANSWER_SYSTEM,
            user_prompt=phases.cove_answer_prompt(state), state=state)
        data = extract_json(raw)
        state.cove_state["verification_answers"] = data.get("answers", [])

    async def _phase_cove_revise(self, state: PipelineState):
        self._log("COVE", "Revising answer based on verification...", state)
        raw, _ = await self._call_llm_cached(
            role="cove_revise",
            system_prompt=phases.COVE_REVISE_SYSTEM,
            user_prompt=phases.cove_revise_prompt(state), state=state)
        data = extract_json(raw)
        state.cove_state["revised_answer"] = data.get("revised_answer", "")
        state.cove_state["changes_made"] = data.get("changes_made", [])
        state.cove_state["remaining_uncertainties"] = data.get("remaining_uncertainties", [])
        # Feed revised answer into candidates for synthesis
        state.candidates.append(SolutionCandidate(
            perspective=PerspectiveType.CONSTRUCTIVE,
            content=state.cove_state.get("revised_answer", ""),
            key_insights=state.cove_state.get("changes_made", []),
            model_used=state.phase_models.get("cove_revise", "unknown"),
        ))

    async def _phase_sot_skeleton(self, state: PipelineState):
        self._log("SoT", "Generating problem skeleton...", state)
        raw, _ = await self._call_llm_cached(
            role="sot_skeleton",
            system_prompt=phases.SOT_SKELETON_SYSTEM,
            user_prompt=phases.sot_skeleton_prompt(state), state=state)
        data = extract_json(raw)
        state.sot_state["sub_problems"] = data.get("sub_problems", [])

    async def _phase_sot_solve(self, state: PipelineState):
        self._log("SoT", "Solving sub-problems in parallel...", state)
        sub_problems = state.sot_state.get("sub_problems", [])
        if not sub_problems:
            state.errors.append("SoT: No sub-problems to solve.")
            return
        # Semaphore to limit parallel LLM calls (max 4 concurrent)
        semaphore = asyncio.Semaphore(4)
        async def _solve_one(sp: dict) -> dict:
            async with semaphore:
                raw, _ = await self._call_llm_cached(
                    role="sot_solve",
                    system_prompt=phases.SOT_SOLVE_SYSTEM,
                    user_prompt=phases.sot_solve_prompt(state, sp), state=state)
                data = extract_json(raw)
                return {
                    "sub_problem_id": sp.get("id", ""),
                    "solution": data.get("solution", ""),
                    "key_insights": data.get("key_insights", []),
                    "assumptions": data.get("assumptions", []),
                }
        tasks = [_solve_one(sp) for sp in sub_problems]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        solutions = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                state.errors.append(f"SoT: Sub-problem {i+1} solve failed: {result}")
                continue
            solutions.append(result)
        state.sot_state["solutions"] = solutions

    async def _phase_sot_assemble(self, state: PipelineState):
        self._log("SoT", "Assembling sub-problem solutions...", state)
        raw, _ = await self._call_llm_cached(
            role="sot_assemble",
            system_prompt=phases.SOT_ASSEMBLE_SYSTEM,
            user_prompt=phases.sot_assemble_prompt(state), state=state)
        data = extract_json(raw)
        state.sot_state["assembled_answer"] = data.get("assembled_answer", "")
        state.sot_state["transitions"] = data.get("transitions", [])
        state.sot_state["resolved_conflicts"] = data.get("resolved_conflicts", [])
        # Feed assembled answer into candidates for synthesis
        state.candidates.append(SolutionCandidate(
            perspective=PerspectiveType.CONSTRUCTIVE,
            content=state.sot_state.get("assembled_answer", ""),
            key_insights=state.sot_state.get("transitions", []),
            model_used=state.phase_models.get("sot_assemble", "unknown"),
        ))

    async def _phase_tot_decompose(self, state: PipelineState):
        self._log("ToT", "Decomposing into decision points...", state)
        raw, _ = await self._call_llm_cached(
            role="tot_decompose",
            system_prompt=phases.TOT_DECOMPOSE_SYSTEM,
            user_prompt=phases.tot_decompose_prompt(state), state=state)
        data = extract_json(raw)
        state.tot_state["decision_points"] = data.get("decision_points", [])
        state.tot_state["current_path"] = []

    async def _phase_tot_generate(self, state: PipelineState):
        self._log("ToT", "Generating candidate actions...", state)
        dps = state.tot_state.get("decision_points", [])
        if not dps:
            state.errors.append("ToT: No decision points to generate candidates for.")
            return
        current_dp = dps[len(state.tot_state.get("current_path", []))]
        raw, _ = await self._call_llm_cached(
            role="tot_generate",
            system_prompt=phases.TOT_GENERATE_SYSTEM,
            user_prompt=phases.tot_generate_prompt(state, current_dp), state=state)
        data = extract_json(raw)
        state.tot_state["current_candidates"] = data.get("candidates", [])

    async def _phase_tot_evaluate(self, state: PipelineState):
        self._log("ToT", "Evaluating candidates...", state)
        candidates = state.tot_state.get("current_candidates", [])
        if not candidates:
            state.errors.append("ToT: No candidates to evaluate.")
            return
        raw, _ = await self._call_llm_cached(
            role="tot_evaluate",
            system_prompt=phases.TOT_EVALUATE_SYSTEM,
            user_prompt=phases.tot_evaluate_prompt(state, candidates), state=state)
        data = extract_json(raw)
        state.tot_state["evaluations"] = data.get("evaluations", [])
        state.tot_state["best_candidate"] = data.get("best_candidate", "")
        # Append best candidate to current path
        best = data.get("best_candidate", "")
        if best:
            state.tot_state["current_path"].append(best)

    async def _phase_tot_backtrack(self, state: PipelineState):
        self._log("ToT", "Backtracking / finalizing path...", state)
        raw, _ = await self._call_llm_cached(
            role="tot_backtrack",
            system_prompt=phases.TOT_BACKTRACK_SYSTEM,
            user_prompt=phases.tot_backtrack_prompt(state), state=state)
        data = extract_json(raw)
        state.tot_state["backtrack_decision"] = data.get("decision", "terminate")
        state.tot_state["final_path"] = data.get("final_path", [])
        state.tot_state["tot_confidence"] = data.get("confidence", 0.0)
        # Feed final path into candidates for synthesis
        path_text = " → ".join(state.tot_state.get("final_path", []))
        state.candidates.append(SolutionCandidate(
            perspective=PerspectiveType.CONSTRUCTIVE,
            content=f"Tree-of-Thoughts optimal path: {path_text}",
            key_insights=[f"Decision: {data.get('decision', 'terminate')}"],
            model_used=state.phase_models.get("tot_backtrack", "unknown"),
        ))

    async def _phase_pot_generate(self, state: PipelineState):
        self._log("PoT", "Generating executable code...", state)
        raw, _ = await self._call_llm_cached(
            role="pot_generate",
            system_prompt=phases.POT_GENERATE_SYSTEM,
            user_prompt=phases.pot_generate_prompt(state), state=state)
        data = extract_json(raw)
        state.pot_state["code"] = data.get("code", "")
        state.pot_state["explanation"] = data.get("explanation", "")
        state.pot_state["expected_output_type"] = data.get("expected_output_type", "")

    async def _phase_pot_execute(self, state: PipelineState):
        self._log("PoT", "Executing generated code...", state)
        code = state.pot_state.get("code", "")
        if not code:
            state.errors.append("PoT: No code to execute.")
            return
        # Simulated execution via LLM (sandbox not available)
        raw, _ = await self._call_llm_cached(
            role="pot_execute",
            system_prompt=phases.POT_EXECUTE_SYSTEM,
            user_prompt=phases.pot_execute_prompt(state), state=state)
        data = extract_json(raw)
        state.pot_state["execution_output"] = data.get("output", "")
        state.pot_state["execution_success"] = data.get("success", False)
        state.pot_state["execution_error"] = data.get("error", "")
        state.pot_state["intermediate_steps"] = data.get("intermediate_steps", [])

    async def _phase_pot_interpret(self, state: PipelineState):
        self._log("PoT", "Interpreting execution results...", state)
        raw, _ = await self._call_llm_cached(
            role="pot_interpret",
            system_prompt=phases.POT_INTERPRET_SYSTEM,
            user_prompt=phases.pot_interpret_prompt(state), state=state)
        data = extract_json(raw)
        state.pot_state["interpretation"] = data.get("interpretation", "")
        state.pot_state["computed_answer"] = data.get("answer", "")
        state.pot_state["caveats"] = data.get("caveats", [])
        # Feed computed answer into candidates for synthesis
        state.candidates.append(SolutionCandidate(
            perspective=PerspectiveType.CONSTRUCTIVE,
            content=state.pot_state.get("computed_answer", ""),
            key_insights=state.pot_state.get("caveats", []),
            model_used=state.phase_models.get("pot_interpret", "unknown"),
        ))

    async def _phase_sd_select(self, state: PipelineState):
        self._log("SELF-DISCOVER", "Selecting reasoning modules...", state)
        raw, _ = await self._call_llm_cached(
            role="sd_select",
            system_prompt=phases.SD_SELECT_SYSTEM,
            user_prompt=phases.sd_select_prompt(state), state=state)
        data = extract_json(raw)
        state.self_discover_state["selected_modules"] = data.get("selected_modules", [])
        state.self_discover_state["composition_strategy"] = data.get("composition_strategy", "")

    async def _phase_sd_adapt(self, state: PipelineState):
        self._log("SELF-DISCOVER", "Adapting modules to problem...", state)
        raw, _ = await self._call_llm_cached(
            role="sd_adapt",
            system_prompt=phases.SD_ADAPT_SYSTEM,
            user_prompt=phases.sd_adapt_prompt(state), state=state)
        data = extract_json(raw)
        state.self_discover_state["adapted_modules"] = data.get("adapted_modules", [])

    async def _phase_sd_implement(self, state: PipelineState):
        self._log("SELF-DISCOVER", "Implementing adapted reasoning pipeline...", state)
        raw, _ = await self._call_llm_cached(
            role="sd_implement",
            system_prompt=phases.SD_IMPLEMENT_SYSTEM,
            user_prompt=phases.sd_implement_prompt(state), state=state)
        data = extract_json(raw)
        state.self_discover_state["module_outputs"] = data.get("module_outputs", [])
        state.self_discover_state["final_answer"] = data.get("final_answer", "")
        state.self_discover_state["module_attribution"] = data.get("module_attribution", {})
        # Feed final answer into candidates for synthesis
        state.candidates.append(SolutionCandidate(
            perspective=PerspectiveType.CONSTRUCTIVE,
            content=state.self_discover_state.get("final_answer", ""),
            key_insights=[m.get("output", "") for m in state.self_discover_state.get("module_outputs", [])],
            model_used=state.phase_models.get("sd_implement", "unknown"),
        ))
