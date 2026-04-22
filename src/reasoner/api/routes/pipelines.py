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


@router.post("/api/pipelines/{pipeline_id}/resume")
async def resume_pipeline(pipeline_id: str):
    """Resume a paused/failed pipeline from event history."""
    try:
        from reasoner.api import get_architecture_components
        from reasoner.application.commands import ResumePipelineCommand

        _, handler_registry = get_architecture_components()
        command = ResumePipelineCommand(
            command_id=f"resume-{pipeline_id}",
            timestamp=time.time(),
            pipeline_id=pipeline_id,
        )
        result = await handler_registry.handle_command(command)
        return result
    except ValueError as e:
        return {"error": str(e), "can_resume": False}
    except Exception as e:
        logger.error(f"Resume pipeline error: {e}")
        return {"error": str(e), "can_resume": False}


@router.post("/api/pipelines/{pipeline_id}/resume-stream")
async def resume_pipeline_stream(pipeline_id: str):
    """Resume a pipeline by reconstructing its context and starting a fresh stream.

    This is a "resume-as-restart" approach: the pipeline's problem, preset, and
    prior synthesis are recovered from the event store, then a new run is started.
    The original pipeline metadata is returned in the first SSE event.
    """
    from fastapi.responses import StreamingResponse

    from reasoner.api import get_architecture_components
    from reasoner.application.commands import ResumePipelineCommand
    from reasoner.api.streaming import run_stream
    from reasoner.api.schemas import RunRequest
    from reasoner.api.serializers import _event

    _, handler_registry = get_architecture_components()
    command = ResumePipelineCommand(
        command_id=f"resume-stream-{pipeline_id}",
        timestamp=time.time(),
        pipeline_id=pipeline_id,
    )

    try:
        result = await handler_registry.handle_command(command)
    except ValueError as e:
        return {"error": str(e), "can_resume": False}
    except Exception as e:
        logger.error(f"Resume stream error: {e}")
        return {"error": str(e), "can_resume": False}

    problem = result.get("problem", "")
    preset = result.get("preset", "auto-budget")

    if not problem:
        return {"error": "Recovered problem is empty", "can_resume": False}

    req = RunRequest(
        problem=problem,
        preset=preset,
        top_k=2,
        sequential=False,
        no_cache=True,
        client_run_id=pipeline_id,
    )

    async def stream_with_resume_meta():
        yield _event({
            "type": "resume_meta",
            "original_pipeline_id": pipeline_id,
            "phases_completed": result.get("phases_completed", []),
            "previous_synthesis": result.get("previous_synthesis", ""),
        })
        async for chunk in run_stream(req):
            yield chunk

    return StreamingResponse(
        stream_with_resume_meta(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


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
