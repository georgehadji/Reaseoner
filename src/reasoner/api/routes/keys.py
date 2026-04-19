"""API key status and validation endpoints."""

from __future__ import annotations

import asyncio
import logging
import os

from fastapi import APIRouter, Request

from reasoner.core.constants import TIMEOUTS, VALIDATION_TEST_MAX_TOKENS
from reasoner.llm import _REGISTRY, build_provider

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/keys/status")
async def get_api_keys_status():
    """
    Get status of all configured LLM provider API keys.

    Returns which keys are set (without revealing values) and which
    providers are available for use.
    """
    env_status: dict[str, dict] = {}

    for model_id, cfg in _REGISTRY.items():
        env_var = cfg.get("env", "")
        if not env_var:
            continue

        if env_var not in env_status:
            key_value = os.environ.get(env_var, "")
            env_status[env_var] = {
                "is_set": bool(key_value),
                "key_length": len(key_value) if key_value else 0,
                "models": [],
                "is_local": cfg.get("is_local", False),
            }

        env_status[env_var]["models"].append(model_id)

    total_providers = len(env_status)
    configured = sum(1 for s in env_status.values() if s["is_set"])

    # SECURITY: Do not expose provider names, env vars, or model lists
    return {
        "summary": {
            "total_providers": total_providers,
            "configured": configured,
            "missing": total_providers - configured,
        },
    }


@router.post("/api/keys/validate")
async def validate_api_keys(request: Request):
    """
    Pre-flight validation of API keys.

    Tests each configured provider with a minimal request to verify
    the API key is valid and the service is accessible.
    """
    results = {}
    tested_envs = set()

    for model_id, cfg in _REGISTRY.items():
        env_var = cfg.get("env", "")
        if not env_var or env_var in tested_envs:
            continue
        tested_envs.add(env_var)

        if cfg.get("is_local"):
            results[env_var] = {
                "status": "skipped",
                "reason": "Local provider - no API key needed",
            }
            continue

        key = os.environ.get(env_var, "")
        if not key:
            results[env_var] = {
                "status": "missing",
                "reason": f"Environment variable {env_var} not set",
            }
            continue

        try:
            provider = build_provider(model_id)
            await asyncio.wait_for(
                provider.complete(
                    system_prompt="Reply with: ok",
                    user_prompt="test",
                    max_tokens=VALIDATION_TEST_MAX_TOKENS,
                ),
                timeout=TIMEOUTS.MODEL_VALIDATION,
            )
            results[env_var] = {
                "status": "valid",
                "model_tested": model_id,
            }
        except asyncio.TimeoutError:
            results[env_var] = {
                "status": "timeout",
                "reason": "Provider did not respond within 10 seconds",
            }
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)[:200]
            results[env_var] = {
                "status": "error",
                "error_type": error_type,
                "reason": error_msg,
            }

    valid_count = sum(1 for r in results.values() if r["status"] == "valid")
    total_count = len(results)

    # SECURITY: Do not expose per-provider validation details or model IDs
    return {
        "summary": {
            "valid": valid_count,
            "total": total_count,
            "all_valid": valid_count == total_count,
        },
    }
