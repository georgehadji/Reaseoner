"""Vertical domain configurations for Verbalized Sampling."""
from __future__ import annotations

# Auto-register vertical configs on package import
from reasoner.vs_vertical_configs import radiology_config, legal_config, aerospace_config

__all__ = ["radiology_config", "legal_config", "aerospace_config"]
