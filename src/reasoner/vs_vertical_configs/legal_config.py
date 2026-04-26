"""Legal vertical configuration for VS."""
from __future__ import annotations

from reasoner.ara_vs_constants import VS_K_GENERATION, VS_TAIL_THRESHOLD_LEGAL
from reasoner.vs_config import VSVerticalConfig, VSVerticalRegistry

LEGAL_CONFIG = VSVerticalConfig(
    domain="legal",
    k=VS_K_GENERATION,
    tail_threshold=VS_TAIL_THRESHOLD_LEGAL,
    generation_strategy="best_verifiable",
    probe_template="Generate {k} angles a legal analyst would investigate for: {query}",
    compliance_flags=["human_review_on_low_prob"],
)

VSVerticalRegistry.register(LEGAL_CONFIG)
