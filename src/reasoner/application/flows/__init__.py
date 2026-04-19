"""Pipeline flow registry factory."""

from __future__ import annotations

from reasoner.api.serializers import (
    _ser_0,
    _ser_1,
    _ser_1_5,
    _ser_2,
    _ser_3,
    _ser_4,
    _ser_5,
)
from reasoner.pipeline import ARAPipeline

from .pipeline_flow import PhaseStep, PipelineFlow

__all__ = ["PhaseStep", "PipelineFlow", "build_default_flow_registry"]


def build_default_flow_registry(pipeline: ARAPipeline) -> PipelineFlow:
    """
    Build a PipelineFlow backed by an *ARAPipeline* instance.

    Each step binds to the corresponding ``_phase_*`` / ``_run_*`` method
    on the pipeline.  This is the single source of truth for method-specific
    phase ordering used by both ``ARAPipeline.run()`` and the API stream.
    """
    flow = PipelineFlow()

    # ── Multi-Perspective (default) ────────────────────────────────────
    flow.register("multi_perspective", [
        PhaseStep(2, "Perspectives",       pipeline._phase_2_perspectives, _ser_2),
        PhaseStep(3, "Critique & Pruning", pipeline._phase_3_critique,     _ser_3, critical=True),
        PhaseStep(4, "Stress Testing",     pipeline._phase_4_stress_test,  _ser_4),
    ])

    # ── Debate ─────────────────────────────────────────────────────────
    flow.register("debate", [
        PhaseStep(2, "Opening Statements",  pipeline._phase_debate_opening,    _ser_2),
        PhaseStep(3, "Rebuttals",           pipeline._phase_debate_rebuttal,   _ser_3),
        PhaseStep(4, "Cross-Examination",   pipeline._phase_debate_cross_examine, _ser_4),
    ])

    # ── Jury / Orchestrated ────────────────────────────────────────────
    flow.register("jury", [
        PhaseStep(2, "Generation Pool",     pipeline._phase_jury_generate,             _ser_2),
        PhaseStep(3, "Critic Pool",         pipeline._phase_jury_critique,             _ser_3, critical=True),
        PhaseStep(4, "Verification & Meta", pipeline._phase_jury_verify_and_meta_eval, _ser_4),
    ])

    # ── Research ───────────────────────────────────────────────────────
    flow.register("research", [
        PhaseStep(2, "Deep Research",      pipeline._phase_research_web_search, _ser_2),
        PhaseStep(3, "Perspectives",       pipeline._phase_2_perspectives,      _ser_2),
        PhaseStep(4, "Critique & Pruning", pipeline._phase_3_critique,          _ser_3, critical=True),
    ])

    # ── Scientific ─────────────────────────────────────────────────────
    flow.register("scientific", [
        PhaseStep(2, "Hypotheses",          pipeline._phase_scientific_hypothesize, _ser_2),
        PhaseStep(3, "Falsification Tests", pipeline._phase_scientific_test,        _ser_3),
        PhaseStep(4, "Stress Testing",      pipeline._phase_4_stress_test,          _ser_4),
    ])

    # ── Socratic ───────────────────────────────────────────────────────
    flow.register("socratic", [
        PhaseStep(2, "Maieutic Questions", pipeline._phase_socratic_question, _ser_2),
        PhaseStep(3, "Dialectic Answers",  pipeline._phase_socratic_answer,   _ser_3),
    ])

    # ── Pre-Mortem ─────────────────────────────────────────────────────
    flow.register("pre_mortem", [
        PhaseStep(2, "Failure Narrative",   pipeline._phase_pre_mortem_failure,   _ser_2),
        PhaseStep(3, "Root Cause Analysis", pipeline._phase_pre_mortem_backtrack, _ser_3),
        PhaseStep(4, "Early Warning Signals", pipeline._phase_pre_mortem_signals, _ser_4),
        PhaseStep(5, "Hardened Redesign",   pipeline._phase_pre_mortem_redesign,  _ser_5),
    ])

    # ── Bayesian ───────────────────────────────────────────────────────
    flow.register("bayesian", [
        PhaseStep(2, "Priors & Hypotheses",  pipeline._phase_bayesian_priors,      _ser_2),
        PhaseStep(3, "Likelihood Update",    pipeline._phase_bayesian_likelihood,  _ser_3),
        PhaseStep(4, "Posterior Analysis",   pipeline._phase_bayesian_posterior,   _ser_4),
        PhaseStep(5, "Sensitivity Analysis", pipeline._phase_bayesian_sensitivity, _ser_5),
    ])

    # ── Dialectical ────────────────────────────────────────────────────
    flow.register("dialectical", [
        PhaseStep(2, "Thesis",              pipeline._phase_dialectical_thesis,         _ser_2),
        PhaseStep(3, "Antithesis",          pipeline._phase_dialectical_antithesis,     _ser_3),
        PhaseStep(4, "Contradictions",      pipeline._phase_dialectical_contradictions, _ser_4),
        PhaseStep(5, "Aufhebung",           pipeline._phase_dialectical_aufhebung,      _ser_5),
    ])

    # ── Analogical ─────────────────────────────────────────────────────
    flow.register("analogical", [
        PhaseStep(2, "Abstraction",      pipeline._phase_analogical_abstraction,     _ser_2),
        PhaseStep(3, "Domain Search",    pipeline._phase_analogical_domain_search,   _ser_3),
        PhaseStep(4, "Mapping",          pipeline._phase_analogical_mapping,         _ser_4),
        PhaseStep(5, "Transfer",         pipeline._phase_analogical_transfer,        _ser_5),
    ])

    # ── Delphi ─────────────────────────────────────────────────────────
    flow.register("delphi", [
        PhaseStep(2, "Round 1 Estimates",    pipeline._phase_delphi_round1,        _ser_2),
        PhaseStep(3, "Aggregation",          pipeline._phase_delphi_aggregation,   _ser_3),
        PhaseStep(4, "Round 2 Estimates",    pipeline._phase_delphi_round2,        _ser_4),
        PhaseStep(5, "Convergence",          pipeline._phase_delphi_convergence,   _ser_5),
        PhaseStep(6, "Dissent Report",       pipeline._phase_delphi_dissent,       _ser_5),
    ])

    # ── CoVE (Chain-of-Verification) ───────────────────────────────────
    flow.register("cove", [
        PhaseStep(2, "Draft Answer",       pipeline._phase_cove_draft,   _ser_2),
        PhaseStep(3, "Verification",       pipeline._phase_cove_verify,  _ser_3),
        PhaseStep(4, "Revised Answer",     pipeline._phase_cove_answer,  _ser_4),
        PhaseStep(5, "Final Revision",     pipeline._phase_cove_revise,  _ser_5),
    ])

    # ── SoT (Skeleton-of-Thought) ──────────────────────────────────────
    flow.register("sot", [
        PhaseStep(2, "Skeleton",   pipeline._phase_sot_skeleton,  _ser_2),
        PhaseStep(3, "Solve",      pipeline._phase_sot_solve,     _ser_3),
        PhaseStep(4, "Assemble",   pipeline._phase_sot_assemble,  _ser_4),
    ])

    # ── ToT (Tree-of-Thought) ──────────────────────────────────────────
    flow.register("tot", [
        PhaseStep(2, "Decompose",  pipeline._phase_tot_decompose,  _ser_2),
        PhaseStep(3, "Generate",   pipeline._phase_tot_generate,   _ser_3),
        PhaseStep(4, "Evaluate",   pipeline._phase_tot_evaluate,   _ser_4),
        PhaseStep(5, "Backtrack",  pipeline._phase_tot_backtrack,  _ser_5),
    ])

    # ── PoT (Program-of-Thought) ───────────────────────────────────────
    flow.register("pot", [
        PhaseStep(2, "Generate Code",    pipeline._phase_pot_generate,   _ser_2),
        PhaseStep(3, "Execute",          pipeline._phase_pot_execute,    _ser_3),
        PhaseStep(4, "Interpret",        pipeline._phase_pot_interpret,  _ser_4),
    ])

    # ── Self-Discover ──────────────────────────────────────────────────
    flow.register("self_discover", [
        PhaseStep(2, "Select Modules",   pipeline._phase_sd_select,    _ser_2),
        PhaseStep(3, "Adapt Modules",    pipeline._phase_sd_adapt,     _ser_3),
        PhaseStep(4, "Implement",        pipeline._phase_sd_implement, _ser_4),
    ])

    return flow
