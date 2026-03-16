"""
ARA Pipeline - Output Renderer
Rich terminal display and JSON export, with method-specific layouts.

Methods:
  MULTI_PERSPECTIVE — 4 perspectives: constructive, destructive, systemic, minimalist
  DEBATE            — adversarial competition: Proposition vs Opposition → Verdict
  ITERATIVE         — generate → evaluate → select → refine (loop up to 5x)
  RESEARCH          — evidence report: quality matrix, claim verification, evidence gaps
  JURY              — 3 generators → 3 critics → verification → meta-evaluation → verdict
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from enum import Enum
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from models import ClaimLabel, PerspectiveType, PipelineState

console = Console()


# ─────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────

def _get_attr(obj, key, default=None):
    """Safely get attribute from dict or object."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


# ─────────────────────────────────────────────────────────────────────
# METHOD DETECTION
# ─────────────────────────────────────────────────────────────────────

class MethodType(Enum):
    MULTI_PERSPECTIVE = "multi-perspective"
    DEBATE            = "debate"
    ITERATIVE         = "iterative"
    RESEARCH          = "research"
    JURY              = "jury"
    SCIENTIFIC        = "scientific"
    SOCRATIC          = "socratic"
    PRE_MORTEM        = "pre-mortem"
    BAYESIAN          = "bayesian"
    DIALECTICAL       = "dialectical"
    ANALOGICAL        = "analogical"
    DELPHI            = "delphi"


_DEBATE_PRESETS       = {"debate", "debate-budget", "debate-balanced", "debate-premium"}
_ITERATIVE_PRESETS    = {
    "iterative", "iterative-budget", "iterative-balanced", "iterative-premium",
    "evolutionary", "evolutionary-budget", "evolutionary-balanced",
}
_RESEARCH_PRESETS     = {"research", "research-budget", "research-balanced", "research-premium", "research-local-budget"}
_JURY_PRESETS         = {
    "jury", "jury-budget", "jury-balanced", "jury-premium",
    "orchestrated", "orchestrated-budget", "orchestrated-balanced",
}
_SCIENTIFIC_PRESETS   = {"scientific", "scientific-budget", "scientific-premium"}
_SOCRATIC_PRESETS     = {"socratic", "socratic-budget", "socratic-premium"}
_PRE_MORTEM_PRESETS   = {"pre-mortem", "pre-mortem-budget", "pre-mortem-premium"}
_BAYESIAN_PRESETS     = {"bayesian", "bayesian-budget", "bayesian-premium"}
_DIALECTICAL_PRESETS  = {"dialectical", "dialectical-budget", "dialectical-premium"}
_ANALOGICAL_PRESETS   = {"analogical", "analogical-budget", "analogical-premium"}
_DELPHI_PRESETS       = {"delphi", "delphi-budget", "delphi-premium"}
# STANDARD presets (now called MULTI_PERSPECTIVE)
_MULTI_PERSPECTIVE_PRESETS = {
    "max-quality", "cost-efficient", "eu-sovereign", "epistemic-diversity",
    "western-only", "claude-only", "deepseek-only", "basic-budget",
    "multi-perspective-budget", "multi-perspective-premium"
}


def _method_type(preset_name: str | None) -> MethodType:
    if preset_name in _DEBATE_PRESETS:       return MethodType.DEBATE
    if preset_name in _ITERATIVE_PRESETS:    return MethodType.ITERATIVE
    if preset_name in _RESEARCH_PRESETS:     return MethodType.RESEARCH
    if preset_name in _JURY_PRESETS:         return MethodType.JURY
    if preset_name in _SCIENTIFIC_PRESETS:   return MethodType.SCIENTIFIC
    if preset_name in _SOCRATIC_PRESETS:     return MethodType.SOCRATIC
    if preset_name in _PRE_MORTEM_PRESETS:   return MethodType.PRE_MORTEM
    if preset_name in _BAYESIAN_PRESETS:     return MethodType.BAYESIAN
    if preset_name in _DIALECTICAL_PRESETS:  return MethodType.DIALECTICAL
    if preset_name in _ANALOGICAL_PRESETS:   return MethodType.ANALOGICAL
    if preset_name in _DELPHI_PRESETS:       return MethodType.DELPHI
    if preset_name in _MULTI_PERSPECTIVE_PRESETS: return MethodType.MULTI_PERSPECTIVE
    return MethodType.MULTI_PERSPECTIVE  # default


# ─────────────────────────────────────────────────────────────────────
# SHARED HELPERS
# ─────────────────────────────────────────────────────────────────────

def _label_color(label: ClaimLabel) -> str:
    return {
        ClaimLabel.VERIFIED:   "green",
        ClaimLabel.HYPOTHESIS: "yellow",
        ClaimLabel.UNKNOWN:    "red",
    }.get(label, "white")


def _duration(state: PipelineState) -> float:
    return (datetime.now() - state.started_at).total_seconds()


def _render_stress(state: PipelineState, section_title: str = "Phase 4 — Stress Tests") -> None:
    if not state.stress_results:
        return
    stress_text = Text()
    for sr in state.stress_results:
        color = "green" if sr.survival_rate > 0.7 else "yellow" if sr.survival_rate > 0.4 else "red"
        stress_text.append(f"[{sr.scenario.value.upper()}] ", style="bold")
        stress_text.append("Survival: ", style="white")
        stress_text.append(f"{sr.survival_rate:.0%}\n", style=color)
        stress_text.append(f"  Failure: {sr.failure_mode}\n", style="dim")
        stress_text.append(f"  Recovery: {sr.recovery_path}\n\n", style="dim cyan")
    console.print(Panel(stress_text, title=f"[cyan]{section_title}[/cyan]", box=box.ROUNDED))


def _render_action_blueprint(state: PipelineState, title: str = "Action Blueprint") -> None:
    fs = state.final_solution
    if not fs:
        return
    
    action_blueprint = _get_attr(fs, 'action_blueprint', [])
    if not action_blueprint:
        return
        
    table = Table(title=title, box=box.SIMPLE_HEAVY)
    table.add_column("#", width=3)
    table.add_column("Action")
    table.add_column("Horizon", width=12)
    table.add_column("Go Criteria")
    table.add_column("Fallback")
    for step in action_blueprint:
        table.add_row(
            str(step.get("step", "?")),
            str(step.get("action", "")),
            str(step.get("time_horizon", "")),
            str(step.get("go_criteria", "")),
            str(step.get("fallback", "")),
        )
    console.print(table)


def _render_errors(state: PipelineState) -> None:
    if state.errors:
        err_text = "\n".join(f"• {e}" for e in state.errors)
        console.print(Panel(
            err_text,
            title=f"[yellow]Pipeline Warnings ({len(state.errors)})[/yellow]",
            box=box.ROUNDED,
        ))


# ─────────────────────────────────────────────────────────────────────
# ROUTING TABLE (used in standard + research)
# ─────────────────────────────────────────────────────────────────────

def render_routing_table(state: PipelineState) -> None:
    """Render a table showing which model handled each phase."""
    if not state.phase_models:
        return
    table = Table(title="Model Routing", box=box.SIMPLE_HEAVY, show_header=True)
    table.add_column("Phase / Role", style="cyan", width=20)
    table.add_column("Model Used", style="white")

    role_labels = {
        "classification":  "Ph0  Classification",
        "decomposition":   "Ph1  Decomposition",
        "constructive":    "Ph2a Constructive",
        "destructive":     "Ph2b Destructive",
        "systemic":        "Ph2c Systemic",
        "minimalist":      "Ph2d Minimalist",
        "scoring":         "Ph3  Scoring / Critique",
        "stress_testing":  "Ph4  Stress Testing",
        "synthesis":       "Ph5  Synthesis",
    }

    all_roles = list(role_labels.keys()) + [
        r for r in state.phase_models if r not in role_labels
    ]

    for role in all_roles:
        if role in state.phase_models:
            label = role_labels.get(role, role)
            table.add_row(label, state.phase_models[role])

    console.print(table)


# ─────────────────────────────────────────────────────────────────────
# MULTI-PERSPECTIVE RENDERER
# ─────────────────────────────────────────────────────────────────────

def _render_multi_perspective(state: PipelineState) -> None:
    duration = _duration(state)
    console.rule(f"[bold blue]ARA v2.0 Pipeline Complete ({duration:.1f}s)[/bold blue]")

    render_routing_table(state)

    console.print(Panel(
        f"[bold]Task Type:[/bold] {state.task_type.value if state.task_type else 'unknown'}\n"
        f"[bold]Rationale:[/bold] {state.task_type_rationale}",
        title="[cyan]Phase 0 — Classification[/cyan]",
        box=box.ROUNDED,
    ))

    if state.decomposition:
        dec = state.decomposition
        dec_text = Text()
        for sp in dec.sub_problems:
            dec_text.append(f"• {sp.id}: {sp.description}\n", style="white")
        dec_text.append("\nAssumptions:\n", style="bold")
        for a in dec.assumptions:
            color = _label_color(a.label)
            dec_text.append(f"  [{a.label.value}] ", style=color)
            dec_text.append(f"{a.text}\n")
        console.print(Panel(dec_text, title="[cyan]Phase 1 — Decomposition[/cyan]", box=box.ROUNDED))

    if state.scores:
        table = Table(title="Phase 3 — Critique Scores", box=box.SIMPLE_HEAVY)
        table.add_column("Perspective", style="cyan")
        table.add_column("Logic", justify="center")
        table.add_column("Evidence", justify="center")
        table.add_column("Resilience", justify="center")
        table.add_column("Feasibility", justify="center")
        table.add_column("Total", justify="center", style="bold")
        table.add_column("Biases")

        for s in sorted(state.scores, key=lambda x: x.total, reverse=True):
            is_top = s.perspective in [c.perspective for c in state.top_candidates]
            row_style = "bold green" if is_top else ""
            table.add_row(
                s.perspective.value,
                f"{s.logical_consistency:.1f}",
                f"{s.evidence_support:.1f}",
                f"{s.failure_resilience:.1f}",
                f"{s.feasibility:.1f}",
                f"[bold]{s.total:.1f}[/bold]",
                ", ".join(s.bias_flags[:2]) if s.bias_flags else "—",
                style=row_style,
            )
        console.print(table)

    _render_stress(state)

    if state.final_solution:
        fs = state.final_solution

        console.print(Panel(
            _get_attr(fs, 'core_solution', ''),
            title="[bold green]CORE SOLUTION[/bold green]",
            box=box.DOUBLE,
            border_style="green",
        ))

        insights_text = Text()
        for i, insight in enumerate(_get_attr(fs, 'critical_insights', []), 1):
            insights_text.append(f"{i}. {insight}\n\n")
        console.print(Panel(insights_text, title="[yellow]Critical Insights[/yellow]", box=box.ROUNDED))

        _render_action_blueprint(state)

        if _get_attr(fs, 'open_questions', []):
            oq_text = "\n".join(f"• {q}" for q in _get_attr(fs, 'open_questions', []))
            console.print(Panel(oq_text, title="[red]Open Questions (Unresolved)[/red]", box=box.ROUNDED))

        meta = _get_attr(fs, 'meta_audit', {})
        meta_text = (
            f"[bold]Most dangerous assumption:[/bold] {_get_attr(meta, 'most_dangerous_assumption', '')}\n"
            f"[bold]Dominant bias:[/bold] {_get_attr(meta, 'dominant_bias', '')}\n"
            f"[bold]Remaining uncertainty:[/bold] {_get_attr(meta, 'remaining_uncertainty', '')}\n"
            f"[bold]If main assumption fails:[/bold] {_get_attr(meta, 'assumption_failure_impact', '')}\n"
            f"[bold]Non-obvious insight:[/bold] [italic]{_get_attr(meta, 'non_obvious_insight', '')}[/italic]"
        )
        console.print(Panel(meta_text, title="[cyan]Meta-Cognitive Audit[/cyan]", box=box.ROUNDED))

    _render_errors(state)


# ─────────────────────────────────────────────────────────────────────
# DEBATE RENDERER
# ─────────────────────────────────────────────────────────────────────

def _render_debate(state: PipelineState) -> None:
    duration = _duration(state)
    console.rule(f"[bold magenta]DEBATE ARENA  ({duration:.1f}s)[/bold magenta]")

    prop_model  = state.phase_models.get("constructive", "?")
    opp_model   = state.phase_models.get("destructive",  "?")
    judge_model = state.phase_models.get("scoring",      "?")

    combatants = Table(title="Combatants", box=box.SIMPLE_HEAVY)
    combatants.add_column("Role", style="cyan", width=22)
    combatants.add_column("Model", style="white")
    combatants.add_row("Proposition (Model A)", prop_model)
    combatants.add_row("Opposition  (Model B)", opp_model)
    combatants.add_row("Judge",                 judge_model)
    console.print(combatants)

    console.print(Panel(state.problem, title="[bold cyan]THE MOTION[/bold cyan]", box=box.ROUNDED))

    if state.task_type:
        console.print(Panel(
            f"[bold]Task type:[/bold] {state.task_type.value}  |  {state.task_type_rationale}",
            title="[cyan]Classification[/cyan]",
            box=box.ROUNDED,
        ))

    prop_cand = next((c for c in state.candidates if c.perspective == PerspectiveType.CONSTRUCTIVE), None)
    opp_cand  = next((c for c in state.candidates if c.perspective == PerspectiveType.DESTRUCTIVE),  None)

    if prop_cand:
        prop_text = Text()
        prop_text.append(prop_cand.content + "\n")
        if prop_cand.key_insights:
            prop_text.append("\nKey Insights:\n", style="bold yellow")
            for ins in prop_cand.key_insights:
                prop_text.append(f"  • {ins}\n", style="yellow")
        console.print(Panel(prop_text, title=f"[green]PROPOSITION — {prop_model}[/green]", box=box.ROUNDED))

    if opp_cand:
        opp_text = Text()
        opp_text.append(opp_cand.content + "\n")
        if opp_cand.key_insights:
            opp_text.append("\nKey Insights:\n", style="bold red")
            for ins in opp_cand.key_insights:
                opp_text.append(f"  • {ins}\n", style="red")
        console.print(Panel(opp_text, title=f"[red]OPPOSITION — {opp_model}[/red]", box=box.ROUNDED))

    prop_score = next((s for s in state.scores if s.perspective == PerspectiveType.CONSTRUCTIVE), None)
    opp_score  = next((s for s in state.scores if s.perspective == PerspectiveType.DESTRUCTIVE),  None)

    if prop_score and opp_score:
        scorecard = Table(title="Judge's Scorecard", box=box.SIMPLE_HEAVY)
        scorecard.add_column("Criterion",   style="cyan",  width=14)
        scorecard.add_column("Proposition", justify="center", style="green")
        scorecard.add_column("Opposition",  justify="center", style="red")

        def _sr(label: str, p: float, o: float) -> tuple[str, str, str]:
            pb = f"[bold]{p:.1f}[/bold]" if p > o else f"{p:.1f}"
            ob = f"[bold]{o:.1f}[/bold]" if o > p else f"{o:.1f}"
            return label, pb, ob

        scorecard.add_row(*_sr("Logic",       prop_score.logical_consistency, opp_score.logical_consistency))
        scorecard.add_row(*_sr("Evidence",    prop_score.evidence_support,    opp_score.evidence_support))
        scorecard.add_row(*_sr("Resilience",  prop_score.failure_resilience,  opp_score.failure_resilience))
        scorecard.add_row(*_sr("Feasibility", prop_score.feasibility,         opp_score.feasibility))
        p_total = f"[bold green]{prop_score.total:.1f}[/bold green]" if prop_score.total >= opp_score.total else f"[bold]{prop_score.total:.1f}[/bold]"
        o_total = f"[bold red]{opp_score.total:.1f}[/bold red]"      if opp_score.total > prop_score.total  else f"[bold]{opp_score.total:.1f}[/bold]"
        scorecard.add_row("TOTAL", p_total, o_total)
        console.print(scorecard)

        margin = abs(prop_score.total - opp_score.total)
        if prop_score.total >= opp_score.total:
            winner_label = f"PROPOSITION WINS  ({prop_model})  by +{margin:.1f} points"
            winner_style = "bold green on dark_green"
            loser_score  = opp_score
        else:
            winner_label = f"OPPOSITION WINS  ({opp_model})  by +{margin:.1f} points"
            winner_style = "bold red on dark_red"
            loser_score  = prop_score

        console.print(Panel(winner_label, style=winner_style, box=box.DOUBLE))

        if loser_score.steel_man:
            console.print(Panel(
                loser_score.steel_man,
                title="[yellow]Dissenting View (Strongest Counter-Argument)[/yellow]",
                box=box.ROUNDED,
            ))

    _render_stress(state, "Challenge Scenarios")

    if state.final_solution:
        fs = state.final_solution

        console.print(Panel(
            _get_attr(fs, 'core_solution', ''),
            title="[bold green]VERDICT[/bold green]",
            box=box.DOUBLE,
            border_style="green",
        ))

        if _get_attr(fs, 'critical_insights', []):
            ins_text = Text()
            for i, insight in enumerate(_get_attr(fs, 'critical_insights', []), 1):
                ins_text.append(f"{i}. {insight}\n\n")
            console.print(Panel(ins_text, title="[yellow]Key Findings[/yellow]", box=box.ROUNDED))

        _render_action_blueprint(state, title="Implementation Ruling")

        if _get_attr(fs, 'open_questions', []):
            oq_text = "\n".join(f"• {q}" for q in _get_attr(fs, 'open_questions', []))
            console.print(Panel(oq_text, title="[red]Unresolved Points[/red]", box=box.ROUNDED))

        meta = _get_attr(fs, 'meta_audit', {})
        meta_text = (
            f"[bold]Most dangerous assumption:[/bold] {_get_attr(meta, 'most_dangerous_assumption', '')}\n"
            f"[bold]Dominant bias in judgment:[/bold] {_get_attr(meta, 'dominant_bias', '')}\n"
            f"[bold]Remaining uncertainty:[/bold] {_get_attr(meta, 'remaining_uncertainty', '')}\n"
            f"[bold]If main assumption fails:[/bold] {_get_attr(meta, 'assumption_failure_impact', '')}\n"
            f"[bold]Non-obvious insight:[/bold] [italic]{_get_attr(meta, 'non_obvious_insight', '')}[/italic]"
        )
        console.print(Panel(meta_text, title="[cyan]Judge's Reservations[/cyan]", box=box.ROUNDED))

    _render_errors(state)


# ─────────────────────────────────────────────────────────────────────
# ITERATIVE RENDERER
# ─────────────────────────────────────────────────────────────────────

def _render_iterative(state: PipelineState) -> None:
    duration = _duration(state)
    console.rule(f"[bold yellow]ITERATIVE OPTIMIZATION  ({duration:.1f}s)[/bold yellow]")

    score_map = {s.perspective: s for s in state.scores}

    if state.candidates:
        pop_table = Table(title="Generation 0 — Initial Population", box=box.SIMPLE_HEAVY)
        pop_table.add_column("Perspective", style="cyan")
        pop_table.add_column("Model", style="white")
        pop_table.add_column("Key Strength", style="white")

        survivors = {c.perspective for c in state.top_candidates}
        for cand in state.candidates:
            sc = score_map.get(cand.perspective)
            fitness_str = f"fitness={sc.total:.1f}" if sc else "—"
            strength = cand.key_insights[0] if cand.key_insights else "—"
            is_survivor = cand.perspective in survivors
            pop_table.add_row(
                f"{cand.perspective.value}  [{fitness_str}]",
                cand.model_used or "—",
                strength[:80] + ("…" if len(strength) > 80 else ""),
                style="bold green" if is_survivor else "",
            )
        console.print(pop_table)

    if state.scores:
        fit_table = Table(title="Fitness Evaluation", box=box.SIMPLE_HEAVY)
        fit_table.add_column("Individual",  style="cyan")
        fit_table.add_column("Logic",       justify="center")
        fit_table.add_column("Evidence",    justify="center")
        fit_table.add_column("Resilience",  justify="center")
        fit_table.add_column("Feasibility", justify="center")
        fit_table.add_column("Fitness",     justify="center", style="bold")
        fit_table.add_column("Weaknesses")

        survivors = {c.perspective for c in state.top_candidates}
        for s in sorted(state.scores, key=lambda x: x.total, reverse=True):
            is_survivor = s.perspective in survivors
            tag = " [SURVIVOR]" if is_survivor else " [ELIMINATED]"
            fit_table.add_row(
                s.perspective.value + tag,
                f"{s.logical_consistency:.1f}",
                f"{s.evidence_support:.1f}",
                f"{s.failure_resilience:.1f}",
                f"{s.feasibility:.1f}",
                f"[bold]{s.total:.1f}[/bold]",
                ", ".join(s.bias_flags[:2]) if s.bias_flags else "—",
                style="bold green" if is_survivor else "dim",
            )
        console.print(fit_table)

        if state.top_candidates:
            surv_text = Text()
            for c in state.top_candidates:
                sc = score_map.get(c.perspective)
                fit = f"{sc.total:.1f}" if sc else "?"
                surv_text.append(f"+ {c.perspective.value}  (fitness={fit})\n", style="bold green")
            console.print(Panel(surv_text, title="[green]Selected Survivors[/green]", box=box.ROUNDED))

    _render_stress(state, "Environmental Pressure Tests")

    if state.final_solution:
        fs = state.final_solution

        console.print(Panel(
            _get_attr(fs, 'core_solution', ''),
            title="[bold green]OPTIMIZED SOLUTION[/bold green]",
            box=box.DOUBLE,
            border_style="green",
        ))

        if _get_attr(fs, 'critical_insights', []):
            em_text = Text()
            for i, insight in enumerate(_get_attr(fs, 'critical_insights', []), 1):
                em_text.append(f"{i}. {insight}\n\n")
            console.print(Panel(em_text, title="[yellow]Emergent Properties[/yellow]", box=box.ROUNDED))

        _render_action_blueprint(state, title="Survival Strategy")

        if _get_attr(fs, 'open_questions', []):
            oq_text = "\n".join(f"• {q}" for q in _get_attr(fs, 'open_questions', []))
            console.print(Panel(oq_text, title="[red]Open Hypotheses[/red]", box=box.ROUNDED))

        meta = _get_attr(fs, 'meta_audit', {})
        meta_text = (
            f"[bold]Critical vulnerability:[/bold] {_get_attr(meta, 'most_dangerous_assumption', '')}\n"
            f"[bold]Iterative pressure detected:[/bold] {_get_attr(meta, 'dominant_bias', '')}\n"
            f"[bold]Remaining uncertainty:[/bold] {_get_attr(meta, 'remaining_uncertainty', '')}\n"
            f"[bold]If vulnerability exploited:[/bold] {_get_attr(meta, 'assumption_failure_impact', '')}\n"
            f"[bold]Emergent insight:[/bold] [italic]{_get_attr(meta, 'non_obvious_insight', '')}[/italic]"
        )
        console.print(Panel(meta_text, title="[cyan]Iterative Forces[/cyan]", box=box.ROUNDED))

    _render_errors(state)


# ─────────────────────────────────────────────────────────────────────
# RESEARCH RENDERER
# ─────────────────────────────────────────────────────────────────────

def _render_research(state: PipelineState) -> None:
    duration = _duration(state)
    console.rule(f"[bold blue]EVIDENCE SYNTHESIS REPORT  ({duration:.1f}s)[/bold blue]")

    if state.phase_models:
        infra_table = Table(title="Research Infrastructure", box=box.SIMPLE_HEAVY)
        infra_table.add_column("Phase / Role", style="cyan", width=22)
        infra_table.add_column("Model",        style="white")
        infra_table.add_column("Type",         style="white", width=14)

        role_labels = {
            "classification":  "Ph0  Classification",
            "decomposition":   "Ph1  Decomposition",
            "constructive":    "Ph2a Constructive",
            "destructive":     "Ph2b Destructive",
            "systemic":        "Ph2c Systemic",
            "minimalist":      "Ph2d Minimalist",
            "scoring":         "Ph3  Scoring",
            "stress_testing":  "Ph4  Stress Testing",
            "synthesis":       "Ph5  Synthesis",
        }
        for role in list(role_labels.keys()) + [r for r in state.phase_models if r not in role_labels]:
            if role in state.phase_models:
                model = state.phase_models[role]
                model_type = "[yellow]Web-grounded[/yellow]" if "sonar" in model else "Offline"
                infra_table.add_row(role_labels.get(role, role), model, model_type)
        console.print(infra_table)

    if state.decomposition:
        dec = state.decomposition
        rq_text = Text()
        for sp in dec.sub_problems:
            rq_text.append(f"RQ {sp.id}: {sp.description}\n", style="bold white")
            if sp.constraints:
                rq_text.append(f"  Constraints: {', '.join(sp.constraints)}\n", style="dim")
        console.print(Panel(rq_text, title="[cyan]Research Question Breakdown[/cyan]", box=box.ROUNDED))

        if dec.assumptions:
            assume_table = Table(title="Evidence Status of Assumptions", box=box.SIMPLE_HEAVY)
            assume_table.add_column("Status",    width=12)
            assume_table.add_column("Assumption")
            assume_table.add_column("Rationale", style="dim")
            for a in dec.assumptions:
                color = _label_color(a.label)
                assume_table.add_row(
                    f"[{color}]{a.label.value}[/{color}]",
                    a.text,
                    a.rationale,
                )
            console.print(assume_table)

    if state.scores:
        eq_table = Table(title="Evidence Quality by Perspective", box=box.SIMPLE_HEAVY)
        eq_table.add_column("Perspective",  style="cyan")
        eq_table.add_column("Logic",        justify="center")
        eq_table.add_column("Evidence",     justify="center", style="bold yellow")
        eq_table.add_column("Resilience",   justify="center")
        eq_table.add_column("Feasibility",  justify="center")
        eq_table.add_column("Total",        justify="center", style="bold")
        eq_table.add_column("Potential Bias")

        for s in sorted(state.scores, key=lambda x: x.evidence_support, reverse=True):
            is_top = s.perspective in [c.perspective for c in state.top_candidates]
            eq_table.add_row(
                s.perspective.value,
                f"{s.logical_consistency:.1f}",
                f"[bold yellow]{s.evidence_support:.1f}[/bold yellow]",
                f"{s.failure_resilience:.1f}",
                f"{s.feasibility:.1f}",
                f"[bold]{s.total:.1f}[/bold]",
                ", ".join(s.bias_flags[:2]) if s.bias_flags else "—",
                style="bold green" if is_top else "",
            )
        console.print(eq_table)

    _render_stress(state, "Adversarial Challenge")

    if state.final_solution:
        fs = state.final_solution

        console.print(Panel(
            _get_attr(fs, 'core_solution', ''),
            title="[bold green]EVIDENCE-GROUNDED SYNTHESIS[/bold green]",
            box=box.DOUBLE,
            border_style="green",
        ))

        if _get_attr(fs, 'claim_labels', {}):
            claim_table = Table(title="Claim Verification Status", box=box.SIMPLE_HEAVY)
            claim_table.add_column("Status", width=14)
            claim_table.add_column("Claim")
            for claim, label in _get_attr(fs, 'claim_labels', {}).items():
                color = _label_color(label)
                claim_table.add_row(f"[{color}]{label.value}[/{color}]", claim)
            console.print(claim_table)

        if _get_attr(fs, 'open_questions', []):
            oq_text = "\n".join(f"• {q}" for q in _get_attr(fs, 'open_questions', []))
            console.print(Panel(oq_text, title="[red]Evidence Gaps (Unverified / Missing Data)[/red]", box=box.ROUNDED))

        if _get_attr(fs, 'critical_insights', []):
            ins_text = Text()
            for i, insight in enumerate(_get_attr(fs, 'critical_insights', []), 1):
                ins_text.append(f"{i}. {insight}\n\n")
            console.print(Panel(ins_text, title="[yellow]Key Findings[/yellow]", box=box.ROUNDED))

        _render_action_blueprint(state, title="Recommended Actions")

        meta = _get_attr(fs, 'meta_audit', {})
        meta_text = (
            f"[bold]Critical evidence gap:[/bold] {_get_attr(meta, 'most_dangerous_assumption', '')}\n"
            f"[bold]Potential researcher bias:[/bold] {_get_attr(meta, 'dominant_bias', '')}\n"
            f"[bold]Remaining uncertainty:[/bold] {_get_attr(meta, 'remaining_uncertainty', '')}\n"
            f"[bold]Impact if gap unresolved:[/bold] {_get_attr(meta, 'assumption_failure_impact', '')}\n"
            f"[bold]Non-obvious finding:[/bold] [italic]{_get_attr(meta, 'non_obvious_insight', '')}[/italic]"
        )
        console.print(Panel(meta_text, title="[cyan]Epistemic Caveats[/cyan]", box=box.ROUNDED))

    _render_errors(state)


# ─────────────────────────────────────────────────────────────────────
# PUBLIC ENTRY POINT
# ─────────────────────────────────────────────────────────────────────

def _render_jury(state: PipelineState) -> None:
    """Render the JURY multi-agent evaluation result."""
    duration = _duration(state)
    console.rule(f"[bold magenta]JURY EVALUATION  ({duration:.1f}s)[/bold magenta]")

    # Generator Pool
    if state.generation_candidates:
        gen_table = Table(title="Generator Pool", box=box.SIMPLE_HEAVY)
        gen_table.add_column("Generator", style="cyan", width=15)
        gen_table.add_column("Model", style="white", width=18)
        gen_table.add_column("Confidence", justify="center", width=12)
        gen_table.add_column("Approach", style="white")

        for gc in state.generation_candidates:
            conf_bar = "█" * int(gc.confidence * 10) + "░" * (10 - int(gc.confidence * 10))
            gen_table.add_row(
                gc.generator_id,
                gc.model_used or "?",
                f"{gc.confidence:.0%} {conf_bar}",
                gc.approach_summary[:60] + ("…" if len(gc.approach_summary) > 60 else ""),
            )
        console.print(gen_table)

    # Critic Scores Matrix
    if state.critic_scores:
        console.print("\n[bold cyan]Critic Scores Matrix[/bold cyan]")
        for cs in state.critic_scores:
            score_text = Text()
            score_text.append(f"[bold]{cs.critic_id}[/bold] ({cs.critic_model})\n", style="cyan")
            for gen_id, ds in cs.candidate_scores.items():
                score_text.append(f"  {gen_id}: ", style="white")
                score_text.append(f"F={ds.factuality:.1f} ", style="green")
                score_text.append(f"R={ds.reasoning:.1f} ", style="blue")
                score_text.append(f"C={ds.completeness:.1f} ", style="yellow")
                score_text.append(f"H={ds.helpfulness:.1f} ", style="magenta")
                score_text.append(f"[bold]Avg={ds.total:.1f}[/bold]\n", style="bold")
            if cs.dissenting_note:
                score_text.append(f"  [yellow]Dissenting:[/yellow] {cs.dissenting_note[:100]}\n", style="yellow")
            console.print(Panel(score_text, box=box.ROUNDED))

    # Verification Results
    if state.verification_results:
        verif_table = Table(title="Verification Results", box=box.SIMPLE_HEAVY)
        verif_table.add_column("Claim", width=40)
        verif_table.add_column("Source", width=12)
        verif_table.add_column("Verdict", width=12)
        verif_table.add_column("Confidence", justify="center", width=12)

        for vr in state.verification_results:
            color = _label_color(vr.verdict)
            verif_table.add_row(
                vr.claim[:40] + ("…" if len(vr.claim) > 40 else ""),
                vr.source_generator,
                f"[{color}]{vr.verdict.value}[/{color}]",
                f"{vr.confidence:.0%}",
            )
        console.print(verif_table)

    # Meta-Evaluation
    if state.meta_evaluation:
        meta = state.meta_evaluation
        meta_text = Text()
        meta_text.append("[bold]Critic Reliability:[/bold]\n", style="cyan")
        for cid, rel in _get_attr(meta, 'critic_reliability', {}).items():
            meta_text.append(f"  {cid}: {rel:.1f}/10\n", style="white")
        meta_text.append(f"\n[bold]Agreement Rate:[/bold] {_get_attr(meta, 'agreement_rate', 0):.0%}\n", style="cyan")
        meta_text.append(f"[bold]Most Reliable:[/bold] {_get_attr(meta, 'most_reliable_critic', '')}\n", style="green")
        meta_text.append(f"[bold]Least Reliable:[/bold] {_get_attr(meta, 'least_reliable_critic', '')}\n", style="red")
        if _get_attr(meta, 'meta_insight', ''):
            meta_text.append(f"\n[bold]Meta Insight:[/bold] {_get_attr(meta, 'meta_insight', '')}\n", style="yellow")
        console.print(Panel(meta_text, title="[cyan]Meta-Evaluation (Judge-the-Judges)[/cyan]", box=box.ROUNDED))

    # Final Solution
    if state.final_solution:
        fs = state.final_solution

        console.print(Panel(
            _get_attr(fs, 'core_solution', ''),
            title="[bold green]FINAL SOLUTION (Jury Verdict)[/bold green]",
            box=box.DOUBLE,
            border_style="green",
        ))

        # Generator Attribution
        if _get_attr(fs, 'generator_attribution', {}):
            attr_text = Text()
            for gid, desc in _get_attr(fs, 'generator_attribution', {}).items():
                attr_text.append(f"[bold]{gid}:[/bold] {desc}\n", style="cyan")
            console.print(Panel(attr_text, title="[cyan]Generator Attribution[/cyan]", box=box.ROUNDED))

        # Critic Weighting
        if _get_attr(fs, 'critic_weighting', {}):
            weight_text = Text()
            for cid, weight in _get_attr(fs, 'critic_weighting', {}).items():
                weight_text.append(f"{cid}: {weight:.1%}\n", style="white")
            console.print(Panel(weight_text, title="[cyan]Critic Weighting (by Reliability)[/cyan]", box=box.ROUNDED))

        if _get_attr(fs, 'critical_insights', []):
            ins_text = Text()
            for i, insight in enumerate(_get_attr(fs, 'critical_insights', []), 1):
                ins_text.append(f"{i}. {insight}\n\n")
            console.print(Panel(ins_text, title="[yellow]Critical Insights[/yellow]", box=box.ROUNDED))

        _render_action_blueprint(state, title="Implementation Plan")

        if _get_attr(fs, 'open_questions', []):
            oq_text = "\n".join(f"• {q}" for q in _get_attr(fs, 'open_questions', []))
            console.print(Panel(oq_text, title="[red]Open Questions[/red]", box=box.ROUNDED))

        meta = _get_attr(fs, 'meta_audit', {})
        meta_text = (
            f"[bold]Most dangerous assumption:[/bold] {_get_attr(meta, 'most_dangerous_assumption', '')}\n"
            f"[bold]Dominant bias:[/bold] {_get_attr(meta, 'dominant_bias', '')}\n"
            f"[bold]Remaining uncertainty:[/bold] {_get_attr(meta, 'remaining_uncertainty', '')}\n"
            f"[bold]If main assumption fails:[/bold] {_get_attr(meta, 'assumption_failure_impact', '')}\n"
            f"[bold]Non-obvious insight:[/bold] [italic]{_get_attr(meta, 'non_obvious_insight', '')}[/italic]"
        )
        console.print(Panel(meta_text, title="[cyan]Meta-Cognitive Audit[/cyan]", box=box.ROUNDED))

    _render_errors(state)


# ─────────────────────────────────────────────────────────────────────
# SCIENTIFIC RENDERER
# ─────────────────────────────────────────────────────────────────────

def _render_scientific(state: PipelineState) -> None:
    duration = _duration(state)
    console.rule(f"[bold green]SCIENTIFIC INQUIRY  ({duration:.1f}s)[/bold green]")
    render_routing_table(state)

    hypotheses = state.scientific_state.get("hypotheses") or []
    if hypotheses:
        hy_text = Text()
        for h in hypotheses:
            hy_text.append(f"H{h.get('id')}: {h.get('statement')}\n", style="bold white")
            hy_text.append(f"  Logic: {h.get('logic')}\n", style="dim")
            hy_text.append(f"  Falsifiability: {h.get('falsifiability')}\n\n", style="dim yellow")
        console.print(Panel(hy_text, title="[cyan]Phase 2 — Hypotheses[/cyan]", box=box.ROUNDED))

    test_results = state.scientific_state.get("test_results") or []
    if test_results:
        test_text = Text()
        for res in test_results:
            color = "green" if res.get("result") == "SUPPORTED" else "red"
            test_text.append(f"Test H{res.get('hypothesis_id')}: ", style="bold")
            test_text.append(f"{res.get('result')}\n", style=color)
            test_text.append(f"  Experiment: {res.get('experiment')}\n", style="white")
            test_text.append(f"  Reasoning: {res.get('reasoning')}\n\n", style="dim")
        console.print(Panel(test_text, title="[cyan]Phase 3 — Falsification Tests[/cyan]", box=box.ROUNDED))

    _render_stress(state)

    if state.final_solution:
        fs = state.final_solution
        console.print(Panel(_get_attr(fs, 'core_solution', ''), title="[bold green]SCIENTIFIC SYNTHESIS[/bold green]", box=box.DOUBLE, border_style="green"))
        if _get_attr(fs, 'critical_insights', []):
            ins_text = Text()
            for i, insight in enumerate(_get_attr(fs, 'critical_insights', []), 1):
                ins_text.append(f"{i}. {insight}\n\n")
            console.print(Panel(ins_text, title="[yellow]Key Findings[/yellow]", box=box.ROUNDED))
        _render_action_blueprint(state)
        meta = _get_attr(fs, 'meta_audit', {})
        meta_text = (
            f"[bold]Most dangerous assumption:[/bold] {_get_attr(meta, 'most_dangerous_assumption', '')}\n"
            f"[bold]Dominant bias:[/bold] {_get_attr(meta, 'dominant_bias', '')}\n"
            f"[bold]Remaining uncertainty:[/bold] {_get_attr(meta, 'remaining_uncertainty', '')}\n"
            f"[bold]If main assumption fails:[/bold] {_get_attr(meta, 'assumption_failure_impact', '')}\n"
            f"[bold]Non-obvious insight:[/bold] [italic]{_get_attr(meta, 'non_obvious_insight', '')}[/italic]"
        )
        console.print(Panel(meta_text, title="[cyan]Meta-Cognitive Audit[/cyan]", box=box.ROUNDED))
    _render_errors(state)


# ─────────────────────────────────────────────────────────────────────
# SOCRATIC RENDERER
# ─────────────────────────────────────────────────────────────────────

def _render_socratic(state: PipelineState) -> None:
    duration = _duration(state)
    console.rule(f"[bold yellow]SOCRATIC DIALOGUE  ({duration:.1f}s)[/bold yellow]")
    render_routing_table(state)

    questions = state.socratic_state.get("questions") or []
    if questions:
        q_text = Text()
        for q in questions:
            q_text.append(f"{q.get('id')}. {q.get('target_concept')}: ", style="bold cyan")
            q_text.append(f"{q.get('question')}\n\n", style="white")
        console.print(Panel(q_text, title="[cyan]Phase 2 — Maieutic Questions[/cyan]", box=box.ROUNDED))

    answers = state.socratic_state.get("answers") or []
    if answers:
        a_text = Text()
        for a in answers:
            a_text.append(f"Refining {a.get('question_id')}:\n", style="bold")
            a_text.append(f"  Answer: {a.get('answer')}\n", style="white")
            if a.get("contradiction_found"):
                a_text.append(f"  [red]Aporia:[/red] {a.get('contradiction_found')}\n", style="red")
            a_text.append(f"  [green]Insight:[/green] {a.get('insight')}\n\n", style="green")
        console.print(Panel(a_text, title="[cyan]Phase 3 — Dialectic Answers[/cyan]", box=box.ROUNDED))

    if state.final_solution:
        fs = state.final_solution
        console.print(Panel(_get_attr(fs, 'core_solution', ''), title="[bold green]PHILOSOPHICAL SYNTHESIS[/bold green]", box=box.DOUBLE, border_style="green"))
        if _get_attr(fs, 'critical_insights', []):
            ins_text = Text()
            for i, insight in enumerate(_get_attr(fs, 'critical_insights', []), 1):
                ins_text.append(f"{i}. {insight}\n\n")
            console.print(Panel(ins_text, title="[yellow]Aporic Insights[/yellow]", box=box.ROUNDED))
        _render_action_blueprint(state)
    _render_errors(state)


# ─────────────────────────────────────────────────────────────────────
# B1: PRE-MORTEM ANALYSIS RENDERER
# ─────────────────────────────────────────────────────────────────────

def _render_pre_mortem(state: PipelineState) -> None:
    pm = state.pre_mortem_state

    # Failure Narrative
    fn = pm.get("failure_narrative", {})
    if fn:
        content = Text()
        content.append(f"Scenario: ", style="bold red")
        content.append(f"{fn.get('scenario', 'N/A')}\n\n")
        content.append(fn.get("what_happened", ""))
        triggers = fn.get("immediate_triggers", [])
        if triggers:
            content.append("\n\nImmediate Triggers:\n", style="bold")
            for t in triggers:
                content.append(f"• {t}\n")
        console.print(Panel(content, title="[red]Failure Narrative[/red]", box=box.HEAVY))

    # Root Cause
    rc = pm.get("root_cause", {})
    if rc:
        content = Text()
        content.append("Pivot Decision: ", style="bold yellow")
        content.append(f"{rc.get('pivot_decision', '')}\n\n")
        content.append("When: ", style="bold")
        content.append(f"{rc.get('decision_point', '')}\n\n")
        content.append("Why it seemed reasonable: ", style="bold")
        content.append(f"{rc.get('why_it_seemed_reasonable', '')}\n\n")
        cascade = rc.get("cascade", [])
        if cascade:
            content.append("Cascade:\n", style="bold")
            for step in cascade:
                content.append(f"  → {step}\n")
        console.print(Panel(content, title="[yellow]Root Cause Analysis[/yellow]", box=box.ROUNDED))

    # Early Warning Signals table
    signals = pm.get("early_signals", [])
    if signals:
        tbl = Table(title="Early Warning Signals", box=box.SIMPLE_HEAD, show_header=True)
        tbl.add_column("Day", style="cyan", width=6)
        tbl.add_column("Signal", style="white")
        tbl.add_column("How to Detect", style="dim")
        tbl.add_column("Action Threshold", style="yellow")
        for s in signals:
            tbl.add_row(
                str(s.get("day", "?")),
                s.get("signal", ""),
                s.get("how_to_detect", ""),
                s.get("action_threshold", ""),
            )
        console.print(tbl)

    # Hardened Redesign
    hs = pm.get("hardened_solution", "")
    if hs:
        content = Text()
        content.append(hs)
        safeguards = pm.get("safeguards", [])
        if safeguards:
            content.append("\n\nSafeguards:\n", style="bold green")
            for s in safeguards:
                content.append(f"✓ {s}\n", style="green")
        console.print(Panel(content, title="[green]Hardened Redesign[/green]", box=box.ROUNDED))

    _render_errors(state)


# ─────────────────────────────────────────────────────────────────────
# B2: BAYESIAN REASONING RENDERER
# ─────────────────────────────────────────────────────────────────────

def _render_bayesian(state: PipelineState) -> None:
    b = state.bayesian_state

    # Hypotheses with Priors
    hypotheses = b.get("hypotheses_with_priors", [])
    if hypotheses:
        tbl = Table(title="Hypotheses & Prior Probabilities", box=box.SIMPLE_HEAD, show_header=True)
        tbl.add_column("ID", style="cyan", width=5)
        tbl.add_column("Statement", style="white")
        tbl.add_column("P(H)", style="yellow", width=8)
        tbl.add_column("Reasoning", style="dim")
        for h in hypotheses:
            tbl.add_row(
                h.get("id", "?"),
                h.get("statement", ""),
                str(h.get("prior_probability", "")),
                h.get("reasoning", "")[:120],
            )
        console.print(tbl)

    # Posteriors
    posteriors = b.get("posteriors", [])
    most_probable = b.get("most_probable", "")
    if posteriors:
        tbl = Table(title="Posterior Probabilities P(H|E)", box=box.SIMPLE_HEAD, show_header=True)
        tbl.add_column("ID", style="cyan", width=5)
        tbl.add_column("P(H|E)", style="yellow", width=8)
        tbl.add_column("Explanation", style="white")
        for p in posteriors:
            hid = p.get("hypothesis_id", "?")
            is_top = hid == most_probable
            label = f"{hid} ★" if is_top else hid
            tbl.add_row(label, str(p.get("posterior_probability", "")), p.get("explanation", "")[:160])
        console.print(tbl)
        if most_probable:
            console.print(Panel(
                Text(f"Most probable hypothesis: {most_probable}", style="bold green"),
                title="[green]Bayesian Verdict[/green]", box=box.ROUNDED,
            ))

    # Sensitivity Analysis
    sensitivity = b.get("sensitivity_results", [])
    if sensitivity:
        tbl = Table(title="Sensitivity Analysis", box=box.SIMPLE_HEAD, show_header=True)
        tbl.add_column("Assumption", style="white")
        tbl.add_column("Posterior Shift", style="cyan", width=14)
        tbl.add_column("Importance", style="yellow", width=12)
        for s in sensitivity:
            shift = s.get("posterior_shift", "")
            shift_color = "red" if shift == "large" else ("yellow" if shift == "medium" else "green")
            tbl.add_row(
                s.get("assumption", ""),
                f"[{shift_color}]{shift}[/{shift_color}]",
                s.get("importance", ""),
            )
        console.print(tbl)
        most_sensitive = b.get("most_sensitive_assumption", "")
        if most_sensitive:
            console.print(Panel(
                Text(f"Most critical assumption: {most_sensitive}", style="bold yellow"),
                title="[yellow]Sensitivity Finding[/yellow]", box=box.ROUNDED,
            ))

    _render_action_blueprint(state)
    _render_errors(state)


# ─────────────────────────────────────────────────────────────────────
# B3: DIALECTICAL REASONING RENDERER
# ─────────────────────────────────────────────────────────────────────

def _render_dialectical(state: PipelineState) -> None:
    d = state.dialectical_state

    # Thesis (green)
    thesis = d.get("thesis", "")
    commitments = d.get("key_commitments", [])
    if thesis:
        content = Text()
        content.append(thesis)
        if commitments:
            content.append("\n\nKey Commitments:\n", style="bold")
            for c in commitments:
                content.append(f"• {c}\n")
        console.print(Panel(content, title="[green]Thesis — Affirmative Position[/green]", box=box.ROUNDED))

    # Antithesis (red)
    antithesis = d.get("antithesis", "")
    contradictions = d.get("contradictions_exposed", [])
    if antithesis:
        content = Text()
        content.append(antithesis)
        if contradictions:
            content.append("\n\nContradictions Exposed:\n", style="bold red")
            for c in contradictions:
                content.append(f"✗ {c}\n", style="red")
        console.print(Panel(content, title="[red]Antithesis — Negation[/red]", box=box.ROUNDED))

    # Contradiction Analysis table
    irreconcilable = d.get("irreconcilable", [])
    compatible = d.get("compatible", [])
    if irreconcilable or compatible:
        tbl = Table(title="Contradiction Analysis", box=box.SIMPLE_HEAD, show_header=True)
        tbl.add_column("Type", style="cyan", width=18)
        tbl.add_column("Contradiction", style="white")
        for c in irreconcilable:
            tbl.add_row("[red]Irreconcilable[/red]", c)
        for c in compatible:
            tbl.add_row("[yellow]Compatible[/yellow]", c)
        console.print(tbl)

    # Aufhebung (magenta)
    aufhebung = d.get("aufhebung", "")
    if aufhebung:
        content = Text()
        content.append(aufhebung, style="bold")
        preserved_t = d.get("preserved_from_thesis", [])
        preserved_a = d.get("preserved_from_antithesis", [])
        new_insights = d.get("new_insights", [])
        if preserved_t:
            content.append("\n\nPreserved from Thesis:\n", style="bold green")
            for p in preserved_t:
                content.append(f"✓ {p}\n", style="green")
        if preserved_a:
            content.append("\nPreserved from Antithesis:\n", style="bold red")
            for p in preserved_a:
                content.append(f"✓ {p}\n", style="red")
        if new_insights:
            content.append("\nGenuine Novelty:\n", style="bold yellow")
            for i in new_insights:
                content.append(f"★ {i}\n", style="yellow")
        console.print(Panel(content, title="[magenta]Aufhebung — Qualitative Transcendence[/magenta]", box=box.HEAVY))

    _render_action_blueprint(state)
    _render_errors(state)


# ─────────────────────────────────────────────────────────────────────
# B4: ANALOGICAL REASONING RENDERER
# ─────────────────────────────────────────────────────────────────────

def _render_analogical(state: PipelineState) -> None:
    a = state.analogical_state

    # Abstract structure panel
    structure = a.get("abstract_structure", "")
    if structure:
        content = Text()
        content.append(structure)
        constraints = a.get("constraints", [])
        objectives = a.get("objectives", [])
        actors = a.get("actors", [])
        core_dynamics = a.get("core_dynamics", [])
        if constraints:
            content.append("\n\nConstraints:\n", style="bold")
            for c in constraints:
                content.append(f"  • {c}\n")
        if objectives:
            content.append("\nObjectives:\n", style="bold cyan")
            for o in objectives:
                content.append(f"  • {o}\n")
        if actors:
            content.append("\nActors:\n", style="bold yellow")
            for actor in actors:
                content.append(f"  • {actor}\n")
        if core_dynamics:
            content.append("\nCore Dynamics:\n", style="bold magenta")
            for d in core_dynamics:
                content.append(f"  • {d}\n")
        structural_type = a.get("structural_type", "")
        if structural_type:
            content.append(f"\nStructural Type: ", style="bold")
            content.append(structural_type, style="cyan")
        console.print(Panel(content, title="[cyan]Abstract Problem Structure[/cyan]", box=box.ROUNDED))

    # Source domains table
    domains = a.get("source_domains", [])
    if domains:
        tbl = Table(title="Source Domains with Isomorphic Solutions", box=box.SIMPLE_HEAD)
        tbl.add_column("Domain", style="yellow")
        tbl.add_column("Solved Problem", style="white")
        tbl.add_column("Key Mechanism", style="cyan")
        tbl.add_column("Relevance", style="green", width=10)
        for d in domains:
            tbl.add_row(
                d.get("domain", ""),
                (d.get("solved_problem", "") or "")[:80],
                (d.get("key_mechanism", "") or "")[:80],
                d.get("relevance_score", ""),
            )
        console.print(tbl)

    # Analogy mapping table
    mappings = a.get("analogy_mappings", [])
    if mappings:
        tbl = Table(title="Structural Analogy Mappings", box=box.SIMPLE_HEAD)
        tbl.add_column("Source Element", style="yellow")
        tbl.add_column("Target Element", style="cyan")
        tbl.add_column("Mapping Type", style="dim", width=14)
        tbl.add_column("Confidence", style="green", width=10)
        for m in mappings:
            tbl.add_row(
                m.get("source_element", ""),
                m.get("target_element", ""),
                m.get("mapping_type", ""),
                m.get("confidence", ""),
            )
        console.print(tbl)

    # Transfer steps
    transfer_steps = a.get("transfer_steps", [])
    if transfer_steps:
        content = Text()
        content.append("Transfer Steps:\n", style="bold green")
        for i, step in enumerate(transfer_steps, 1):
            content.append(f"  {i}. {step}\n")
        adaptations = a.get("adaptations_required", [])
        if adaptations:
            content.append("\nAdaptations Required:\n", style="bold yellow")
            for adap in adaptations:
                content.append(f"  ⟳ {adap}\n", style="yellow")
        caveats = a.get("caveats", [])
        if caveats:
            content.append("\nCaveats:\n", style="bold dim")
            for cav in caveats:
                content.append(f"  ! {cav}\n", style="dim")
        console.print(Panel(content, title="[green]Transfer Plan[/green]", box=box.ROUNDED))

    # Transferred solution
    transferred = a.get("transferred_solution", "")
    if transferred:
        confidence = a.get("transfer_confidence", "")
        title_suffix = f" [dim](confidence: {confidence})[/dim]" if confidence else ""
        console.print(Panel(
            Text(transferred, style="bold"),
            title=f"[green]Transferred Solution[/green]{title_suffix}",
            box=box.ROUNDED,
        ))

    # Broken analogies
    broken = a.get("broken_analogies", [])
    if broken:
        content = Text()
        content.append("Where the analogy breaks down:\n", style="bold red")
        for b in broken:
            content.append(f"  ✗ {b}\n", style="red")
        unmapped = a.get("unmapped_elements", [])
        if unmapped:
            content.append("\nUnmapped Source Elements:\n", style="bold dim")
            for u in unmapped:
                content.append(f"  ? {u}\n", style="dim")
        console.print(Panel(content, title="[red]Analogy Limitations[/red]", box=box.ROUNDED))

    _render_action_blueprint(state)
    _render_errors(state)


# ─────────────────────────────────────────────────────────────────────
# B5: DELPHI METHOD RENDERER
# ─────────────────────────────────────────────────────────────────────

def _render_delphi(state: PipelineState) -> None:
    d = state.delphi_state

    # Round 1 expert estimates table
    r1 = d.get("round_1_estimates", [])
    if r1:
        tbl = Table(title="Round 1 — Independent Expert Estimates", box=box.SIMPLE_HEAD)
        tbl.add_column("Expert", style="cyan", width=10)
        tbl.add_column("Estimate", style="white")
        tbl.add_column("Confidence", style="yellow", width=10)
        tbl.add_column("Key Assumption", style="dim")
        for e in r1:
            tbl.add_row(
                e.get("expert_id", "?"),
                str(e.get("estimate_label", e.get("estimate_value", "N/A"))),
                e.get("confidence", ""),
                (e.get("key_assumptions", [""])[0] if e.get("key_assumptions") else "")[:80],
            )
        console.print(tbl)

    # Aggregated statistics
    stats = d.get("aggregated_stats", {})
    if stats:
        content = Text()
        median = stats.get("median", stats.get("central_theme", "N/A"))
        iqr = stats.get("iqr", stats.get("spread", "N/A"))
        outlier = stats.get("outlier_expert", "N/A")
        content.append("Median: ", style="bold")
        content.append(f"{median}\n")
        content.append("Spread (IQR): ", style="bold")
        content.append(f"{iqr}\n")
        content.append("Outlier expert: ", style="bold yellow")
        content.append(f"{outlier}\n")
        console.print(Panel(content, title="[yellow]Anonymous Aggregated Statistics[/yellow]", box=box.ROUNDED))

    # Round 2 revisions table
    r2 = d.get("round_2_estimates", [])
    if r2:
        tbl = Table(title="Round 2 — Revised Estimates", box=box.SIMPLE_HEAD)
        tbl.add_column("Expert", style="cyan", width=10)
        tbl.add_column("Revised Estimate", style="white")
        tbl.add_column("Position", style="yellow", width=12)
        tbl.add_column("Rationale", style="dim")
        for e in r2:
            position = e.get("position", "")
            pos_color = "green" if position == "revised" else "red"
            tbl.add_row(
                e.get("expert_id", "?"),
                str(e.get("revised_label", e.get("revised_estimate", "N/A"))),
                f"[{pos_color}]{position}[/{pos_color}]",
                e.get("rationale", "")[:80],
            )
        console.print(tbl)

    # Convergence verdict
    consensus = d.get("consensus", {})
    converged = d.get("converged", False)
    if consensus:
        color = "green" if converged else "yellow"
        label = "CONVERGED" if converged else "NOT CONVERGED"
        content = Text()
        content.append(f"{label}\n", style=f"bold {color}")
        final_val = consensus.get("median", consensus.get("consensus_label", ""))
        if final_val:
            content.append(f"Consensus: {final_val}\n")
        remaining = consensus.get("remaining_disagreement", "")
        if remaining:
            content.append(f"Remaining disagreement: {remaining}\n", style="dim")
        console.print(Panel(content, title=f"[{color}]Convergence Result[/{color}]", box=box.ROUNDED))

    # Minority dissent
    dissent = d.get("dissent", {})
    if dissent:
        minority_report = dissent.get("minority_report", "")
        missing = dissent.get("what_consensus_misses", [])
        content = Text()
        if minority_report:
            content.append(minority_report + "\n\n", style="italic")
        if missing:
            content.append("What the consensus misses:\n", style="bold red")
            for m in missing:
                content.append(f"  x {m}\n", style="red")
        console.print(Panel(content, title="[red]Minority Dissent Report[/red]", box=box.ROUNDED))

    _render_action_blueprint(state)
    _render_errors(state)


# ─────────────────────────────────────────────────────────────────────
# PUBLIC ENTRY POINT
# ─────────────────────────────────────────────────────────────────────

def render_pipeline_result(state: PipelineState) -> None:
    """Dispatch to the appropriate method-specific renderer."""
    method = _method_type(state.preset_name)
    if method == MethodType.DEBATE:
        _render_debate(state)
    elif method == MethodType.ITERATIVE:
        _render_iterative(state)
    elif method == MethodType.RESEARCH:
        _render_research(state)
    elif method == MethodType.JURY:
        _render_jury(state)
    elif method == MethodType.SCIENTIFIC:
        _render_scientific(state)
    elif method == MethodType.SOCRATIC:
        _render_socratic(state)
    elif method == MethodType.PRE_MORTEM:
        _render_pre_mortem(state)
    elif method == MethodType.BAYESIAN:
        _render_bayesian(state)
    elif method == MethodType.DIALECTICAL:
        _render_dialectical(state)
    elif method == MethodType.ANALOGICAL:
        _render_analogical(state)
    elif method == MethodType.DELPHI:
        _render_delphi(state)
    else:
        _render_multi_perspective(state)


# ─────────────────────────────────────────────────────────────────────
# JSON EXPORT
# ─────────────────────────────────────────────────────────────────────

def export_to_json(state: PipelineState, path: str) -> None:
    """Export complete pipeline state to JSON file."""

    def _serialize(obj: Any) -> Any:
        if hasattr(obj, "value"):  # Enum
            return obj.value
        if hasattr(obj, "__dataclass_fields__"):
            return {k: _serialize(v) for k, v in asdict(obj).items()}
        if isinstance(obj, list):
            return [_serialize(i) for i in obj]
        if isinstance(obj, dict):
            return {k: _serialize(v) for k, v in obj.items()}
        if isinstance(obj, datetime):
            return obj.isoformat()
        return obj

    data = {
        "problem":             state.problem,
        "preset_name":         state.preset_name,
        "started_at":          state.started_at.isoformat(),
        "task_type":           state.task_type.value if state.task_type else None,
        "task_type_rationale": state.task_type_rationale,
        "phase_models":        state.phase_models,
        "sub_problems":        _serialize(state.decomposition.sub_problems if state.decomposition else []),
        "assumptions":         _serialize(state.decomposition.assumptions  if state.decomposition else []),
        "candidates":          _serialize(state.candidates),
        "scores":              _serialize(state.scores),
        "stress_results":      _serialize(state.stress_results),
        "final_solution":      _serialize(state.final_solution),
        "errors":              state.errors,
        "phase_logs":          state.phase_logs,
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
