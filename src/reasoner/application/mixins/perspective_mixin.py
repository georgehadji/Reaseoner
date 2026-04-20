"""Perspective, critique, and stress-test mixin for ARAPipeline."""

from __future__ import annotations

import asyncio
import json
import logging

from reasoner.core.constants import TRUNCATION, get_token_budget, DEFAULT_MAX_TOKENS
from reasoner.models import PipelineState, SolutionCandidate, PerspectiveType, StressTestResult, ScenarioType
from reasoner.parsing import ParseError, extract_json

import reasoner.phases as phases
from reasoner.parsing import _parse_critique_scores

logger = logging.getLogger(__name__)


class PerspectiveMixin:
    """Mixin providing multi-perspective, critique, and stress-test phases."""

    async def _phase_2_perspectives(self, state: PipelineState):
        self._log("PHASE-2", "Running multi-perspective analysis...", state)

        _PERSPECTIVE_HALLUCINATION_KEYWORDS = {"greek text", "greek characters", "parsing errors", "encoding issues", "unicode problems"}

        def _is_perspective_hallucinated(candidate: SolutionCandidate) -> bool:
            if state.language != "English":
                return False
            text = f"{candidate.content} {' '.join(candidate.key_insights)}".lower()
            return any(kw in text for kw in _PERSPECTIVE_HALLUCINATION_KEYWORDS)

        async def _get_perspective(p_name: str):
            from reasoner.pipeline import TOKEN_OPTIMIZATION
            p_enum = PerspectiveType(p_name)
            base_system = phases.PERSPECTIVE_SYSTEMS.get(p_name, "")
            lang_instruction = phases.get_language_instruction(state)
            system_prompt = f"{lang_instruction}\n\n{base_system}"
            # TOKEN OPTIMIZATION: Use phase-aware context with aggressive compression
            user_prompt = phases.perspective_prompt(state, p_name)
            # TOKEN OPTIMIZATION: Use perspective-specific token budget + caching
            raw, _ = await self._call_llm_cached(
                role=p_name,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                state=state,
                max_tokens=get_token_budget(p_name) if TOKEN_OPTIMIZATION["dynamic_budgets"] else DEFAULT_MAX_TOKENS
            )
            data = extract_json(raw)
            # Guard against absent keys: content/key_insights are typed str/list[str] and
            # must not be None — downstream prompt builders slice content and iterate insights.
            core_analysis = data.get("core_analysis") or ""
            if not isinstance(core_analysis, str):
                core_analysis = json.dumps(core_analysis, ensure_ascii=False) if isinstance(core_analysis, (dict, list)) else str(core_analysis)
            # DEFENSIVE: If LLM returned valid JSON but wrong schema, serialize the whole dict as content
            if not core_analysis and isinstance(data, dict) and len(data) > 1:
                core_analysis = json.dumps(data, ensure_ascii=False)
                key_insights = []
                self._log("PHASE-2", f"Perspective '{p_name}' returned non-standard schema; using full JSON as content.", state)
            else:
                key_insights = data.get("key_insights") or []
                if not isinstance(key_insights, list):
                    key_insights = [str(key_insights)] if key_insights else []
            return SolutionCandidate(
                perspective=p_enum,
                content=core_analysis,
                key_insights=key_insights,
                model_used="",
            )

        def _perspective_name(p) -> str:
            return p.name if hasattr(p, 'name') else str(p)

        tasks = [_get_perspective(_perspective_name(p)) for p in self.perspectives]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, r in enumerate(results):
            p_name = _perspective_name(self.perspectives[i])
            if isinstance(r, Exception):
                msg = f"Perspective '{p_name}' failed: {r}"
                self._log("PHASE-2", msg, state)
                state.errors.append(msg)
            else:
                if _is_perspective_hallucinated(r):
                    self._log("PHASE-2", f"Filtering hallucinated perspective '{p_name}'; regenerating once.", state)
                    try:
                        replacement = await _get_perspective(p_name)
                        if _is_perspective_hallucinated(replacement):
                            self._log("PHASE-2", f"Replacement for '{p_name}' still hallucinated; keeping with penalty.", state)
                        state.candidates.append(replacement)
                    except Exception as exc:
                        self._log("PHASE-2", f"Failed to regenerate perspective '{p_name}': {exc}", state)
                        state.errors.append(f"Perspective '{p_name}' regeneration failed: {exc}")
                else:
                    state.candidates.append(r)

    async def _phase_3_critique(self, state: PipelineState):
        from reasoner.pipeline import TOKEN_OPTIMIZATION, USE_PHASE_SUBAGENTS
        self._log("PHASE-3", "Critiquing candidates...", state)
        if not state.candidates:
            self._log("PHASE-3", "No candidates to critique. Skipping.", state)
            state.scores = []
            state.top_candidates = []
            return

        # ── Subagent path (opt-in via env) ────────────────────────────
        if USE_PHASE_SUBAGENTS["critique"]:
            from reasoner.subagents.critique.hyper_agent import CritiqueHyperAgent
            agent = CritiqueHyperAgent()
            try:
                state.scores = await agent.execute(state, self.router)
                self._log("PHASE-3", f"CritiqueHyperAgent produced {len(state.scores)} scores.", state)
            except Exception as exc:
                self._log("PHASE-3", f"CritiqueHyperAgent failed ({exc}), falling back to legacy.", state)
                state.scores = []
            # Fall through to shared pruning logic

        else:
            # ── Legacy monolithic path ─────────────────────────────────
            raw, _ = await self._call_llm_cached(
                role="scoring",
                system_prompt=phases.CRITIQUE_SYSTEM,
                user_prompt=phases.critique_prompt(state),
                state=state,
                max_tokens=get_token_budget("scoring") if TOKEN_OPTIMIZATION["dynamic_budgets"] else DEFAULT_MAX_TOKENS
            )
            try:
                data = extract_json(raw)
            except ParseError as exc:
                self._log("PHASE-3", f"Failed to parse critique response: {exc}", state)
                state.errors.append(f"Critique parse error: {exc}")
                data = {}
            state.scores = _parse_critique_scores(data.get("scores", []))

        # ── Shared pruning logic ──────────────────────────────────────
        for score in state.scores:
            if score.confidence_vs_accuracy_penalty > 5.0: # Threshold for triggering recovery
                candidate_to_check = next((c for c in state.candidates if c.perspective == score.perspective), None)
                if candidate_to_check:
                    self._log("PHASE-3", f"High penalty for {score.perspective}. Triggering recovery path.", state)
                    await self._run_recovery_path(state, candidate_to_check)

        scored_perspectives = {s.perspective: s.total for s in state.scores}
        top_p = sorted(scored_perspectives, key=scored_perspectives.get, reverse=True)[:self.top_k]
        state.top_candidates = [c for c in state.candidates if c.perspective in top_p]

    async def _phase_4_stress_test(self, state: PipelineState):
        self._log("PHASE-4", "Running stress tests...", state)
        # TOKEN OPTIMIZATION: Use stress_testing-specific token budget + caching
        from reasoner.pipeline import TOKEN_OPTIMIZATION
        raw, _ = await self._call_llm_cached(
            role="stress_testing",
            system_prompt=phases.STRESS_SYSTEM,
            user_prompt=phases.stress_test_prompt(state),
            state=state,
            max_tokens=get_token_budget("stress_testing") if TOKEN_OPTIMIZATION["dynamic_budgets"] else DEFAULT_MAX_TOKENS
        )
        try:
            data = extract_json(raw)
        except ParseError as exc:
            self._log("PHASE-4", f"Failed to parse stress test response: {exc}", state)
            state.errors.append(f"Stress test parse error: {exc}")
            data = {}
        # Use ScenarioType.coerce() so that LLM variants ("constraint violation",
        # "constraint-violation") all map to the correct enum member.  Without it,
        # the raw string is stored and any enum-identity check downstream fails.
        _HALLUCINATION_KEYWORDS = {
            "greek", "parsing", "encoding", "json", "invalid text", "missing text",
            "unicode", "charset", "markdown", "truncated output", "length limits",
            "context misinterpretation", "off-topic response", "output format",
            "markdown fence", "json parse error", "model limitation", "token limit",
        }

        def _is_hallucinated(st: dict) -> bool:
            text = f"{st.get('failure_mode', '')} {st.get('scenario', '')}".lower()
            return any(kw in text for kw in _HALLUCINATION_KEYWORDS)

        _stress: list[StressTestResult] = []
        for st in data.get("stress_tests", []):
            try:
                if _is_hallucinated(st):
                    self._log("PHASE-4", f"Filtering hallucinated stress test: {st}", state)
                    continue
                _stress.append(StressTestResult(
                    scenario=ScenarioType.coerce(st.get("scenario", "optimal")),
                    survival_rate=float(st.get("survival_rate") or 0),
                    failure_mode=st.get("failure_mode") or "",
                    recovery_path=st.get("recovery_path") or "",
                ))
            except (ValueError, TypeError) as exc:
                logger.warning("Skipping malformed StressTestResult: %s", exc)
        if not _stress:
            _stress.append(StressTestResult(
                scenario=ScenarioType.OPTIMAL,
                survival_rate=1.0,
                failure_mode="",
                recovery_path="",
            ))
        state.stress_results = _stress
