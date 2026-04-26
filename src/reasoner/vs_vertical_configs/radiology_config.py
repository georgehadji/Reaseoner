"""Radiology vertical configuration for VS."""
from __future__ import annotations

from reasoner.ara_vs_constants import VS_K_RADIOLOGY_GENERATION, VS_TAIL_THRESHOLD_RADIOLOGY
from reasoner.vs_config import VSVerticalConfig, VSVerticalRegistry

RADIOLOGY_CONFIG = VSVerticalConfig(
    domain="radiology",
    k=VS_K_RADIOLOGY_GENERATION,
    tail_threshold=VS_TAIL_THRESHOLD_RADIOLOGY,
    generation_strategy="best_verifiable",
    probe_template="Generate {k} distinct clinical questions a radiologist would ask about: {query}",
    compliance_flags=["fda_510k", "hipaa_minimal"],
)

VSVerticalRegistry.register(RADIOLOGY_CONFIG)
