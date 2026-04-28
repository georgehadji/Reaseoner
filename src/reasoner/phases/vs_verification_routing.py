"""VS Two-Tier Verification Routing stage."""
from __future__ import annotations

from enum import Enum

from reasoner.reasoner_vs_constants import VS_ROUTING_HIGH_PROB, VS_ROUTING_MEDIUM_PROB
from reasoner.vs_config import VSFeatureFlags


class VerificationRoute(str, Enum):
    NLI_ONLY = "nli_only"
    NLI_THEN_LLM = "nli_then_llm"
    CONSERVATIVE = "conservative"


async def route_claim_by_vs_probability(
    claim: str,
    probability: float,
    flags: VSFeatureFlags,
) -> tuple[VerificationRoute, dict]:
    if not flags.verification_routing:
        return VerificationRoute.NLI_ONLY, {}

    if probability >= VS_ROUTING_HIGH_PROB:
        return VerificationRoute.NLI_ONLY, {"confidence": "high"}

    if probability >= VS_ROUTING_MEDIUM_PROB:
        return VerificationRoute.NLI_THEN_LLM, {"confidence": "medium"}

    return VerificationRoute.CONSERVATIVE, {"confidence": "low", "human_review_flag": True}
