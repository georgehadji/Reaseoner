"""
PhaseSubAgent package — intra-phase focused reasoning agents.

Each sub-agent has one job, accesses PipelineState, and returns structured output.
Hyper-agents orchestrate parallel sub-agents and synthesize their results.

Example:
    from reasoner.subagents.synthesis import SynthesisHyperAgent
    agent = SynthesisHyperAgent()
    final_solution = await agent.execute(state, router)
"""

from reasoner.subagents.base import PhaseSubAgent
from reasoner.subagents.models import PhaseSubAgentInput, PhaseSubAgentOutput

__all__ = [
    "PhaseSubAgent",
    "PhaseSubAgentInput",
    "PhaseSubAgentOutput",
]
