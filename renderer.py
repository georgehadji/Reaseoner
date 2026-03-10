"""
ARA Pipeline - Output Renderer
Rich terminal display and JSON export, with method-specific layouts.

Methods:
  STANDARD    — structured analysis (default for all non-specialized presets)
  DEBATE      — adversarial competition: Proposition vs Opposition → Verdict
  EVOLUTIONARY — population generation → fitness selection → optimized solution
  RESEARCH    — evidence report: quality matrix, claim verification, evidence gaps
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
# METHOD DETECTION
# ─────────────────────────────────────────────────────────────────────

class MethodType(Enum):
    STANDARD     = "standard"
    DEBATE       = "debate"
    EVOLUTIONARY = "evolutionary"
    RESEARCH     = "research"


_DEBATE_PRESETS       = {"debate", "debate-budget"}
_EVOLUTIONARY_PRESETS = {"evolutionary", "evolutionary-budget"}
_RESEARCH_PRESETS     = {"research"}


def _method_type(preset_name: str | None) -> MethodType:
    if preset_name in _DEBATE_PRESETS:       return MethodType.DEBATE
    if preset_name in _EVOLUTIONARY_PRESETS: return MethodType.EVOLUTIONARY
    if preset_name in _RESEARCH_PRESETS:     return MethodType.RESEARCH
    return MethodType.STANDARD


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
    if not fs or not fs.action_blueprint:
        return
    table = Table(title=title, box=box.SIMPLE_HEAVY)
    table.add_column("#", width=3)
    table.add_column("Action")
    table.add_column("Horizon", width=12)
    table.add_column("Go Criteria")
    table.add_column("Fallback")
    for step in fs.action_blueprint:
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
# STANDARD RENDERER (original behaviour)
# ─────────────────────────────────────────────────────────────────────

def _render_standard(state: PipelineState) -> None:
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
            fs.core_solution,
            title="[bold green]CORE SOLUTION[/bold green]",
            box=box.DOUBLE,
            border_style="green",
        ))

        insights_text = Text()
        for i, insight in enumerate(fs.critical_insights, 1):
            insights_text.append(f"{i}. {insight}\n\n")
        console.print(Panel(insights_text, title="[yellow]Critical Insights[/yellow]", box=box.ROUNDED))

        _render_action_blueprint(state)

        if fs.open_questions:
            oq_text = "\n".join(f"• {q}" for q in fs.open_questions)
            console.print(Panel(oq_text, title="[red]Open Questions (Unresolved)[/red]", box=box.ROUNDED))

        meta = fs.meta_audit
        meta_text = (
            f"[bold]Most dangerous assumption:[/bold] {meta.most_dangerous_assumption}\n"
            f"[bold]Dominant bias:[/bold] {meta.dominant_bias}\n"
            f"[bold]Remaining uncertainty:[/bold] {meta.remaining_uncertainty}\n"
            f"[bold]If main assumption fails:[/bold] {meta.assumption_failure_impact}\n"
            f"[bold]Non-obvious insight:[/bold] [italic]{meta.non_obvious_insight}[/italic]"
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
            fs.core_solution,
            title="[bold green]VERDICT[/bold green]",
            box=box.DOUBLE,
            border_style="green",
        ))

        if fs.critical_insights:
            ins_text = Text()
            for i, insight in enumerate(fs.critical_insights, 1):
                ins_text.append(f"{i}. {insight}\n\n")
            console.print(Panel(ins_text, title="[yellow]Key Findings[/yellow]", box=box.ROUNDED))

        _render_action_blueprint(state, title="Implementation Ruling")

        if fs.open_questions:
            oq_text = "\n".join(f"• {q}" for q in fs.open_questions)
            console.print(Panel(oq_text, title="[red]Unresolved Points[/red]", box=box.ROUNDED))

        meta = fs.meta_audit
        meta_text = (
            f"[bold]Most dangerous assumption:[/bold] {meta.most_dangerous_assumption}\n"
            f"[bold]Dominant bias in judgment:[/bold] {meta.dominant_bias}\n"
            f"[bold]Remaining uncertainty:[/bold] {meta.remaining_uncertainty}\n"
            f"[bold]If main assumption fails:[/bold] {meta.assumption_failure_impact}\n"
            f"[bold]Non-obvious insight:[/bold] [italic]{meta.non_obvious_insight}[/italic]"
        )
        console.print(Panel(meta_text, title="[cyan]Judge's Reservations[/cyan]", box=box.ROUNDED))

    _render_errors(state)


# ─────────────────────────────────────────────────────────────────────
# EVOLUTIONARY RENDERER
# ─────────────────────────────────────────────────────────────────────

def _render_evolutionary(state: PipelineState) -> None:
    duration = _duration(state)
    console.rule(f"[bold yellow]EVOLUTIONARY OPTIMIZATION  ({duration:.1f}s)[/bold yellow]")

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
            fs.core_solution,
            title="[bold green]OPTIMIZED SOLUTION[/bold green]",
            box=box.DOUBLE,
            border_style="green",
        ))

        if fs.critical_insights:
            em_text = Text()
            for i, insight in enumerate(fs.critical_insights, 1):
                em_text.append(f"{i}. {insight}\n\n")
            console.print(Panel(em_text, title="[yellow]Emergent Properties[/yellow]", box=box.ROUNDED))

        _render_action_blueprint(state, title="Survival Strategy")

        if fs.open_questions:
            oq_text = "\n".join(f"• {q}" for q in fs.open_questions)
            console.print(Panel(oq_text, title="[red]Open Hypotheses[/red]", box=box.ROUNDED))

        meta = fs.meta_audit
        meta_text = (
            f"[bold]Critical vulnerability:[/bold] {meta.most_dangerous_assumption}\n"
            f"[bold]Evolutionary pressure detected:[/bold] {meta.dominant_bias}\n"
            f"[bold]Remaining uncertainty:[/bold] {meta.remaining_uncertainty}\n"
            f"[bold]If vulnerability exploited:[/bold] {meta.assumption_failure_impact}\n"
            f"[bold]Emergent insight:[/bold] [italic]{meta.non_obvious_insight}[/italic]"
        )
        console.print(Panel(meta_text, title="[cyan]Evolutionary Forces[/cyan]", box=box.ROUNDED))

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
            fs.core_solution,
            title="[bold green]EVIDENCE-GROUNDED SYNTHESIS[/bold green]",
            box=box.DOUBLE,
            border_style="green",
        ))

        if fs.claim_labels:
            claim_table = Table(title="Claim Verification Status", box=box.SIMPLE_HEAVY)
            claim_table.add_column("Status", width=14)
            claim_table.add_column("Claim")
            for claim, label in fs.claim_labels.items():
                color = _label_color(label)
                claim_table.add_row(f"[{color}]{label.value}[/{color}]", claim)
            console.print(claim_table)

        if fs.open_questions:
            oq_text = "\n".join(f"• {q}" for q in fs.open_questions)
            console.print(Panel(oq_text, title="[red]Evidence Gaps (Unverified / Missing Data)[/red]", box=box.ROUNDED))

        if fs.critical_insights:
            ins_text = Text()
            for i, insight in enumerate(fs.critical_insights, 1):
                ins_text.append(f"{i}. {insight}\n\n")
            console.print(Panel(ins_text, title="[yellow]Key Findings[/yellow]", box=box.ROUNDED))

        _render_action_blueprint(state, title="Recommended Actions")

        meta = fs.meta_audit
        meta_text = (
            f"[bold]Critical evidence gap:[/bold] {meta.most_dangerous_assumption}\n"
            f"[bold]Potential researcher bias:[/bold] {meta.dominant_bias}\n"
            f"[bold]Remaining uncertainty:[/bold] {meta.remaining_uncertainty}\n"
            f"[bold]Impact if gap unresolved:[/bold] {meta.assumption_failure_impact}\n"
            f"[bold]Non-obvious finding:[/bold] [italic]{meta.non_obvious_insight}[/italic]"
        )
        console.print(Panel(meta_text, title="[cyan]Epistemic Caveats[/cyan]", box=box.ROUNDED))

    _render_errors(state)


# ─────────────────────────────────────────────────────────────────────
# PUBLIC ENTRY POINT
# ─────────────────────────────────────────────────────────────────────

def render_pipeline_result(state: PipelineState) -> None:
    """Dispatch to the appropriate method-specific renderer."""
    method = _method_type(state.preset_name)
    if method == MethodType.DEBATE:
        _render_debate(state)
    elif method == MethodType.EVOLUTIONARY:
        _render_evolutionary(state)
    elif method == MethodType.RESEARCH:
        _render_research(state)
    else:
        _render_standard(state)


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
