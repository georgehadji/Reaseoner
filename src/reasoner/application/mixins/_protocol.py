"""Protocol defining the interface expected by all ReasonerPipeline mixins."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from reasoner.infrastructure.llm.router import ProviderRouter
from reasoner.models import GenerationCandidate, PipelineState, SolutionCandidate


@runtime_checkable
class PipelineMixinProtocol(Protocol):
    """
    Protocol that documents the attributes and methods mixins expect from
    ``ReasonerPipeline``.  Inheriting from this protocol is optional at runtime
    (it is *not* enforced by ``ReasonerPipeline`` itself), but it serves two
    purposes:

    1. **Documentation** — makes the mixin → pipeline contract explicit.
    2. **Type checking** — mypy / pyright can verify that mixin methods only
       access attributes declared here.

    .. note::
       ``ReasonerPipeline`` does **not** formally implement this protocol (it does
       not need the ``Protocol`` base class).  Mixins may inherit from it for
       IDE auto-completion and static analysis.
    """

    router: ProviderRouter
    """Provider router used to select LLM backends per role."""

    def _log(self, phase: str, message: str, state: PipelineState) -> None:
        """Emit a structured log entry for *phase*."""
        ...

    async def _call_llm_cached(
        self,
        role: str,
        system_prompt: str,
        user_prompt: str,
        state: PipelineState,
        phase_key: str | None = None,
        **kwargs: Any,
    ) -> tuple[str, dict[str, Any]]:
        """Call the LLM with token-aware caching and cost tracking."""
        ...

    async def _run_recovery_path(
        self,
        state: PipelineState,
        candidate_to_verify: SolutionCandidate | GenerationCandidate,
    ) -> None:
        """Execute a cross-verification path for a problematic candidate."""
        ...
