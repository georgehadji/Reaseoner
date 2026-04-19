"""Widget, suggestions, and UI status endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter

from reasoner.api.schemas import SuggestionRequestModel
from reasoner.suggestions import generate_suggestions_async, SuggestionRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/ui/status")
async def ui_status():
    """Check if UI integration is available."""
    return {
        "available": True,
        "endpoints": {
            "run_with_context": "/api/run-with-context",
        },
        # SECURITY: Do not expose supported methods or presets
    }


@router.get("/api/presets")
async def api_presets():
    # SECURITY: Do not expose preset names, descriptions, or key requirements
    return {}


@router.get("/api/models")
async def api_models():
    # SECURITY: Do not expose available models or provider configuration
    return []


@router.post("/api/suggestions")
async def get_suggestions(req: SuggestionRequestModel):
    """Get smart search suggestions based on query."""
    try:
        request = SuggestionRequest(
            query=req.query,
            chat_history=req.chat_history,
            max_suggestions=req.max_suggestions,
        )
        response = await generate_suggestions_async(request)
        return {"suggestions": response.suggestions, "query": response.query}
    except Exception as e:
        logger.error(f"Suggestions error: {e}")
        return {"suggestions": [], "query": req.query}


@router.post("/api/widget/execute")
async def execute_widget(req):
    """
    Execute widget using new architecture.

    Supports auto-detection from query or explicit widget execution.
    """
    try:
        from reasoner.api import get_architecture_components

        _, handler_registry = get_architecture_components()
        result = await handler_registry.handle_command(req)
        return result
    except Exception as e:
        logger.error(f"Widget execution error: {e}")
        return {"error": str(e), "detected": False}


@router.get("/api/widgets/list")
async def list_widgets():
    """List all available widgets."""
    try:
        from reasoner.infrastructure.widgets import get_widget_registry

        registry = get_widget_registry()
        widgets = registry.list_widgets()
        return {"widgets": widgets, "total": len(widgets)}
    except Exception as e:
        logger.error(f"List widgets error: {e}")
        return {"error": str(e), "widgets": []}


@router.get("/api/widgets/detect")
async def detect_widgets(query: str = ""):
    """Detect widgets for a query."""
    try:
        from reasoner.infrastructure.widgets import get_widget_registry

        registry = get_widget_registry()
        detections = await registry.detect_widgets(query)
        return {
            "detected": len(detections) > 0,
            "widgets": [d.to_dict() for d in detections],
        }
    except Exception as e:
        logger.error(f"Widget detection error: {e}")
        return {"detected": False, "widgets": []}
