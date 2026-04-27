"""Coding pipeline mixin — production-grade code generation with adversarial review."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from reasoner.models import PipelineState, SolutionCandidate, PerspectiveType
from reasoner.parsing import extract_json

import reasoner.phases as phases
from reasoner.application.mixins._protocol import PipelineMixinProtocol

logger = logging.getLogger(__name__)


class CodingMixin(PipelineMixinProtocol):
    """Mixin providing the 5-phase production code generation pipeline."""

    async def _phase_coding_spec(self, state: PipelineState) -> None:
        """Phase 2: Decompose request into technical specification."""
        self._log("CODING", "Analyzing coding request and producing spec...", state)
        raw, _ = await self._call_llm_cached(
            role="coding_spec",
            system_prompt=phases.CODING_SPEC_SYSTEM,
            user_prompt=phases.coding_spec_prompt(state),
            state=state,
        )
        data = extract_json(raw)
        state.coding_state["spec"] = data
        state.coding_state["language"] = data.get("language", "")
        state.coding_state["framework"] = data.get("framework", "")
        state.coding_state["files_to_generate"] = data.get("files", [])
        logger.debug(
            "CODING spec: %d files planned, lang=%s",
            len(data.get("files", [])),
            data.get("language", "?"),
        )

    async def _phase_coding_generate(self, state: PipelineState) -> None:
        """Phase 3: Generate each file in parallel."""
        self._log("CODING", "Generating production code files in parallel...", state)
        files_to_generate: list[dict[str, Any]] = state.coding_state.get("files_to_generate", [])
        if not files_to_generate:
            state.errors.append("CODING: No files in spec — cannot generate.")
            return

        async def _generate_one(file_spec: dict[str, Any]) -> dict[str, Any]:
            raw, _ = await self._call_llm_cached(
                role="coding_generate",
                system_prompt=phases.CODING_GENERATE_SYSTEM,
                user_prompt=phases.coding_generate_prompt(state, file_spec),
                state=state,
            )
            result = extract_json(raw)
            if not result.get("path"):
                result["path"] = file_spec.get("path", "unknown")
            if not result.get("content"):
                result["content"] = f"# Generation failed for {file_spec.get('path', '?')}"
            return result

        results = await asyncio.gather(*[_generate_one(f) for f in files_to_generate], return_exceptions=True)

        generated: list[dict[str, Any]] = []
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                path = files_to_generate[i].get("path", f"file_{i}")
                logger.warning("CODING generate error for %s: %s", path, res)
                generated.append({"path": path, "content": f"# Error: {res}", "language": "", "key_decisions": []})
            else:
                generated.append(res)

        state.coding_state["generated_files"] = generated
        logger.debug("CODING generated %d files", len(generated))

    async def _phase_coding_review(self, state: PipelineState) -> None:
        """Phase 3.5: Adversarial security and quality review."""
        self._log("CODING", "Running adversarial security and quality review...", state)
        if not state.coding_state.get("generated_files"):
            state.errors.append("CODING: No generated files to review.")
            return

        raw, _ = await self._call_llm_cached(
            role="coding_review",
            system_prompt=phases.CODING_REVIEW_SYSTEM,
            user_prompt=phases.coding_review_prompt(state),
            state=state,
        )
        data = extract_json(raw)
        state.coding_state["review"] = data

        critical_count = len(data.get("critical_issues", []))
        high_count = len(data.get("high_issues", []))
        verdict = data.get("overall_verdict", "UNKNOWN")
        self._log(
            "CODING",
            f"Review complete: {verdict} | {critical_count} critical, {high_count} high issues",
            state,
        )

    async def _phase_coding_tests(self, state: PipelineState) -> None:
        """Phase 4: Generate comprehensive tests."""
        self._log("CODING", "Generating test suite...", state)
        raw, _ = await self._call_llm_cached(
            role="coding_tests",
            system_prompt=phases.CODING_TESTS_SYSTEM,
            user_prompt=phases.coding_tests_prompt(state),
            state=state,
        )
        data = extract_json(raw)
        state.coding_state["tests"] = data
        test_count = len(data.get("test_files", []))
        coverage = data.get("coverage_estimate", "unknown")
        logger.debug("CODING tests: %d test files, coverage=%s", test_count, coverage)

    async def _phase_coding_assemble(self, state: PipelineState) -> None:
        """Phase 5: Apply review fixes and assemble final delivery."""
        self._log("CODING", "Assembling final production-ready output...", state)
        raw, _ = await self._call_llm_cached(
            role="coding_assemble",
            system_prompt=phases.CODING_ASSEMBLE_SYSTEM,
            user_prompt=phases.coding_assemble_prompt(state),
            state=state,
        )
        data = extract_json(raw)
        state.coding_state["final_files"] = data.get("files", [])
        state.coding_state["readme"] = data.get("readme", "")
        state.coding_state["fixes_applied"] = data.get("fixes_applied", [])
        state.coding_state["known_limitations"] = data.get("known_limitations", [])

        # Feed assembled result into candidates so universal synthesis phase sees it
        readme = state.coding_state.get("readme", "")
        files_summary = "\n\n".join(
            f"### {f['path']}\n```\n{f.get('content', '')[:1200]}\n```"
            for f in state.coding_state.get("final_files", [])
        )
        full_output = f"{readme}\n\n{files_summary}".strip()

        state.candidates.append(
            SolutionCandidate(
                perspective=PerspectiveType.CONSTRUCTIVE,
                content=full_output,
                key_insights=data.get("fixes_applied", []),
                model_used=state.phase_models.get("coding_assemble", "unknown"),
            )
        )
        fixes = len(data.get("fixes_applied", []))
        self._log("CODING", f"Assembly complete: {fixes} fixes applied", state)
