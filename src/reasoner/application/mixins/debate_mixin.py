"""Debate phase mixin for ARAPipeline."""

from __future__ import annotations

import asyncio
import logging

from reasoner.core.constants import TRUNCATION
from reasoner.models import PipelineState
from reasoner.parsing import extract_json

import reasoner.phases as phases
from reasoner.parsing import _parse_critique_scores
from reasoner.application.mixins._protocol import PipelineMixinProtocol

logger = logging.getLogger(__name__)


class DebateMixin(PipelineMixinProtocol):
    """Mixin providing debate phase methods."""

    async def _phase_debate_opening(self, state: PipelineState) -> None:
        self._log("DEBATE", "Round 1: Opening Statements", state)
        async def _get_opening(side: str):
            raw, _ = await self._call_llm_cached(role="constructive" if side=="A" else "destructive", system_prompt=phases.DEBATE_OPENING_SYSTEM, user_prompt=phases.debate_opening_prompt(state, side), state=state)
            return extract_json(raw)
        
        results = await asyncio.gather(_get_opening("A"), _get_opening("B"), return_exceptions=True)
        statements = []
        for side, r in zip(["A", "B"], results):
            if isinstance(r, Exception):
                msg = f"Debate opening '{side}' failed: {r}"
                self._log("DEBATE", msg, state)
                state.errors.append(msg)
            else:
                statements.append(r)
        state.debate_rounds.append({"round": 1, "type": "opening", "statements": statements})

    async def _phase_debate_rebuttal(self, state: PipelineState) -> None:
        self._log("DEBATE", "Round 2: Rebuttals", state)
        # Guard: opening phase may have produced fewer than 2 statements if one side failed.
        # Abort the rebuttal round rather than crash with IndexError.
        opening_statements = state.debate_rounds[0]['statements'] if state.debate_rounds else []
        if len(opening_statements) < 2:
            msg = f"Debate rebuttal skipped: only {len(opening_statements)} opening statement(s) available"
            self._log("DEBATE", msg, state)
            state.errors.append(msg)
            return
        statement_a = opening_statements[0].get('content', '')
        statement_b = opening_statements[1].get('content', '')
        async def _get_rebuttal(side: str, opponent_statement: str):
            raw, _ = await self._call_llm_cached(role="constructive" if side=="A" else "destructive", system_prompt=phases.DEBATE_REBUTTAL_SYSTEM, user_prompt=phases.debate_rebuttal_prompt(state, side, opponent_statement), state=state)
            return extract_json(raw)
        
        results = await asyncio.gather(_get_rebuttal("A", statement_b), _get_rebuttal("B", statement_a), return_exceptions=True)
        rebuttals = []
        for side, r in zip(["A", "B"], results):
            if isinstance(r, Exception):
                msg = f"Debate rebuttal '{side}' failed: {r}"
                self._log("DEBATE", msg, state)
                state.errors.append(msg)
            else:
                rebuttals.append(r)
        state.debate_rounds.append({"round": 2, "type": "rebuttal", "rebuttals": rebuttals})

    async def _phase_debate_judge(self, state: PipelineState) -> None:
        self._log("DEBATE", "Round 3: Judging", state)
        raw, _ = await self._call_llm_cached(role="systemic", system_prompt=phases.DEBATE_JUDGE_SYSTEM, user_prompt=phases.debate_judge_prompt(state), state=state)
        data = extract_json(raw)
        state.scores = _parse_critique_scores(data.get("scores", []))  # Store judge's scores
        # This data can then be used by the final synthesis step

    async def _phase_debate_cross_examine(self, state: PipelineState) -> None:
        """A5: Cross-examination — each side challenges the other's specific claims."""
        self._log("DEBATE", "Running cross-examination...", state)
        side_a_claims = []
        side_b_claims = []
        for rd in state.debate_rounds:
            if rd.get("phase") == "rebuttal":
                if rd.get("side") == "A":
                    side_a_claims.append(rd.get("content", "")[:TRUNCATION.CONTENT])
                elif rd.get("side") == "B":
                    side_b_claims.append(rd.get("content", "")[:TRUNCATION.CONTENT])
        tasks = [
            self._call_llm_cached(
                role="constructive",
                system_prompt=phases.DEBATE_CROSS_SYSTEM,
                user_prompt=phases.debate_cross_examine_prompt(state, "A", side_b_claims), state=state),
            self._call_llm_cached(
                role="destructive",
                system_prompt=phases.DEBATE_CROSS_SYSTEM,
                user_prompt=phases.debate_cross_examine_prompt(state, "B", side_a_claims), state=state),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                self._log("DEBATE", f"Cross-examine error: {r}", state)
                continue
            raw, _ = r
            data = extract_json(raw)
            state.debate_rounds.append({
                "phase": "cross_examine",
                "side": data.get("side", "?"),
                "challenges": data.get("challenges", []),
            })
