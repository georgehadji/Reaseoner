"""WebSocket endpoints for real-time pipeline updates."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket

from reasoner.infrastructure.websocket import (
    get_websocket_manager,
    websocket_endpoint,
)

router = APIRouter()


@router.websocket("/ws")
async def websocket_connect(
    websocket: WebSocket,
    pipeline_id: str | None = None,
):
    """
    WebSocket endpoint for real-time pipeline updates.

    Usage:
        ws://<host>:<port>/ws
        ws://<host>:<port>/ws?pipeline_id=xxx

    Messages:
        - subscribe: {"type": "subscribe", "pipeline_id": "xxx"}
        - unsubscribe: {"type": "unsubscribe", "pipeline_id": "xxx"}
        - ping: {"type": "ping"}

    Responses:
        - event: Pipeline domain events
        - progress: Phase progress updates
        - complete: Pipeline completion
        - error: Error notifications
    """
    await websocket_endpoint(websocket, pipeline_id)


@router.websocket("/ws/pipeline/{pipeline_id}")
async def pipeline_websocket(
    websocket: WebSocket,
    pipeline_id: str,
):
    """
    WebSocket endpoint for specific pipeline.

    Automatically subscribes to pipeline updates.
    """
    await websocket_endpoint(websocket, pipeline_id)


@router.get("/api/websocket/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics."""
    manager = get_websocket_manager()
    return {
        "active_connections": manager.get_connection_count(),
        "subscriptions": {
            pipeline_id: manager.get_subscriber_count(pipeline_id)
            for pipeline_id in manager.subscriptions.keys()
        },
    }
