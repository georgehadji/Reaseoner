"""Verbalized Sampling brainstorming pipeline mixin.

Implements three phases:
  Phase 2 — VS Idea Generation  (_phase_brainstorm_generate)
  Phase 3 — Cluster & Score     (_phase_brainstorm_cluster)
  Phase 4 — Deep Development    (_phase_brainstorm_develop)

The mixin reads its runtime configuration from
``state.brainstorming_state["config"]`` which is injected by streaming.py
from the preset's ``brainstorming_config`` dict before phase execution.
If no config is present, sensible defaults are used.
"""

from __future__ import annotations

import logging

from reasoner.models import PipelineState
from reasoner.parsing import extract_json
from reasoner.phases.brainstorming import (
    VS_CLUSTER_SYSTEM,
    VS_DEVELOP_SYSTEM,
    VS_GENERATION_SYSTEM,
    vs_cluster_prompt,
    vs_develop_prompt,
    vs_generation_prompt,
)

logger = logging.getLogger(__name__)
_LOG_TAG = "BRAINSTORM"


class BrainstormingMixin:
    """Mixin providing the Verbalized Sampling brainstorming pipeline."""

    # ── Phase 2: VS Idea Generation ───────────────────────────────────────────

    async def _phase_brainstorm_generate(self, state: PipelineState) -> None:
        """VS-Multi idea generation across N rounds.

        Each round extends ``state.brainstorming_state["raw_ideas"]`` with k new
        ideas.  The previous round's ideas are shown to the model (VS-Multi) so
        each round explores genuinely new territory.
        """
        cfg: dict = state.brainstorming_state.setdefault("config", {})
        rounds: int = cfg.get("rounds", 3)
        k: int = cfg.get("k", 5)
        threshold: float = cfg.get("threshold", 0.10)
        n_tail: int = cfg.get("n_tail", 2)
        use_cot: bool = cfg.get("use_cot", False)

        all_ideas: list[dict] = []
        for rnd in range(1, rounds + 1):
            self._log(_LOG_TAG, f"VS round {rnd}/{rounds} (k={k}, threshold={threshold})…", state)
            prompt = vs_generation_prompt(
                state, rnd, k, threshold, n_tail,
                previous_ideas=all_ideas,
                use_cot=use_cot,
            )
            raw, _ = await self._call_llm_cached(
                role="brainstorm_generate",
                system_prompt=VS_GENERATION_SYSTEM.format(threshold=threshold),
                user_prompt=prompt,
                state=state,
            )
            try:
                data = extract_json(raw)
                ideas: list[dict] = data.get("ideas", [])
                all_ideas.extend(ideas)
                self._log(_LOG_TAG, f"Round {rnd}: +{len(ideas)} ideas (total {len(all_ideas)})", state)
            except Exception as exc:
                self._log(_LOG_TAG, f"Round {rnd} parse error: {exc}", state)
                state.errors.append(f"VS round {rnd}: {exc}")

        state.brainstorming_state["raw_ideas"] = all_ideas
        state.brainstorming_state["raw_idea_count"] = len(all_ideas)

    # ── Phase 3: Cluster & Score ──────────────────────────────────────────────

    async def _phase_brainstorm_cluster(self, state: PipelineState) -> None:
        """Deduplicate, theme-cluster, and score the raw idea pool."""
        raw_ideas: list[dict] = state.brainstorming_state.get("raw_ideas", [])
        if not raw_ideas:
            self._log(_LOG_TAG, "No raw ideas to cluster — skipping.", state)
            state.errors.append("Brainstorming: VS generation produced no raw ideas; clustering skipped.")
            return

        self._log(_LOG_TAG, f"Clustering {len(raw_ideas)} raw ideas…", state)
        raw, _ = await self._call_llm_cached(
            role="brainstorm_cluster",
            system_prompt=VS_CLUSTER_SYSTEM,
            user_prompt=vs_cluster_prompt(state, raw_ideas),
            state=state,
        )
        try:
            data = extract_json(raw)
            clusters: list[dict] = data.get("clusters", [])
            state.brainstorming_state["clusters"] = clusters
            state.brainstorming_state["deduplicated_count"] = data.get("deduplicated_count", 0)
            # Collect ideas marked keep=True (default True if key absent)
            top_ideas: list[dict] = [
                idea
                for cluster in clusters
                for idea in cluster.get("ideas", [])
                if idea.get("keep", True)
            ]
            state.brainstorming_state["top_ideas"] = top_ideas
            self._log(
                _LOG_TAG,
                f"Clustered into {len(clusters)} themes; {len(top_ideas)} ideas kept.",
                state,
            )
        except Exception as exc:
            self._log(_LOG_TAG, f"Cluster parse error: {exc}", state)
            state.errors.append(f"VS cluster: {exc}")

    # ── Phase 4: Deep Development ─────────────────────────────────────────────

    async def _phase_brainstorm_develop(self, state: PipelineState) -> None:
        """Deeply develop the top N ideas from the clustering phase."""
        top_ideas: list[dict] = state.brainstorming_state.get("top_ideas", [])
        max_develop: int = state.brainstorming_state.get("config", {}).get("max_develop", 3)
        ideas_to_develop = top_ideas[:max_develop]

        if not ideas_to_develop:
            self._log(_LOG_TAG, "No top ideas to develop — skipping.", state)
            state.errors.append("Brainstorming: no ideas survived clustering; development skipped.")
            return

        self._log(_LOG_TAG, f"Developing top {len(ideas_to_develop)} ideas…", state)
        raw, _ = await self._call_llm_cached(
            role="brainstorm_develop",
            system_prompt=VS_DEVELOP_SYSTEM,
            user_prompt=vs_develop_prompt(state, ideas_to_develop),
            state=state,
        )
        try:
            data = extract_json(raw)
            developments: list[dict] = data.get("developments", [])
            state.brainstorming_state["developments"] = developments
            self._log(_LOG_TAG, f"Developed {len(developments)} ideas.", state)
        except Exception as exc:
            self._log(_LOG_TAG, f"Develop parse error: {exc}", state)
            state.errors.append(f"VS develop: {exc}")
