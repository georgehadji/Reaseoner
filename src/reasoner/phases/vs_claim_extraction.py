"""VS Claim Extraction stage — ClaimExtractionStage."""
from __future__ import annotations

import asyncio
from collections import Counter
from enum import Enum
from typing import Any, Protocol

from pydantic import BaseModel, Field

from reasoner.reasoner_vs_constants import VS_CONSENSUS_MIN_SUPPORT
from reasoner.phases.vs_generation import GenerationCandidate
from reasoner.vs_config import VSFeatureFlags


class _LLMClient(Protocol):
    async def generate(self, *, system: str = "", user: str = "") -> str: ...


class ClaimExtractionMode(str, Enum):
    SINGLE = "single"
    UNION = "union"
    CONSENSUS = "consensus"


class VSClaimExtractionConfig(BaseModel):
    mode: ClaimExtractionMode = ClaimExtractionMode.SINGLE


class ExtractedClaimSet(BaseModel):
    claims: list[str]
    source: str
    vs_metadata: dict[str, Any] = Field(default_factory=dict)


async def _extract_claims(text: str, llm_client: _LLMClient | None) -> list[str]:
    """Stub claim extraction: split on sentences for testing."""
    if llm_client is None:
        # Simple sentence split fallback
        return [s.strip() for s in text.replace("!", ".").replace("?", ".").split(".") if s.strip()]
    prompt = f"Extract factual claims from this text as a JSON list of strings:\n{text}"
    raw = await llm_client.generate(user=prompt)
    # Fallback to sentence split if parsing fails
    return [s.strip() for s in text.replace("!", ".").replace("?", ".").split(".") if s.strip()]


async def extract_claims_from_vs_candidates(
    candidates: list[GenerationCandidate],
    config: VSClaimExtractionConfig,
    llm_client: _LLMClient,
    flags: VSFeatureFlags,
) -> ExtractedClaimSet:
    if not flags.claim_extraction:
        return ExtractedClaimSet(claims=[c.text for c in candidates], source="direct")

    if not candidates:
        return ExtractedClaimSet(claims=[], source="direct")

    if config.mode == ClaimExtractionMode.SINGLE:
        return ExtractedClaimSet(claims=[candidates[0].text], source="single")

    if config.mode == ClaimExtractionMode.UNION:
        tasks = [asyncio.create_task(_extract_claims(c.text, llm_client)) for c in candidates]
        results = await asyncio.gather(*tasks)
        all_claims: list[str] = []
        seen: set[str] = set()
        for sublist in results:
            for claim in sublist:
                key = claim.lower().strip()
                if key not in seen:
                    seen.add(key)
                    all_claims.append(claim)
        return ExtractedClaimSet(claims=all_claims, source="union")

    # CONSENSUS
    tasks = [asyncio.create_task(_extract_claims(c.text, llm_client)) for c in candidates]
    results = await asyncio.gather(*tasks)
    claim_counts = Counter(claim.lower().strip() for sublist in results for claim in sublist)
    consensus = [claim for sublist in results for claim in sublist if claim_counts[claim.lower().strip()] > len(candidates) / 2]
    # Deduplicate while preserving first-seen order
    seen: set[str] = set()
    deduped: list[str] = []
    for claim in consensus:
        key = claim.lower().strip()
        if key not in seen:
            seen.add(key)
            deduped.append(claim)
    return ExtractedClaimSet(claims=deduped, source="consensus")
