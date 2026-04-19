"""Event store and pipeline management endpoints."""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter

from reasoner.application.queries import GetPipelineStatusQuery

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/events/stats")
async def get_event_stats():
    """Get event store statistics."""
    try:
        from reasoner.api import get_architecture_components

        event_store, _ = get_architecture_components()
        stats = await event_store.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Event stats error: {e}")
        return {"error": str(e)}


@router.get("/api/pipelines")
async def list_pipelines(
    limit: int = 50,
    offset: int = 0,
    status: str | None = None,
):
    """List pipelines from event store."""
    try:
        from reasoner.api import get_architecture_components

        event_store, _ = get_architecture_components()
        pipelines = await event_store.list_pipelines(
            limit=limit,
            offset=offset,
            status=status,
        )
        return {"pipelines": pipelines, "total": len(pipelines)}
    except Exception as e:
        logger.error(f"List pipelines error: {e}")
        return {"error": str(e), "pipelines": []}


@router.get("/api/pipelines/{pipeline_id}")
async def get_pipeline_status(pipeline_id: str):
    """Get pipeline status from event store."""
    try:
        from reasoner.api import get_architecture_components

        event_store, handler_registry = get_architecture_components()

        query = GetPipelineStatusQuery(
            query_id=f"status-{pipeline_id}",
            timestamp=time.time(),
            pipeline_id=pipeline_id,
        )

        result = await handler_registry.handle_query(query)
        return result
    except Exception as e:
        logger.error(f"Get pipeline error: {e}")
        return {"error": str(e)}


@router.delete("/api/pipelines/{pipeline_id}")
async def delete_pipeline(pipeline_id: str):
    """Delete pipeline and all events (GDPR compliance)."""
    try:
        from reasoner.api import get_architecture_components

        event_store, _ = get_architecture_components()
        await event_store.delete_aggregate(pipeline_id)
        return {"status": "deleted", "pipeline_id": pipeline_id}
    except Exception as e:
        logger.error(f"Delete pipeline error: {e}")
        return {"error": str(e)}
