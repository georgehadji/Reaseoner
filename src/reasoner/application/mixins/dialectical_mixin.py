"""Dialectical reasoning mixin for ReasonerPipeline."""

from __future__ import annotations

import logging

from reasoner.models import PipelineState
from reasoner.parsing import extract_json

import reasoner.phases as phases
from reasoner.application.mixins._protocol import PipelineMixinProtocol

logger = logging.getLogger(__name__)


class DialecticalMixin(PipelineMixinProtocol):
    """Mixin providing dialectical, scientific, socratic, pre-mortem, bayesian, and analogical phases."""

    async def _phase_scientific_hypothesize(self, state: PipelineState) -> None:
        self._log("SCIENTIFIC", "Generating hypotheses...", state)
        raw, _ = await self._call_llm_cached(
            role="primary",
            system_prompt=phases.SCIENTIFIC_HYPOTHESIS_SYSTEM,
            user_prompt=phases.scientific_hypothesis_prompt(state), state=state)
        data = extract_json(raw)
        state.scientific_state["hypotheses"] = data.get("hypotheses", [])

    async def _phase_scientific_test(self, state: PipelineState) -> None:
        self._log("SCIENTIFIC", "Running falsification tests...", state)
        raw, _ = await self._call_llm_cached(
            role="scoring",
            system_prompt=phases.SCIENTIFIC_TEST_SYSTEM,
            user_prompt=phases.scientific_test_prompt(state), state=state)
        data = extract_json(raw)
        state.scientific_state["test_results"] = data.get("test_results", [])
        # A1: Inline Bayesian posterior update — compute posterior for each hypothesis
        hypotheses = state.scientific_state.get("hypotheses", [])
        test_results = state.scientific_state.get("test_results", [])
        for hyp in hypotheses:
            hyp_id = hyp.get("id", "")
            tests = [t for t in test_results if t.get("hypothesis_id") == hyp_id]
            supported = sum(1 for t in tests if t.get("result") == "SUPPORTED")
            hyp["posterior_probability"] = round(supported / max(len(tests), 1), 2)
        state.scientific_state["hypotheses"] = hypotheses

    async def _phase_socratic_question(self, state: PipelineState) -> None:
        self._log("SOCRATIC", "Generating Socratic questions...", state)
        raw, _ = await self._call_llm_cached(
            role="destructive",  # A4: questioner uses destructive role for genuine challenge
            system_prompt=phases.SOCRATIC_QUESTION_SYSTEM,
            user_prompt=phases.socratic_question_prompt(state), state=state)
        data = extract_json(raw)
        state.socratic_state["questions"] = data.get("questions", [])

    async def _phase_socratic_answer(self, state: PipelineState) -> None:
        self._log("SOCRATIC", "Attempting Dialectic answers...", state)
        raw, _ = await self._call_llm_cached(
            role="constructive",  # A4: answerer uses constructive role — genuinely different model
            system_prompt=phases.SOCRATIC_ANSWER_SYSTEM,
            user_prompt=phases.socratic_answer_prompt(state), state=state)
        data = extract_json(raw)
        state.socratic_state["answers"] = data.get("answers", [])

    async def _phase_pre_mortem_failure(self, state: PipelineState) -> None:
        self._log("PRE-MORTEM", "Constructing failure narrative...", state)
        raw, _ = await self._call_llm_cached(
            role="destructive",
            system_prompt=phases.PRE_MORTEM_FAILURE_SYSTEM,
            user_prompt=phases.pre_mortem_failure_prompt(state), state=state)
        data = extract_json(raw)
        state.pre_mortem_state["failure_narrative"] = data

    async def _phase_pre_mortem_backtrack(self, state: PipelineState) -> None:
        self._log("PRE-MORTEM", "Identifying root cause pivot point...", state)
        raw, _ = await self._call_llm_cached(
            role="scoring",
            system_prompt=phases.PRE_MORTEM_BACKTRACK_SYSTEM,
            user_prompt=phases.pre_mortem_backtrack_prompt(state), state=state)
        data = extract_json(raw)
        state.pre_mortem_state["root_cause"] = data

    async def _phase_pre_mortem_signals(self, state: PipelineState) -> None:
        self._log("PRE-MORTEM", "Identifying early warning signals...", state)
        raw, _ = await self._call_llm_cached(
            role="scoring",
            system_prompt=phases.PRE_MORTEM_SIGNALS_SYSTEM,
            user_prompt=phases.pre_mortem_signals_prompt(state), state=state)
        data = extract_json(raw)
        state.pre_mortem_state["early_signals"] = data.get("early_signals", [])
        state.pre_mortem_state["monitoring_cadence"] = data.get("monitoring_cadence", "")

    async def _phase_pre_mortem_redesign(self, state: PipelineState) -> None:
        self._log("PRE-MORTEM", "Generating hardened redesign...", state)
        raw, _ = await self._call_llm_cached(
            role="synthesis",
            system_prompt=phases.PRE_MORTEM_REDESIGN_SYSTEM,
            user_prompt=phases.pre_mortem_redesign_prompt(state), state=state)
        data = extract_json(raw)
        state.pre_mortem_state["hardened_solution"] = data.get("hardened_solution", "")
        state.pre_mortem_state["safeguards"] = data.get("safeguards", [])
        state.pre_mortem_state["checkpoints"] = data.get("checkpoints", [])
        state.pre_mortem_state["rollback_plan"] = data.get("rollback_plan", "")

    async def _phase_bayesian_priors(self, state: PipelineState) -> None:
        self._log("BAYESIAN", "Eliciting prior distributions...", state)
        raw, _ = await self._call_llm_cached(
            role="constructive",
            system_prompt=phases.BAYESIAN_PRIOR_SYSTEM,
            user_prompt=phases.bayesian_prior_prompt(state), state=state)
        data = extract_json(raw)
        state.bayesian_state["hypotheses_with_priors"] = data.get("hypotheses", [])

    async def _phase_bayesian_likelihood(self, state: PipelineState) -> None:
        self._log("BAYESIAN", "Assessing likelihoods...", state)
        raw, _ = await self._call_llm_cached(
            role="destructive",
            system_prompt=phases.BAYESIAN_LIKELIHOOD_SYSTEM,
            user_prompt=phases.bayesian_likelihood_prompt(state), state=state)
        data = extract_json(raw)
        state.bayesian_state["evidence_likelihoods"] = data.get("likelihoods", [])
        state.bayesian_state["observations"] = data.get("observations", [])

    async def _phase_bayesian_posterior(self, state: PipelineState) -> None:
        self._log("BAYESIAN", "Computing posteriors...", state)
        raw, _ = await self._call_llm_cached(
            role="scoring",
            system_prompt=phases.BAYESIAN_POSTERIOR_SYSTEM,
            user_prompt=phases.bayesian_posterior_prompt(state), state=state)
        data = extract_json(raw)
        posteriors = data.get("posteriors", [])
        # Normalize so posteriors sum to 1.0, correcting LLM rounding drift.
        total = sum(p.get("posterior_probability", 0.0) for p in posteriors if isinstance(p, dict))
        if total > 0 and abs(total - 1.0) > 0.01:
            for p in posteriors:
                if isinstance(p, dict) and "posterior_probability" in p:
                    p["posterior_probability"] = round(p["posterior_probability"] / total, 4)
        state.bayesian_state["posteriors"] = posteriors
        state.bayesian_state["most_probable"] = data.get("most_probable", "")

    async def _phase_bayesian_sensitivity(self, state: PipelineState) -> None:
        self._log("BAYESIAN", "Running sensitivity analysis...", state)
        raw, _ = await self._call_llm_cached(
            role="synthesis",
            system_prompt=phases.BAYESIAN_SENSITIVITY_SYSTEM,
            user_prompt=phases.bayesian_sensitivity_prompt(state), state=state)
        data = extract_json(raw)
        state.bayesian_state["sensitivity_results"] = data.get("sensitivity_analysis", [])
        state.bayesian_state["most_sensitive_assumption"] = data.get("most_sensitive_assumption", "")

    async def _phase_dialectical_thesis(self, state: PipelineState) -> None:
        self._log("DIALECTICAL", "Formulating thesis...", state)
        raw, _ = await self._call_llm_cached(
            role="constructive",
            system_prompt=phases.DIALECTICAL_THESIS_SYSTEM,
            user_prompt=phases.dialectical_thesis_prompt(state), state=state)
        data = extract_json(raw)
        state.dialectical_state["thesis"] = data.get("thesis", "")
        state.dialectical_state["key_commitments"] = data.get("key_commitments", [])
        state.dialectical_state["thesis_assumptions"] = data.get("assumptions", [])

    async def _phase_dialectical_antithesis(self, state: PipelineState) -> None:
        self._log("DIALECTICAL", "Formulating antithesis...", state)
        raw, _ = await self._call_llm_cached(
            role="destructive",
            system_prompt=phases.DIALECTICAL_ANTITHESIS_SYSTEM,
            user_prompt=phases.dialectical_antithesis_prompt(state), state=state)
        data = extract_json(raw)
        state.dialectical_state["antithesis"] = data.get("antithesis", "")
        state.dialectical_state["contradictions_exposed"] = data.get("contradictions_exposed", [])
        state.dialectical_state["negated_commitments"] = data.get("negated_commitments", [])

    async def _phase_dialectical_contradictions(self, state: PipelineState) -> None:
        self._log("DIALECTICAL", "Analyzing contradictions...", state)
        raw, _ = await self._call_llm_cached(
            role="scoring",
            system_prompt=phases.DIALECTICAL_CONTRADICTIONS_SYSTEM,
            user_prompt=phases.dialectical_contradictions_prompt(state), state=state)
        data = extract_json(raw)
        state.dialectical_state["irreconcilable"] = data.get("irreconcilable", [])
        state.dialectical_state["compatible"] = data.get("compatible", [])
        state.dialectical_state["synthesis_candidates"] = data.get("synthesis_candidates", [])

    async def _phase_dialectical_aufhebung(self, state: PipelineState) -> None:
        self._log("DIALECTICAL", "Formulating Aufhebung...", state)
        raw, _ = await self._call_llm_cached(
            role="synthesis",
            system_prompt=phases.DIALECTICAL_AUFHEBUNG_SYSTEM,
            user_prompt=phases.dialectical_aufhebung_prompt(state), state=state)
        data = extract_json(raw)
        state.dialectical_state["aufhebung"] = data.get("aufhebung", "")
        state.dialectical_state["preserved_from_thesis"] = data.get("preserved_from_thesis", [])
        state.dialectical_state["preserved_from_antithesis"] = data.get("preserved_from_antithesis", [])
        state.dialectical_state["transcended"] = data.get("transcended", "")
        state.dialectical_state["new_insights"] = data.get("new_insights", [])

    async def _phase_analogical_abstraction(self, state: PipelineState) -> None:
        self._log("ANALOGICAL", "Extracting abstract problem structure...", state)
        raw, _ = await self._call_llm_cached(
            role="systemic",
            system_prompt=phases.ANALOGICAL_ABSTRACTION_SYSTEM,
            user_prompt=phases.analogical_abstraction_prompt(state), state=state)
        data = extract_json(raw)
        state.analogical_state["abstract_structure"] = data.get("abstract_structure", "") or ""
        state.analogical_state["constraints"] = data.get("constraints", [])
        state.analogical_state["objectives"] = data.get("objectives", [])
        state.analogical_state["actors"] = data.get("actors", [])
        state.analogical_state["core_dynamics"] = data.get("core_dynamics", [])
        state.analogical_state["structural_type"] = data.get("structural_type", "") or ""

    async def _phase_analogical_domain_search(self, state: PipelineState) -> None:
        self._log("ANALOGICAL", "Searching for isomorphic source domains...", state)
        raw, _ = await self._call_llm_cached(
            role="systemic",
            system_prompt=phases.ANALOGICAL_DOMAIN_SEARCH_SYSTEM,
            user_prompt=phases.analogical_domain_search_prompt(state), state=state)
        data = extract_json(raw)
        _raw_domains = data.get("source_domains", [])
        state.analogical_state["source_domains"] = _raw_domains if isinstance(_raw_domains, list) else []

    async def _phase_analogical_mapping(self, state: PipelineState) -> None:
        if not state.analogical_state.get("source_domains"):
            return
        self._log("ANALOGICAL", "Mapping source domain elements to target problem...", state)
        raw, _ = await self._call_llm_cached(
            role="systemic",
            system_prompt=phases.ANALOGICAL_MAPPING_SYSTEM,
            user_prompt=phases.analogical_mapping_prompt(state), state=state)
        data = extract_json(raw)
        _raw_mappings = data.get("analogy_mappings", [])
        state.analogical_state["analogy_mappings"] = _raw_mappings if isinstance(_raw_mappings, list) else []
        state.analogical_state["unmapped_elements"] = data.get("unmapped_elements", [])
        state.analogical_state["mapping_quality"] = data.get("mapping_quality", "") or ""

    async def _phase_analogical_transfer(self, state: PipelineState) -> None:
        if not state.analogical_state.get("source_domains"):
            return
        self._log("ANALOGICAL", "Transferring and adapting solution from source domain...", state)
        raw, _ = await self._call_llm_cached(
            role="synthesis",
            system_prompt=phases.ANALOGICAL_TRANSFER_SYSTEM,
            user_prompt=phases.analogical_transfer_prompt(state), state=state)
        data = extract_json(raw)
        
        if isinstance(data, str):
            self._log("ANALOGICAL", f"Transfer parse error: expected dict, got string", state)
            state.errors.append("Analogical transfer: parse error, got string instead of JSON object.")
            data = {"transferred_solution": data} # Fallback to using the raw text as the solution

        state.analogical_state["transferred_solution"] = data.get("transferred_solution", "") or ""
        state.analogical_state["transfer_steps"] = data.get("transfer_steps", [])
        state.analogical_state["adaptations_required"] = data.get("adaptations_required", [])
        state.analogical_state["broken_analogies"] = data.get("broken_analogies", [])
        state.analogical_state["transfer_confidence"] = data.get("confidence", "") or ""
        state.analogical_state["caveats"] = data.get("caveats", [])
