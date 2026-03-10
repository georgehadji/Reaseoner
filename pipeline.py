"""
ARA Pipeline - Main Orchestrator Controller
Adaptive Reasoning Architecture v2.0

Each phase = separate inference step with explicit state management.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Any

from models import (
    Assumption,
    ClaimLabel,
    CritiqueScore,
    Decomposition,
    FinalSolution,
    MetaCognitiveAudit,
    PerspectiveType,
    PipelineState,
    ScenarioType,
    SolutionCandidate,
    StressTestResult,
    SubProblem,
    TaskType,
)
from parsing import ParseError, extract_json, extract_solution_prose, safe_float, safe_list
import phases
from phases import (
    CLASSIFICATION_SYSTEM,
    CRITIQUE_SYSTEM,
    DECOMPOSITION_SYSTEM,
    STRESS_SYSTEM,
    SYNTHESIS_SYSTEM,
    classification_prompt,
    critique_prompt,
    decomposition_prompt,
    perspective_prompt,
    stress_test_prompt,
    synthesis_prompt,
)
from llm import ProviderRouter
from core import PhaseConfig, make_phase_result, DEFAULT_PERSPECTIVES

logger = logging.getLogger(__name__)


class ARAPipeline:
    """
    Orchestrated ARA v2.0 Pipeline.

    Architecture:
    ┌─────────────────────────────────────────────┐
    │  Phase 0: Task Classification               │
    │  Phase 1: Problem Decomposition             │
    │  Phase 2: Multi-Perspective Analysis (async)│
    │  Phase 3: Critique & Pruning                │
    │  Phase 4: Stress Testing                    │
    │  Phase 5: Synthesis                         │
    └─────────────────────────────────────────────┘

    Each phase is a separate LLM inference call.
    State is persisted between phases.
    """

    # Default per-phase LLM params — can be overridden via PhaseConfig.with_overrides()
    _PHASE_CONFIGS: dict[str, PhaseConfig] = {
        "classification": PhaseConfig(max_tokens=512,  temperature=1.0, role="classification"),
        "decomposition":  PhaseConfig(max_tokens=1500, temperature=1.0, role="decomposition"),
        "perspective":    PhaseConfig(max_tokens=1200, temperature=1.0, role="primary"),  # role overridden per perspective
        "scoring":        PhaseConfig(max_tokens=2000, temperature=1.0, role="scoring"),
        "stress_testing": PhaseConfig(max_tokens=1500, temperature=1.0, role="stress_testing"),
        "synthesis":      PhaseConfig(max_tokens=8192, temperature=1.0, role="synthesis"),
    }

    def __init__(
        self,
        router: ProviderRouter,
        top_k: int = 2,
        parallel_perspectives: bool = True,
        verbose: bool = True,
        phase_config_overrides: dict[str, PhaseConfig] | None = None,
        preset_name: str | None = None,
    ) -> None:
        self.router = router
        self.top_k = top_k
        self.parallel_perspectives = parallel_perspectives
        self.verbose = verbose
        self.preset_name = preset_name
        # Merge class-level defaults with any preset-provided overrides
        self.phase_configs: dict[str, PhaseConfig] = {
            **self._PHASE_CONFIGS,
            **(phase_config_overrides or {}),
        }
        # Data-driven perspectives — can be replaced to add/remove perspectives
        self.perspectives = list(DEFAULT_PERSPECTIVES)

    def _log(self, phase: str, message: str, state: PipelineState) -> None:
        state.log(phase, message)
        if self.verbose:
            logger.info("[%s] %s", phase, message)

    # ─────────────────────────────────────────────
    # PHASE 0 — TASK CLASSIFICATION
    # ─────────────────────────────────────────────

    async def phase_0_classify(self, state: PipelineState) -> None:
        self._log("PHASE-0", "Classifying task...", state)
        cfg = self.phase_configs["classification"]
        t0 = time.monotonic()
        raw, tokens = "", {"input": 0, "output": 0}
        phase_errors: list[str] = []

        try:
            raw, tokens = await self.router.call(
                role=cfg.role,
                system_prompt=CLASSIFICATION_SYSTEM,
                user_prompt=classification_prompt(state.problem),
                max_tokens=cfg.max_tokens,
                temperature=cfg.temperature,
                timeout_seconds=cfg.timeout_seconds,
            )
            state.phase_tokens["Phase 0: Classification"] = tokens
            data = extract_json(raw)
            state.task_type = TaskType(data.get("task_type", "hybrid"))
            state.task_type_rationale = str(data.get("rationale", ""))
            state.language = str(data.get("language", "English"))
            self._log("PHASE-0", f"Task type: {state.task_type.value}, Language: {state.language}", state)
        except (ParseError, ValueError, KeyError) as exc:
            msg = f"Phase 0 classification parse error: {exc} (model: {self.router.get('classification').model if hasattr(self.router.get('classification'), 'model') else 'unknown'})"
            state.errors.append(msg)
            phase_errors.append(msg)
            state.task_type = TaskType.HYBRID
            state.task_type_rationale = "Fallback: classification failed"
            self._log("PHASE-0", f"Parse error — defaulting to HYBRID: {exc}", state)
        finally:
            state.phase_results.append(make_phase_result(
                phase_name="classification",
                output=state.task_type,
                tokens=tokens,
                model_used=self.router.get(cfg.role).model,
                start_time=t0,
                errors=phase_errors,
                raw_response=raw,
            ))

    # ─────────────────────────────────────────────
    # PHASE 1 — DECOMPOSITION
    # ─────────────────────────────────────────────

    async def phase_1_decompose(self, state: PipelineState) -> None:
        self._log("PHASE-1", "Decomposing problem...", state)
        cfg = self.phase_configs["decomposition"]
        t0 = time.monotonic()
        raw, tokens = "", {"input": 0, "output": 0}
        phase_errors: list[str] = []

        try:
            raw, tokens = await self.router.call(
                role=cfg.role,
                system_prompt=DECOMPOSITION_SYSTEM,
                user_prompt=decomposition_prompt(state),
                max_tokens=cfg.max_tokens,
                temperature=cfg.temperature,
                timeout_seconds=cfg.timeout_seconds,
            )
            state.phase_tokens["Phase 1: Decomposition"] = tokens
            data = extract_json(raw)

            sub_problems = [
                SubProblem(
                    id=sp.get("id", f"SP{i+1}"),
                    description=str(sp.get("description", "")),
                    inputs=safe_list(sp.get("inputs", [])),
                    outputs=safe_list(sp.get("outputs", [])),
                    constraints=safe_list(sp.get("constraints", [])),
                )
                for i, sp in enumerate(data.get("sub_problems", [])[:5])
            ]

            assumptions = [
                Assumption(
                    text=str(a.get("text", "")),
                    label=ClaimLabel(a.get("label", "UNKNOWN")),
                    rationale=str(a.get("rationale", "")),
                )
                for a in data.get("assumptions", [])
            ]

            state.decomposition = Decomposition(
                sub_problems=sub_problems,
                assumptions=assumptions,
                failure_modes=safe_list(data.get("failure_modes", [])),
                raw_response=raw,
            )

            self._log(
                "PHASE-1",
                f"{len(sub_problems)} sub-problems, {len(assumptions)} assumptions",
                state,
            )
        except (ParseError, ValueError, KeyError) as exc:
            msg = f"Phase 1 decomposition parse error: {exc} (model: {self.router.get('decomposition').model if hasattr(self.router.get('decomposition'), 'model') else 'unknown'})"
            state.errors.append(msg)
            phase_errors.append(msg)
            state.decomposition = Decomposition(
                sub_problems=[
                    SubProblem(
                        id="SP1",
                        description=state.problem,
                        inputs=["problem statement"],
                        outputs=["solution"],
                        constraints=["unknown"],
                    )
                ],
                assumptions=[
                    Assumption(
                        text="Problem is well-defined",
                        label=ClaimLabel.UNKNOWN,
                        rationale="Fallback assumption",
                    )
                ],
                failure_modes=["Decomposition failed — working with full problem"],
                raw_response=raw,
            )
            self._log("PHASE-1", f"Parse error — using fallback decomposition: {exc}", state)
        finally:
            state.phase_results.append(make_phase_result(
                phase_name="decomposition",
                output=state.decomposition,
                tokens=tokens,
                model_used=self.router.get(cfg.role).model,
                start_time=t0,
                errors=phase_errors,
                raw_response=raw,
            ))

    # ─────────────────────────────────────────────
    # PHASE 2 — MULTI-PERSPECTIVE ANALYSIS
    # ─────────────────────────────────────────────

    async def _single_perspective(
        self, state: PipelineState, perspective: "Any"
    ) -> SolutionCandidate:
        """
        Run one perspective as an independent LLM call.
        Accepts either PerspectiveDefinition (new) or PerspectiveType (legacy).
        """
        from core.perspectives import PerspectiveDefinition

        if isinstance(perspective, PerspectiveDefinition):
            routing_key = perspective.routing_key
            system_prompt = perspective.system_prompt
            perspective_enum = PerspectiveType(perspective.name)
        else:
            # Legacy PerspectiveType path (used by api.py or external callers)
            from phases import PERSPECTIVE_SYSTEMS
            routing_key = perspective.value
            system_prompt = PERSPECTIVE_SYSTEMS[perspective]
            perspective_enum = perspective

        cfg = self.phase_configs["perspective"].with_overrides(role=routing_key)
        try:
            model_for_perspective = self.router.get(routing_key).model
        except Exception:
            model_for_perspective = "unknown"

        raw, tokens = await self.router.call(
            role=routing_key,
            system_prompt=system_prompt,
            user_prompt=perspective_prompt(state, perspective_enum),
            max_tokens=cfg.max_tokens,
            temperature=cfg.temperature,
            timeout_seconds=cfg.timeout_seconds,
        )
        phase_key = f"Phase 2: {routing_key.capitalize()}"
        if phase_key not in state.phase_tokens:
            state.phase_tokens[phase_key] = {"input": 0, "output": 0}
        state.phase_tokens[phase_key]["input"] += tokens["input"]
        state.phase_tokens[phase_key]["output"] += tokens["output"]

        try:
            data = extract_json(raw)
            return SolutionCandidate(
                perspective=perspective_enum,
                content=str(data.get("core_analysis", raw[:800])),
                key_insights=safe_list(data.get("key_insights", [])),
                model_used=model_for_perspective,
            )
        except ParseError:
            return SolutionCandidate(
                perspective=perspective_enum,
                content=raw[:800],
                key_insights=[],
                model_used=model_for_perspective,
            )

    async def phase_2_analyze(self, state: PipelineState) -> None:
        self._log("PHASE-2", "Running multi-perspective analysis...", state)
        t0 = time.monotonic()
        phase_errors: list[str] = []

        if self.parallel_perspectives:
            tasks = [self._single_perspective(state, p) for p in self.perspectives]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, r in enumerate(results):
                if isinstance(r, Exception):
                    p = self.perspectives[i]
                    name = p.name if hasattr(p, "name") else p.value
                    try:
                        model_used = self.router.get(name).model
                        msg = f"Perspective {name} failed on model {model_used}: {r}"
                    except Exception:
                        msg = f"Perspective {name} failed: {r}"
                    state.errors.append(msg)
                    phase_errors.append(msg)
                else:
                    state.candidates.append(r)
        else:
            for p in self.perspectives:
                name = p.name if hasattr(p, "name") else p.value
                try:
                    candidate = await self._single_perspective(state, p)
                    state.candidates.append(candidate)
                except Exception as exc:
                    try:
                        model_used = self.router.get(name).model
                        msg = f"Perspective {name} failed on model {model_used}: {exc}"
                    except Exception:
                        msg = f"Perspective {name} failed: {exc}"
                    state.errors.append(msg)
                    phase_errors.append(msg)

        self._log("PHASE-2", f"{len(state.candidates)} candidates generated", state)
        p2_tokens = {k: v for k, v in state.phase_tokens.items() if k.startswith("Phase 2:")}
        state.phase_results.append(make_phase_result(
            phase_name="analysis",
            output=state.candidates,
            tokens={
                "input": sum(v["input"] for v in p2_tokens.values()),
                "output": sum(v["output"] for v in p2_tokens.values()),
            },
            model_used="multiple",
            start_time=t0,
            errors=phase_errors,
        ))

    # ─────────────────────────────────────────────
    # PHASE 3 — CRITIQUE & PRUNING
    # ─────────────────────────────────────────────

    async def phase_3_critique(self, state: PipelineState) -> None:
        self._log("PHASE-3", "Critiquing and scoring candidates...", state)
        cfg = self.phase_configs["scoring"]
        t0 = time.monotonic()
        raw, tokens = "", {"input": 0, "output": 0}
        phase_errors: list[str] = []

        try:
            raw, tokens = await self.router.call(
                role=cfg.role,
                system_prompt=CRITIQUE_SYSTEM,
                user_prompt=critique_prompt(state),
                max_tokens=cfg.max_tokens,
                temperature=cfg.temperature,
                timeout_seconds=cfg.timeout_seconds,
            )
            state.phase_tokens["Phase 3: Critique & Pruning"] = tokens
            data = extract_json(raw)
            scores_data = data.get("scores", [])

            for s in scores_data:
                try:
                    state.scores.append(
                        CritiqueScore(
                            perspective=PerspectiveType(s.get("perspective", "constructive")),
                            logical_consistency=safe_float(s.get("logical_consistency", 5)),
                            evidence_support=safe_float(s.get("evidence_support", 5)),
                            failure_resilience=safe_float(s.get("failure_resilience", 5)),
                            feasibility=safe_float(s.get("feasibility", 5)),
                            bias_flags=safe_list(s.get("bias_flags", [])),
                            steel_man=str(s.get("steel_man", "")),
                        )
                    )
                except (ValueError, KeyError) as exc:
                    state.errors.append(f"Score parse error for entry: {exc}")

            scored_perspectives = {s.perspective: s.total for s in state.scores}
            top_perspectives = sorted(
                scored_perspectives, key=scored_perspectives.get, reverse=True  # type: ignore[arg-type]
            )[: self.top_k]

            state.top_candidates = [
                c for c in state.candidates if c.perspective in top_perspectives
            ]

            self._log(
                "PHASE-3",
                f"Top {self.top_k} candidates: {[p.value for p in top_perspectives]}",
                state,
            )
        except (ParseError, ValueError) as exc:
            msg = f"Phase 3 scoring parse error: {exc} (model: {self.router.get('scoring').model if hasattr(self.router.get('scoring'), 'model') else 'unknown'})"
            state.errors.append(msg)
            phase_errors.append(msg)
            state.top_candidates = state.candidates[: self.top_k]
            self._log("PHASE-3", f"Parse error — keeping first {self.top_k}: {exc}", state)
        finally:
            state.phase_results.append(make_phase_result(
                phase_name="scoring",
                output=state.scores,
                tokens=tokens,
                model_used=self.router.get(cfg.role).model,
                start_time=t0,
                errors=phase_errors,
                raw_response=raw,
            ))

    # ─────────────────────────────────────────────
    # PHASE 4 — STRESS TESTING
    # ─────────────────────────────────────────────

    async def phase_4_stress_test(self, state: PipelineState) -> None:
        self._log("PHASE-4", "Running stress tests...", state)
        cfg = self.phase_configs["stress_testing"]
        t0 = time.monotonic()
        raw, tokens = "", {"input": 0, "output": 0}
        phase_errors: list[str] = []

        try:
            raw, tokens = await self.router.call(
                role=cfg.role,
                system_prompt=STRESS_SYSTEM,
                user_prompt=stress_test_prompt(state),
                max_tokens=cfg.max_tokens,
                temperature=cfg.temperature,
                timeout_seconds=cfg.timeout_seconds,
            )
            state.phase_tokens["Phase 4: Stress Testing"] = tokens
            data = extract_json(raw)
            for test in data.get("stress_tests", []):
                try:
                    state.stress_results.append(
                        StressTestResult(
                            scenario=ScenarioType(test.get("scenario", "optimal")),
                            survival_rate=safe_float(
                                test.get("survival_rate", 0.5), min_val=0.0, max_val=1.0
                            ),
                            failure_mode=str(test.get("failure_mode", "Unknown")),
                            recovery_path=str(test.get("recovery_path", "None specified")),
                        )
                    )
                except (ValueError, KeyError) as exc:
                    state.errors.append(f"Stress test parse error: {exc}")

            self._log("PHASE-4", f"{len(state.stress_results)} scenarios tested", state)
        except (ParseError, ValueError) as exc:
            msg = f"Phase 4 stress test parse error: {exc} (model: {self.router.get('stress_testing').model if hasattr(self.router.get('stress_testing'), 'model') else 'unknown'})"
            state.errors.append(msg)
            phase_errors.append(msg)
            self._log("PHASE-4", f"Stress test parsing failed: {exc}", state)
        finally:
            state.phase_results.append(make_phase_result(
                phase_name="stress_testing",
                output=state.stress_results,
                tokens=tokens,
                model_used=self.router.get(cfg.role).model,
                start_time=t0,
                errors=phase_errors,
                raw_response=raw,
            ))

    # ─────────────────────────────────────────────
    # PHASE 5 — SYNTHESIS
    # ─────────────────────────────────────────────

    async def phase_5_synthesize(self, state: PipelineState) -> None:
        self._log("PHASE-5", "Synthesizing final solution...", state)
        cfg = self.phase_configs["synthesis"]
        t0 = time.monotonic()
        raw, tokens = "", {"input": 0, "output": 0}
        phase_errors: list[str] = []

        try:
            raw, tokens = await self.router.call(
                role=cfg.role,
                system_prompt=SYNTHESIS_SYSTEM,
                user_prompt=synthesis_prompt(state, state.preset_name),
                max_tokens=cfg.max_tokens,
                temperature=cfg.temperature,
                timeout_seconds=cfg.timeout_seconds,
            )
            state.phase_tokens["Phase 5: Synthesis"] = tokens

            # Try hybrid format: [SOLUTION]...prose...[/SOLUTION] + JSON metadata block
            prose = extract_solution_prose(raw)
            if prose is not None:
                core_solution = prose
                try:
                    data = extract_json(raw)
                except ParseError:
                    data = {}
            else:
                # Fallback: old all-JSON format
                data = extract_json(raw)
                core_solution = str(data.get("core_solution", raw[:2000]))

            meta_data = data.get("meta_audit", {})
            meta_audit = MetaCognitiveAudit(
                most_dangerous_assumption=str(meta_data.get("most_dangerous_assumption", "Unknown")),
                dominant_bias=str(meta_data.get("dominant_bias", "Unknown")),
                remaining_uncertainty=str(meta_data.get("remaining_uncertainty", "Unknown")),
                assumption_failure_impact=str(meta_data.get("assumption_failure_impact", "Unknown")),
                non_obvious_insight=str(meta_data.get("non_obvious_insight", "Unknown")),
            )

            raw_labels = data.get("claim_labels", {})
            claim_labels: dict[str, ClaimLabel] = {}
            for claim, label_str in raw_labels.items():
                try:
                    claim_labels[claim] = ClaimLabel(label_str)
                except ValueError:
                    claim_labels[claim] = ClaimLabel.UNKNOWN

            state.final_solution = FinalSolution(
                core_solution=core_solution,
                critical_insights=safe_list(data.get("critical_insights", []))[:5],
                action_blueprint=data.get("action_blueprint", []),
                open_questions=safe_list(data.get("open_questions", [])),
                claim_labels=claim_labels,
                meta_audit=meta_audit,
            )
            self._log("PHASE-5", "Synthesis complete", state)

        except (ParseError, ValueError, KeyError) as exc:
            msg = f"Phase 5 synthesis parse error: {exc} (model: {self.router.get('synthesis').model if hasattr(self.router.get('synthesis'), 'model') else 'unknown'})"
            state.errors.append(msg)
            phase_errors.append(msg)
            state.final_solution = FinalSolution(
                core_solution=raw,
                critical_insights=[],
                action_blueprint=[],
                open_questions=["Synthesis parsing failed"],
                claim_labels={},
                meta_audit=MetaCognitiveAudit(
                    most_dangerous_assumption="Parse failure",
                    dominant_bias="Unknown",
                    remaining_uncertainty="Full solution uncertain",
                    assumption_failure_impact="Unknown",
                    non_obvious_insight="None extracted",
                ),
            )
            self._log("PHASE-5", f"Synthesis parse error: {exc}", state)
        finally:
            state.phase_results.append(make_phase_result(
                phase_name="synthesis",
                output=state.final_solution,
                tokens=tokens,
                model_used=self.router.get(cfg.role).model,
                start_time=t0,
                errors=phase_errors,
                raw_response=raw,
            ))

    # ─────────────────────────────────────────────
    # MAIN ORCHESTRATOR
    # ─────────────────────────────────────────────

    async def run(self, problem: str) -> PipelineState:
        """
        Execute the full ARA pipeline.
        Returns complete PipelineState with all intermediate results.
        """
        state = PipelineState(problem=problem, preset_name=self.preset_name)

        phases = [
            ("Phase 0: Classification", self.phase_0_classify),
            ("Phase 1: Decomposition", self.phase_1_decompose),
            ("Phase 2: Multi-Perspective Analysis", self.phase_2_analyze),
            ("Phase 3: Critique & Pruning", self.phase_3_critique),
            ("Phase 4: Stress Testing", self.phase_4_stress_test),
            ("Phase 5: Synthesis", self.phase_5_synthesize),
        ]

        for phase_name, phase_fn in phases:
            try:
                await phase_fn(state)
            except Exception as exc:
                error_msg = f"{phase_name} failed with unhandled error: {exc}"
                state.errors.append(error_msg)
                logger.exception(error_msg)
                # Pipeline continues — each phase has fallbacks

        return state
