"""
Single source of truth for all hardcoded constants used across the Reasoner project.

This module contains ONLY pure constants (no I/O, no environment reads, no side effects)
so it is safe to import from anywhere without risk of circular dependencies or
unexpected initialization order issues.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# ═════════════════════════════════════════════════════════════════════
# DEFAULTS
# ═════════════════════════════════════════════════════════════════════

DEFAULT_MAX_TOKENS: int = 2048
DEFAULT_TEMPERATURE: float = 0.7
DEFAULT_TOP_K: int = 2
DEFAULT_PRESET: str = "multi-perspective-budget"
DEFAULT_CLI_PRESET: str = "multi-perspective-budget"
DEFAULT_SEQUENTIAL: bool = False
DEFAULT_SOURCE_TYPE: Literal["general", "academic", "social", "news", "code"] = "general"
DEFAULT_NUM_SUGGESTIONS: int = 5
DEFAULT_SEARCH_RESULTS: int = 10
DEFAULT_MAX_DECOMPOSED_QUERIES: int = 3
DEFAULT_CIRCUIT_BREAKER_THRESHOLD: int = 3
DEFAULT_MAX_RETRIES: int = 3
DEFAULT_BACKOFF_BASE: int = 2
DEFAULT_BACKOFF_DELAY: float = 1.0
DEFAULT_HEARTBEAT_INTERVAL: float = 30.0
DEFAULT_SNAPSHOT_INTERVAL: float = 60.0
DEFAULT_DB_COMMAND_TIMEOUT: int = 60
CORS_MAX_AGE_SECONDS: int = 86400
MAX_CACHE_FILES: int = 1000
MAX_CIRCUIT_BREAKER_REGISTRY_SIZE: int = 1000
MAX_RATE_LIMIT_BUCKETS: int = 10000
SNAPSHOT_LIST_LIMIT: int = 1000
DEFAULT_SANITIZER_MAX_LENGTH: int = 10000
DEFAULT_API_PORT: int = 8001
SSE_FLUSH_INTERVAL: float = 0.02
VALIDATION_TEST_MAX_TOKENS: int = 1

# ═════════════════════════════════════════════════════════════════════
# GATE AGENT
# ═════════════════════════════════════════════════════════════════════

GATE_MAX_TOKENS: int = 256
GATE_TEMPERATURE: float = 0.0
GATE_TIMEOUT_SECONDS: float = 5.0
GATE_CONFIDENCE_THRESHOLD: float = 0.70
GATE_DEFAULT_MODEL: str = "gemini-flash"  # non-OpenAI model that supports temperature=0

# ═════════════════════════════════════════════════════════════════════
# HYPERGATE AGENT (sub-agent orchestrator replacing GateAgent)
# ═════════════════════════════════════════════════════════════════════

HYPERGATE_DIRECT_THRESHOLD: float = 0.80   # DirectDetector confidence floor
HYPERGATE_WEB_THRESHOLD: float = 0.75      # WebDetector confidence floor
HYPERGATE_METHOD_THRESHOLD: float = 0.70   # MethodClassifier confidence floor
HYPERGATE_AMBIGUOUS_FLOOR: float = 0.45    # Below this on all agents → hard fallback
HYPERGATE_TIMEOUT_SECONDS: float = 6.0     # Per-sub-agent call timeout
HYPERGATE_CACHE_SIZE: int = 512            # LRU size (per sub-agent + top-level)
HYPERGATE_MAX_TOKENS_LANGUAGE: int = 80
HYPERGATE_MAX_TOKENS_COMPLEXITY: int = 80
HYPERGATE_MAX_TOKENS_DIRECT: int = 100
HYPERGATE_MAX_TOKENS_WEB: int = 100
HYPERGATE_MAX_TOKENS_METHOD: int = 128
HYPERGATE_MAX_TOKENS_TIEBREAK: int = 200

# ═════════════════════════════════════════════════════════════════════
# TOKEN BUDGETS
# ═════════════════════════════════════════════════════════════════════

PHASE_TOKEN_BUDGETS: dict[str, int] = {
    # Phase 0: Simple classification - minimal output
    "classification": 256,
    # Phase 1: Decomposition - structured but bounded
    "decomposition": 1024,
    # Phase 2: Perspective analysis - moderate detail
    "perspective": 1536,
    "constructive": 1536,
    "destructive": 2560,
    "systemic": 1536,
    "minimalist": 1536,
    # Phase 3: Critique - scores + brief rationale
    "critique": 1024,
    "scoring": 1024,
    # Phase 4: Stress testing - scenario results
    "stress_testing": 1024,
    # Phase 5: Synthesis - comprehensive final output
    "synthesis": 12288,
    # Method-specific phases
    "debate_opening": 1024,
    "debate_rebuttal": 1024,
    "debate_judge": 1024,
    "jury_generator": 1536,
    "jury_critic": 1024,
    "jury_verifier": 1024,
    "iterative_generate": 1536,
    "iterative_critique": 1024,
    "research": 4096,
    "verification": 1024,
    "deep_read": 2048,
    "cross_verify": 1024,
    # Default fallback
    "default": 1536,
}


def get_token_budget(role: str) -> int:
    """Get token budget for a specific role/phase."""
    return PHASE_TOKEN_BUDGETS.get(role, PHASE_TOKEN_BUDGETS["default"])


# ═════════════════════════════════════════════════════════════════════
# BASE URLs
# ═════════════════════════════════════════════════════════════════════

DEFAULT_SEARXNG_URL: str = "http://localhost:8888"
DEFAULT_NEURO_URL: str = "http://localhost:50001"
DEFAULT_OLLAMA_URL: str = "http://localhost:11434"
OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
OPENAI_BASE_URL: str = "https://api.openai.com/v1"
ANTHROPIC_BASE_URL: str = "https://api.anthropic.com/v1"
GOOGLE_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"

# ═════════════════════════════════════════════════════════════════════
# MODEL ALIASES
# ═════════════════════════════════════════════════════════════════════

MODEL_CLAUDE_SONNET: str = "claude-sonnet"
MODEL_GEMINI_FLASH: str = "gemini-flash"
MODEL_GEMINI_PRO: str = "gemini-pro"
MODEL_GPT4O_MINI: str = "gpt-4o-mini"
MODEL_GEMINI_FLASH_IMAGE: str = "gemini-flash-image"
MODEL_GEMINI_PRO_IMAGE: str = "gemini-pro-image"
MODEL_GEMINI_31_FLASH_IMAGE_PREVIEW: str = "gemini-3.1-flash-image-preview"
MODEL_GPT5_IMAGE: str = "gpt-5-image"
MODEL_GPT5_IMAGE_MINI: str = "gpt-5-image-mini"
MODEL_FLUX_2_PRO: str = "flux.2-pro"
MODEL_FLUX_2_FLEX: str = "flux.2-flex"

# Qwen (temperature-supporting, non-OpenAI)
MODEL_QWEN35_FLASH: str = "qwen3.5-flash"
MODEL_QWEN35_9B: str = "qwen3.5-9b"
MODEL_QWEN36_PLUS: str = "qwen3.6-plus"

# MiniMax (temperature-supporting, non-OpenAI, cross-lab diversity)
MODEL_MINIMAX_M25_FREE: str = "minimax-m2.5-free"
MODEL_MINIMAX_M27: str = "minimax-m2.7"

# Xiaomi (temperature-supporting, non-OpenAI, cross-lab diversity)
MODEL_MIMO_V2_PRO: str = "mimo-v2-pro"
MODEL_MIMO_V2_FLASH: str = "mimo-v2-flash"

# ═════════════════════════════════════════════════════════════════════
# GROUPED LIMITS (Value Object Pattern via frozen dataclasses)
# ═════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Timeouts:
    HEALTH_CHECK: float = 5.0
    EMBEDDING: float = 15.0
    SEARCH_CLIENT: float = 30.0
    SCRAPER: float = 30.0
    WIDGET: float = 10.0
    WIDGET_SHORT: float = 5.0
    MODEL_VALIDATION: float = 10.0
    HTTP_TOTAL: float = 60.0
    HTTP_CONNECT: float = 10.0


@dataclass(frozen=True)
class TruncationLimits:
    PROBLEM: int = 500
    CONTENT: int = 800
    SNIPPET: int = 500
    API_STORAGE: int = 200
    KEY_INSIGHTS: int = 3
    MEMORY: int = 2
    SESSION_LOG: int = 200
    SESSION_EXCERPT: int = 100
    ASSUMPTION: int = 150
    SOLUTION: int = 1000
    PROMPT: int = 300
    LARGE_CONTENT: int = 4000
    DEEP_READ: int = 8000


TIMEOUTS = Timeouts()
TRUNCATION = TruncationLimits()

# ═════════════════════════════════════════════════════════════════════
# PROMPT / JSON CONSTANTS
# ═════════════════════════════════════════════════════════════════════

JSON_ONLY_FOOTER: str = "Output ONLY valid JSON."

# ═════════════════════════════════════════════════════════════════════
# IMAGE GENERATION
# ═════════════════════════════════════════════════════════════════════

IMAGE_GEN_BUDGET_PRESET: str = "image-gen-budget"
IMAGE_GEN_PREMIUM_PRESET: str = "image-gen-premium"
IMAGE_GEN_PRESET_ALIASES: tuple[str, str] = ("budget", "premium")
IMAGE_GEN_ALLOWED_PRESETS: tuple[str, str] = (
    IMAGE_GEN_BUDGET_PRESET,
    IMAGE_GEN_PREMIUM_PRESET,
)
IMAGE_GEN_DEFAULT_PRESET: str = IMAGE_GEN_BUDGET_PRESET
IMAGE_GEN_DEFAULT_ASPECT_RATIO: str = "1:1"
IMAGE_GEN_ALLOWED_ASPECT_RATIOS: tuple[str, ...] = ("1:1", "16:9", "9:16", "4:3", "3:4")
IMAGE_GEN_DEFAULT_RESOLUTION: str = "1024x1024"
IMAGE_GEN_DEFAULT_WIDTH: int = 1024
IMAGE_GEN_DEFAULT_HEIGHT: int = 1024
IMAGE_GEN_REMOTE_TIMEOUT_SECONDS: float = 20.0
IMAGE_GEN_COMPLETION_TIMEOUT_SECONDS: float = 90.0
IMAGE_GEN_ENHANCEMENT_MODEL: str = MODEL_GEMINI_FLASH
IMAGE_GEN_PRESETS: dict[str, list[str]] = {
    "budget": [MODEL_GEMINI_FLASH_IMAGE, MODEL_GPT5_IMAGE_MINI],
    "premium": [MODEL_GEMINI_PRO_IMAGE, MODEL_GPT5_IMAGE],
    IMAGE_GEN_BUDGET_PRESET: [MODEL_GEMINI_FLASH_IMAGE, MODEL_GPT5_IMAGE_MINI],
    IMAGE_GEN_PREMIUM_PRESET: [MODEL_GEMINI_PRO_IMAGE, MODEL_GPT5_IMAGE],
}
IMAGE_GEN_FALLBACKS: dict[str, list[str]] = {
    "budget": [MODEL_GEMINI_31_FLASH_IMAGE_PREVIEW, MODEL_FLUX_2_FLEX],
    "premium": [MODEL_GPT5_IMAGE_MINI, MODEL_FLUX_2_PRO, MODEL_FLUX_2_FLEX],
    IMAGE_GEN_BUDGET_PRESET: [MODEL_GEMINI_31_FLASH_IMAGE_PREVIEW, MODEL_FLUX_2_FLEX],
    IMAGE_GEN_PREMIUM_PRESET: [MODEL_GPT5_IMAGE_MINI, MODEL_FLUX_2_PRO, MODEL_FLUX_2_FLEX],
}
IMAGE_GEN_ENHANCEMENT_SYSTEM_PROMPT: str = (
    "You are an expert image-generation prompt engineer for DALL-E 3, Midjourney, and Flux. "
    "Take the user's simple description and expand it into a highly detailed, vivid prompt "
    "optimized for AI image generation. "
    "Focus on: "
    "1. Subject: Detailed description of the main focus. "
    "2. Style: Artistic style (e.g., photorealistic, oil painting, cinematic, synthwave). "
    "3. Composition: Camera angle, depth of field, framing. "
    "4. Lighting: Type of light, direction, mood. "
    "5. Colors: Color palette, saturation, contrast. "
    "6. Details: Texture, atmosphere, intricate background elements. "
    "Output ONLY the enhanced prompt — no intro, no quotes, no explanation."
)
IMAGE_GEN_POLICY_REWRITE_SYSTEM_PROMPT: str = (
    "You rewrite image prompts so they are safe for mainstream image providers. "
    "If the prompt references copyrighted, trademarked, franchise, mascot, or studio-owned characters, "
    "replace them with original non-infringing character descriptions while preserving scene, medium, mood, "
    "composition, color palette, and high-level archetypes. "
    "Do not mention any brand, franchise, studio, or character names in the rewritten prompt. "
    "Keep the prompt concrete and production-ready for image generation. "
    "Output ONLY the rewritten prompt."
)

# ═════════════════════════════════════════════════════════════════════
# ARTICLE / ESSAY GENERATION
# ═════════════════════════════════════════════════════════════════════

ARTICLE_MIN_SOURCE_COUNT: int = 8
ARTICLE_MAX_SOURCE_COUNT: int = 16
ARTICLE_SEARCH_RESULTS_PER_QUERY: int = 6
ARTICLE_MAX_SOURCES_FOR_CLAIM_EXTRACTION: int = 16
ARTICLE_MIN_CLAIM_SUPPORT_RATIO: float = 0.5
