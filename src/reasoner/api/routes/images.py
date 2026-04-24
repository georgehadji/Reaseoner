"""Image generation endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request

from reasoner.api.auth_deps import check_rate_limit, optional_auth
from reasoner.api.schemas import GenerateImageRequest
from reasoner.infrastructure.llm.image_generation import enhance_image_prompt, generate_images

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/api/generate-image")
async def generate_image_endpoint(
    request: Request,
    body: GenerateImageRequest,
    authenticated=Depends(optional_auth),
    rate_limit_checked=Depends(check_rate_limit),
):
    """Generate images from a text prompt using 2 multimodal models in parallel.

    Automatically enhances the prompt before generation.

    Uses a 2-model parallel pair based on the selected preset:
      - budget: gemini-flash-image + gpt-5-image-mini
      - premium: gemini-pro-image + gpt-5-image
    """
    try:
        if body.preview_only:
            enhanced_prompt = await enhance_image_prompt(body.prompt)
            return {
                "success": True,
                "images": [],
                "enhanced_prompt": enhanced_prompt,
                "rewritten_prompt": None,
            }
        result = await generate_images(
            prompt=body.prompt,
            preset=body.preset,
            enhance=body.enhance,
            aspect_ratio=body.aspect_ratio,
            resolution=body.resolution,
            reference_images=body.reference_images,
            num_images=body.num_images,
        )
        if not result.get("success"):
            logger.error("Image generation failed: %s", result.get("error"))
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
            }
        return {
            "success": True,
            "images": result["images"],
            "enhanced_prompt": result.get("enhanced_prompt"),
            "rewritten_prompt": result.get("rewritten_prompt"),
        }
    except Exception as exc:
        logger.error("Image generation endpoint error: %s", exc)
        return {
            "success": False,
            "error": "Internal server error",
        }
