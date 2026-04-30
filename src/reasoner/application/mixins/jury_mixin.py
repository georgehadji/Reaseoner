"""Jury phase mixin for ReasonerPipeline."""

from __future__ import annotations

import asyncio
import logging

from reasoner.models import PipelineState, GenerationCandidate, CriticScore, CriticDimensionScore, VerificationResult, MetaEvaluation, ClaimLabel
from reasoner.parsing import ParseError, extract_json

import reasoner.phases as phases
from reasoner.application.mixins._protocol import PipelineMixinProtocol

logger = logging.getLogger(__name__)


class JuryMixin(PipelineMixinProtocol):
    """Mixin providing jury phase methods."""

    async def _phase_jury_generate(self, state: PipelineState) -> None:
        self._log("JURY", "Generating independent solutions...", state)
        
        async def _get_generator(gen_id: str):
            raw, _ = await self._call_llm_cached(
                role=gen_id,
                system_prompt=phases.JURY_GENERATOR_SYSTEM,
                user_prompt=phases.jury_generator_prompt(state, gen_id), state=state)
            data = extract_json(raw)
            return GenerationCandidate(**data, model_used="")

        # Extract generator roles
        gen_roles = [cfg.role for name, cfg in self.phase_configs.items() if "generator" in name]
        if not gen_roles: # Fallback if config is minimal
            gen_roles = ["generator_1", "generator_2", "generator_3"]
            
        tasks = [_get_generator(role) for role in gen_roles]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                role = gen_roles[i]
                msg = f"Jury generator '{role}' failed: {r}"
                self._log("JURY", msg, state)
                state.errors.append(msg)
            else:
                state.generation_candidates.append(r)

    async def _phase_jury_critique(self, state: PipelineState) -> None:
        self._log("JURY_CRITIQUE", "Jury critiquing candidates...", state)
        
        async def _get_jury_critique(critic_id: str):
            raw, _ = await self._call_llm_cached(
                role=critic_id,
                system_prompt=phases.JURY_CRITIC_SYSTEM,
                user_prompt=phases.jury_critic_prompt(state),
                state=state)
            data = extract_json(raw)
            # Instantiate nested CriticDimensionScore objects
            candidate_scores = {}
            for gen_id, dims in data.get('candidate_scores', {}).items():
                candidate_scores[gen_id] = CriticDimensionScore(
                    factuality=float(dims.get('factuality') or 0),
                    reasoning=float(dims.get('reasoning') or 0),
                    completeness=float(dims.get('completeness') or 0),
                    helpfulness=float(dims.get('helpfulness') or 0),
                    confidence_vs_accuracy_penalty=float(dims.get('confidence_vs_accuracy_penalty') or 0.0)
                )
            data['candidate_scores'] = candidate_scores
            return CriticScore(**data)

        # Get critics from preset (simplified for now, assume roles exist)
        critic_roles = [cfg.role for name, cfg in self.phase_configs.items() if "critic" in name]
        if not critic_roles:
            critic_roles = ["critic_1", "critic_2", "critic_3"]
            
        tasks = [_get_jury_critique(role) for role in critic_roles]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                role = critic_roles[i]
                msg = f"Jury critic '{role}' failed: {r}"
                self._log("JURY_CRITIQUE", msg, state)
                state.errors.append(msg)
            else:
                state.critic_scores.append(r)

        # After critiques, identify if any candidates need recovery path
        for critic_score in state.critic_scores:
            for gen_id, scores in critic_score.candidate_scores.items():
                # Check the confidence_vs_accuracy_penalty
                if scores.confidence_vs_accuracy_penalty > 5.0: # Threshold
                    candidate_to_check = next((gc for gc in state.generation_candidates if gc.generator_id == gen_id), None)
                    if candidate_to_check:

                        self._log("JURY_CRITIQUE", f"High penalty for Jury candidate {gen_id}. Triggering recovery path.", state)
                        await self._run_recovery_path(state, candidate_to_check)

    async def _phase_jury_verify_and_meta_eval(self, state: PipelineState) -> None:
        self._log("JURY", "Verifying claims and meta-evaluating critics...", state)

        def _parse_verification_results(raw_list: list[dict]) -> list[VerificationResult]:
            out: list[VerificationResult] = []
            for v in raw_list:
                try:
                    verdict_raw = v.get("verdict", "UNKNOWN")
                    verdict = ClaimLabel(verdict_raw) if verdict_raw in [e.value for e in ClaimLabel] else ClaimLabel.UNKNOWN
                    out.append(VerificationResult(
                        claim=str(v.get("claim", "")),
                        source_generator=str(v.get("source_generator", "")),
                        verdict=verdict,
                        evidence=str(v.get("evidence", "")),
                        confidence=float(v.get("confidence") or 0.0),
                    ))
                except (KeyError, ValueError, TypeError) as exc:
                    logger.warning("Skipping malformed VerificationResult entry: %s", exc)
            return out

        def _parse_meta_evaluation(data: dict) -> MetaEvaluation:
            try:
                return MetaEvaluation(
                    critic_reliability=data.get("critic_reliability", {}),
                    bias_analysis=data.get("bias_analysis", {}),
                    agreement_rate=float(data.get("agreement_rate") or 0.0),
                    most_reliable_critic=str(data.get("most_reliable_critic", "")),
                    least_reliable_critic=str(data.get("least_reliable_critic", "")),
                    meta_insight=str(data.get("meta_insight", "")),
                )
            except (KeyError, ValueError, TypeError) as exc:
                logger.warning("Malformed MetaEvaluation response: %s", exc)
                return MetaEvaluation(
                    critic_reliability={},
                    bias_analysis={},
                    agreement_rate=0.0,
                    most_reliable_critic="",
                    least_reliable_critic="",
                    meta_insight="",
                )

        # 1. Verification
        raw_v, _ = await self._call_llm_cached(
            role="verifier",
            system_prompt=phases.JURY_VERIFIER_SYSTEM,
            user_prompt=phases.jury_verifier_prompt(state), state=state)
        v_data = extract_json(raw_v)
        state.verification_results = _parse_verification_results(v_data.get("verifications", []))

        # 2. Meta Evaluation
        raw_m, _ = await self._call_llm_cached(
            role="meta_evaluator",
            system_prompt=phases.JURY_META_EVAL_SYSTEM,
            user_prompt=phases.jury_meta_eval_prompt(state), state=state)
        m_data = extract_json(raw_m)
        state.meta_evaluation = _parse_meta_evaluation(m_data)

    async def _phase_jury_weighted_ranking(self, state: PipelineState) -> None:
        """A3: Rerank generators by critic reliability weights."""
        self._log("JURY", "Computing reliability-weighted ranking...", state)
        reliability: dict[str, float] = {}
        if state.meta_evaluation:
            reliability = state.meta_evaluation.critic_reliability or {}
        
        generator_scores: dict[str, float] = {}
        for cs in state.critic_scores:
            weight = reliability.get(cs.critic_id, 1.0)
            for gen_id, dims in cs.candidate_scores.items():
                # Weighted score based on Avg (total)
                generator_scores[gen_id] = generator_scores.get(gen_id, 0.0) + (dims.total * weight)
        
        state.jury_weighted_ranking = sorted(
            generator_scores.keys(),
            key=lambda gid: generator_scores[gid],
            reverse=True,
        )
        self._log("JURY", f"Weighted ranking: {state.jury_weighted_ranking}", state)
