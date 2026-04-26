"""Aerospace vertical configuration for VS."""
from __future__ import annotations

from reasoner.ara_vs_constants import VS_K_GENERATION, VS_TAIL_THRESHOLD_AEROSPACE
from reasoner.vs_config import VSVerticalConfig, VSVerticalRegistry

AEROSPACE_CONFIG = VSVerticalConfig(
    domain="aerospace",
    k=VS_K_GENERATION,
    tail_threshold=VS_TAIL_THRESHOLD_AEROSPACE,
    generation_strategy="best_verifiable",
    probe_template="Generate {k} failure-mode probes an aerospace engineer would consider for: {query}",
    compliance_flags=["cmmc_lvl2"],
)

VSVerticalRegistry.register(AEROSPACE_CONFIG)
