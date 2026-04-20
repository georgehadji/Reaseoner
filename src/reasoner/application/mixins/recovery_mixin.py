"""Recovery path mixin for ARAPipeline."""

from __future__ import annotations

import logging
from dataclasses import asdict

from reasoner.core.constants import TRUNCATION
from reasoner.models import PipelineState, SolutionCandidate, GenerationCandidate
from reasoner.parsing import ParseError, extract_json

import reasoner.phases as phases
from reasoner.application.mixins._protocol import PipelineMixinProtocol

logger = logging.getLogger(__name__)


class RecoveryMixin(PipelineMixinProtocol):
    """Mixin providing recovery path execution."""

    async def _run_recovery_path(self, state: PipelineState, candidate_to_verify: SolutionCandidate | GenerationCandidate) -> None:
        """Executes a cross-verification path for a potentially problematic candidate."""
        self._log("RECOVERY", f"Initiating recovery path for candidate: {candidate_to_verify.perspective if isinstance(candidate_to_verify, SolutionCandidate) else candidate_to_verify.generator_id}", state)
        
        try:
            raw_verification, _ = await self._call_llm_cached(
                role="recovery_path",
                system_prompt=phases.CROSS_VERIFICATION_SYSTEM,
                user_prompt=phases.cross_verification_prompt(state, candidate_solution=asdict(candidate_to_verify)),
                # verification uses recovery_path temperature from registry
                max_tokens=1024, state=state)
            verification_data = extract_json(raw_verification)
            if verification_data.get("verification_findings"):
                self._log("RECOVERY", f"Cross-verification found issues for candidate. Findings: {verification_data['verification_findings'][:TRUNCATION.MEMORY]}", state)
                # Do NOT append to state.errors — recovery findings are diagnostics, not pipeline failures.
            else:
                self._log("RECOVERY", "Cross-verification found no issues.", state)
        except ParseError as e:
            self._log("RECOVERY", f"Recovery Path: Parse error during verification: {e}", state)
            state.errors.append(f"Recovery Path: Parse error during verification for candidate (id: {candidate_to_verify.perspective if isinstance(candidate_to_verify, SolutionCandidate) else candidate_to_verify.generator_id}): {str(e)}")
        except Exception as e:
            self._log("RECOVERY", f"Recovery Path: Verification failed: {e}", state)
            state.errors.append(f"Recovery Path: Verification failed for candidate (id: {candidate_to_verify.perspective if isinstance(candidate_to_verify, SolutionCandidate) else candidate_to_verify.generator_id}): {str(e)}")
        
        self._log("RECOVERY", "Recovery path complete.", state)
