from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from reasoner.models import PipelineState


def _is_orchestrated(preset: str) -> bool:
    return preset in ("jury", "jury-budget", "jury-balanced", "jury-premium", "orchestrated")

def _is_debate(preset: str) -> bool:
    return "debate" in preset

def _is_scientific(preset: str) -> bool:
    return "scientific" in preset

def _is_socratic(preset: str) -> bool:
    return "socratic" in preset

def _is_iterative(preset: str) -> bool:
    return "iterative" in preset

def _get_v(obj, key, default=None):
    if obj is None: return default
    if isinstance(obj, dict):
        val = obj.get(key, default)
        return default if val is None else val
    val = getattr(obj, key, default)
    return default if val is None else val

def _ser_0(state: PipelineState) -> dict:
    tt = _get_v(state, 'task_type')
    return {
        "task_type": tt.value if hasattr(tt, 'value') else str(tt or "unknown"),
        "rationale": _get_v(state, 'task_type_rationale', ''),
        "language": _get_v(state, 'language', 'English'),
        "tokens": state.phase_tokens.get("Phase 0: Classification", {"input": 0, "output": 0}),
    }

def _ser_1(state: PipelineState) -> dict:
    dec = _get_v(state, 'decomposition')
    if not dec: return {}

    # Handle both object and dict formats
    sub_problems = _get_v(dec, 'sub_problems', [])
    assumptions = _get_v(dec, 'assumptions', [])

    return {
        "sub_problems": [
            {
                "id": _get_v(sp, 'id', ''),
                "description": _get_v(sp, 'description', ''),
                "constraints": _get_v(sp, 'constraints', [])
            } for sp in sub_problems
        ],
        "assumptions": [
            {
                "text": _get_v(a, 'text', ''),
                "label": (lambda x: x.value if hasattr(x, 'value') else str(x))(_get_v(a, 'label', 'UNKNOWN')),
                "rationale": _get_v(a, 'rationale', '')
            } for a in assumptions
        ],
        "failure_modes": _get_v(dec, 'failure_modes', []),
        "tokens": state.phase_tokens.get("Phase 1: Decomposition", {"input": 0, "output": 0}),
    }

def _ser_1_5(state: PipelineState) -> dict:
    """Deep Read serializer."""
    return {
        "web_discovery_results": _get_v(state, 'web_discovery_results', []),
        "vetted_context": _get_v(state, 'vetted_context', []),
        "tokens": state.phase_tokens.get("Phase 1.5: Deep Read", {"input": 0, "output": 0}),
    }

def _ser_2(state: PipelineState) -> dict:
    candidates = _get_v(state, 'candidates', [])
    gen_candidates = _get_v(state, 'generation_candidates', [])

    result = {
        "candidates": [
            {
                "perspective": (lambda x: x.value if hasattr(x, 'value') else str(x))(_get_v(c, 'perspective', '')),
                "content": _get_v(c, 'content', ''),
                "key_insights": _get_v(c, 'key_insights', []),
                "model_used": _get_v(c, 'model_used', ''),
            } for c in candidates
        ],
        "tokens": {"input": 0, "output": 0},
    }

    if gen_candidates:
        result["generation_candidates"] = [
            {
                "generator_id": _get_v(gc, 'generator_id', ''),
                "model_used": _get_v(gc, 'model_used', ''),
                "solution": _get_v(gc, 'solution', ''),
                "confidence": _get_v(gc, 'confidence', 0),
                "key_claims": _get_v(gc, 'key_claims', []),
                "approach_summary": _get_v(gc, 'approach_summary', ''),
            } for gc in gen_candidates
        ]

    # Add other states safely
    for field in ['scientific_state', 'socratic_state', 'debate_rounds', 'web_discovery_results']:
        val = _get_v(state, field)
        if val: result[field] = val

    return result

def _ser_3(state: PipelineState) -> dict:
    scores = _get_v(state, 'scores', [])
    top_candidates = _get_v(state, 'top_candidates', [])
    top_perspectives = {(_get_v(c, 'perspective').value if hasattr(_get_v(c, 'perspective'), 'value') else str(_get_v(c, 'perspective'))) for c in top_candidates}

    result = {
        "scores": [
            {
                "perspective": (lambda x: x.value if hasattr(x, 'value') else str(x))(_get_v(s, 'perspective', '')),
                "logical_consistency": _get_v(s, 'logical_consistency', 0),
                "evidence_support": _get_v(s, 'evidence_support', 0),
                "failure_resilience": _get_v(s, 'failure_resilience', 0),
                "feasibility": _get_v(s, 'feasibility', 0),
                "total": round(_get_v(s, 'total', 0), 2),
                "bias_flags": _get_v(s, 'bias_flags', []),
                "steel_man": _get_v(s, 'steel_man', ''),
                "is_top": (lambda x: x.value if hasattr(x, 'value') else str(x))(_get_v(s, 'perspective')) in top_perspectives,
            } for s in sorted(scores, key=lambda x: _get_v(x, 'total', 0), reverse=True)
        ],
        "tokens": state.phase_tokens.get("Phase 3: Critique & Pruning", {"input": 0, "output": 0}),
    }

    # Fallback for debate rebuttals when scores are empty
    if not result["scores"]:
        debate_rounds = _get_v(state, 'debate_rounds', [])
        rebuttals = [r for r in debate_rounds if isinstance(r, dict) and r.get('type') == 'rebuttal']
        if rebuttals:
            result["debate_rebuttals"] = rebuttals

        # Fallback for scientific falsification tests
        scientific_state = _get_v(state, 'scientific_state')
        if scientific_state and isinstance(scientific_state, dict):
            result["scientific_state"] = scientific_state

        # Fallback for socratic dialectic answers
        socratic_state = _get_v(state, 'socratic_state')
        if socratic_state and isinstance(socratic_state, dict):
            result["socratic_state"] = socratic_state

    return result

def _ser_4(state: PipelineState) -> dict:
    stress = _get_v(state, 'stress_results', [])
    verif = _get_v(state, 'verification_results', [])
    meta = _get_v(state, 'meta_evaluation')
    scores = _get_v(state, 'scores', [])

    result = {
        "tests": [
            {
                "scenario": (lambda x: x.value if hasattr(x, 'value') else str(x))(_get_v(sr, 'scenario', '')),
                "survival_rate": _get_v(sr, 'survival_rate', 0),
                "failure_mode": _get_v(sr, 'failure_mode', ''),
                "recovery_path": _get_v(sr, 'recovery_path', ''),
            } for sr in stress
        ],
        "tokens": state.phase_tokens.get("Phase 4: Stress Testing", {"input": 0, "output": 0}),
    }

    if verif:
        result["verification_results"] = [
            {
                "claim": _get_v(vr, 'claim', ''),
                "source_generator": _get_v(vr, 'source_generator', ''),
                "verdict": (lambda x: x.value if hasattr(x, 'value') else str(x))(_get_v(vr, 'verdict', '')),
                "evidence": _get_v(vr, 'evidence', ''),
                "confidence": _get_v(vr, 'confidence', 0),
            } for vr in verif
        ]

    if meta:
        result["meta_evaluation"] = {
            "critic_reliability": _get_v(meta, 'critic_reliability', {}),
            "bias_analysis": _get_v(meta, 'bias_analysis', {}),
            "agreement_rate": _get_v(meta, 'agreement_rate', 0),
            "most_reliable_critic": _get_v(meta, 'most_reliable_critic', ''),
            "least_reliable_critic": _get_v(meta, 'least_reliable_critic', ''),
            "meta_insight": _get_v(meta, 'meta_insight', ''),
        }

    # Fallback for debate judge / jury verification when primary fields are empty
    if not stress and not verif and scores:
        result["scores"] = [
            {
                "perspective": (lambda x: x.value if hasattr(x, 'value') else str(x))(_get_v(s, 'perspective', '')),
                "total": round(_get_v(s, 'total', 0), 2),
                "steel_man": _get_v(s, 'steel_man', ''),
            } for s in sorted(scores, key=lambda x: _get_v(x, 'total', 0), reverse=True)
        ]

    return result

def _ser_5(state: PipelineState) -> dict:
    fs = _get_v(state, 'final_solution')
    if fs is None:
        return {}

    meta = _get_v(fs, 'meta_audit', {})

    # Action blueprint handling
    raw_bp = _get_v(fs, 'action_blueprint', [])
    clean_bp = []
    for step in (raw_bp if isinstance(raw_bp, list) else []):
        if isinstance(step, dict):
            # Only accept dicts that have at least one expected key or a non-empty action
            if not any(k in step for k in ("step", "action", "time_horizon", "go_criteria", "fallback")):
                continue
            entry = {
                "step": _get_v(step, 'step', ''),
                "action": _get_v(step, 'action', ''),
                "time_horizon": _get_v(step, 'time_horizon', ''),
                "go_criteria": _get_v(step, 'go_criteria', ''),
                "fallback": _get_v(step, 'fallback', '')
            }
            if entry["step"] or entry["action"]:
                clean_bp.append(entry)
        elif step is not None and str(step).strip():
            clean_bp.append({"step": "", "action": str(step).strip(), "time_horizon": "", "go_criteria": "", "fallback": ""})

    # Claim labels handling
    raw_labels = _get_v(fs, 'claim_labels', {})
    clean_labels = {k: (v.value if hasattr(v, 'value') else str(v)) for k, v in (raw_labels.items() if isinstance(raw_labels, dict) else {})}

    # Aggregate tokens across all phases
    total_input = sum(t.get("input", 0) for t in state.phase_tokens.values())
    total_output = sum(t.get("output", 0) for t in state.phase_tokens.values())

    # Build meta_audit only when source data exists
    meta_audit: dict[str, Any] = {}
    if meta:
        meta_audit = {
            "most_dangerous_assumption": _get_v(meta, 'most_dangerous_assumption', ''),
            "dominant_bias": _get_v(meta, 'dominant_bias', ''),
            "remaining_uncertainty": _get_v(meta, 'remaining_uncertainty', ''),
            "assumption_failure_impact": _get_v(meta, 'assumption_failure_impact', ''),
            "non_obvious_insight": _get_v(meta, 'non_obvious_insight', ''),
        }

    return {
        "core_solution": _get_v(fs, 'core_solution', ''),
        "critical_insights": _get_v(fs, 'critical_insights', []),
        "action_blueprint": clean_bp,
        "open_questions": _get_v(fs, 'open_questions', []),
        "claim_labels": clean_labels,
        "meta_audit": meta_audit,
        "tokens": {"input": total_input, "output": total_output}
    }


def _event(data: dict) -> str:
    def json_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    return f"data: {json.dumps(data, default=json_serializer)}\n\n"
