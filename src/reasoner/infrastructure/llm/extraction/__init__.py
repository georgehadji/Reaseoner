"""Image and document extraction utilities using vision-capable LLMs."""

from __future__ import annotations

import base64
import logging
from typing import Optional

from reasoner.infrastructure.llm.registry import build_provider

logger = logging.getLogger(__name__)

# Cheap vision model for image captioning — prioritizes cost-effectiveness
# Tiered fallback: Gemini Flash-Lite (cheapest) → GLM-4.6V → Gemini 2.5 Flash
_CAPTION_MODELS = ["gemini-flash", "glm-4-airx", "gemini-pro"]

# Cache to avoid re-describing the same image
_image_cache: dict[str, str] = {}


def _compute_image_hash(content: bytes) -> str:
    """Compute a simple hash for image deduplication."""
    import hashlib
    return hashlib.sha256(content).hexdigest()[:16]


def _encode_image_base64(content: bytes) -> str:
    """Encode image bytes to base64 data URI."""
    return base64.b64encode(content).decode("utf-8")


async def describe_image(content: bytes, filename: str) -> str:
    """
    Describe an image using a cheap vision-capable model via OpenRouter.

    Args:
        content: Raw image bytes
        filename: Original filename (for mime type detection)

    Returns:
        Detailed text description of the image
    """
    image_hash = _compute_image_hash(content)
    if image_hash in _image_cache:
        return _image_cache[image_hash]

    # Detect mime type from filename
    ext = filename.lower().split(".")[-1] if "." in filename else "png"
    mime_type = f"image/{ext.replace('jpg', 'jpeg').replace('webp', 'webp').replace('png', 'png')}"

    b64_data = _encode_image_base64(content)

    # Build the multimodal message payload
    # OpenRouter format: content as list of {type, text/image_url} dicts
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "Describe this image in detail. Include any text visible in the image, "
                        "charts, diagrams, tables, and their meaning. Be thorough and factual."
                    ),
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{b64_data}",
                        "detail": "high",
                    },
                },
            ],
        }
    ]

    last_error: Optional[str] = None
    for model_id in _CAPTION_MODELS:
        try:
            provider = build_provider(model_id)
            # Use the provider's underlying async client
            response = await provider._client.chat.completions.create(
                model=provider.model,
                messages=messages,  # type: ignore[arg-type]
                max_tokens=1024,
                temperature=0.3,
            )
            description = response.choices[0].message.content or "[No description returned]"
            _image_cache[image_hash] = description
            return description

        except Exception as e:
            last_error = f"{model_id}: {e}"
            logger.warning(f"Image captioning failed with {model_id}: {e}")
            continue

    logger.error(f"All caption models failed. Last error: {last_error}")
    return f"[Image description unavailable — all vision models failed. Last error: {last_error}]"
