"""
WebSocket Integration for Real-time Event Streaming

Provides real-time updates to clients via WebSocket connections.
Supports:
- Pipeline progress streaming
- Event notifications
- Widget result streaming
"""

from __future__ import annotations

import json
import asyncio
import logging
from typing import Any, Set, Dict
from dataclasses import dataclass, asdict

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from reasoner.core.constants import DEFAULT_HEARTBEAT_INTERVAL

logger = logging.getLogger(__name__)


@dataclass
class WebSocketMessage:
    """WebSocket message structure."""
    type: str  # 'event', 'progress', 'complete', 'error'
    data: dict[str, Any]
    pipeline_id: str | None = None
    
    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps({
            'type': self.type,
            'data': self.data,
            'pipeline_id': self.pipeline_id,
        })


class WebSocketManager:
    """
    Manages WebSocket connections and broadcasting.
    
    Features:
    - Connection management
    - Targeted broadcasting (by pipeline_id)
    - Automatic reconnection support
    - Heartbeat/ping-pong
    """
    
    def __init__(self):
        # Active connections: {connection_id: websocket}
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Subscriptions: {pipeline_id: set[connection_id]}
        self.subscriptions: Dict[str, Set[str]] = {}
        
        # Connection metadata: {connection_id: metadata}
        self.connection_metadata: Dict[str, dict[str, Any]] = {}
        
        # Background task for heartbeats
        self._heartbeat_task: asyncio.Task | None = None
        
        # Concurrency guard for all mutable state
        self._lock: asyncio.Lock = asyncio.Lock()
    
    async def connect(
        self,
        websocket: WebSocket,
        connection_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Accept and register new WebSocket connection."""
        await websocket.accept()
        
        async with self._lock:
            self.active_connections[connection_id] = websocket
            self.connection_metadata[connection_id] = metadata or {}
        
        logger.info(f"WebSocket connected: {connection_id}")
        
        # Send welcome message outside the lock to avoid deadlock
        # if send_to_connection also tries to acquire the lock.
        await self.send_to_connection(
            connection_id,
            WebSocketMessage(
                type='connected',
                data={'connection_id': connection_id},
            ),
        )
    
    def disconnect(self, connection_id: str) -> None:
        """Remove disconnected connection."""
        # asyncio.Lock is not re-entrant, so if this is called from a
        # coroutine that already holds the lock we must not block.
        # In practice all callers run inside the event loop, so we can
        # safely acquire the lock here.
        async def _do_disconnect():
            async with self._lock:
                if connection_id in self.active_connections:
                    del self.active_connections[connection_id]
                
                # Remove from all subscriptions
                for pipeline_id in list(self.subscriptions.keys()):
                    if connection_id in self.subscriptions[pipeline_id]:
                        self.subscriptions[pipeline_id].discard(connection_id)
                
                if connection_id in self.connection_metadata:
                    del self.connection_metadata[connection_id]
            
            logger.info(f"WebSocket disconnected: {connection_id}")
        
        # Schedule the async cleanup on the running loop.
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_do_disconnect())
        except RuntimeError:
            # No running loop (should not happen in production)
            logger.warning(f"No event loop available to disconnect {connection_id}")
    
    async def subscribe(self, connection_id: str, pipeline_id: str) -> None:
        """Subscribe connection to pipeline updates."""
        async with self._lock:
            if pipeline_id not in self.subscriptions:
                self.subscriptions[pipeline_id] = set()
            
            self.subscriptions[pipeline_id].add(connection_id)
        
        logger.info(f"Connection {connection_id} subscribed to pipeline {pipeline_id}")
    
    async def unsubscribe(self, connection_id: str, pipeline_id: str) -> None:
        """Unsubscribe connection from pipeline updates."""
        async with self._lock:
            if pipeline_id in self.subscriptions:
                self.subscriptions[pipeline_id].discard(connection_id)
    
    async def broadcast_to_pipeline(
        self,
        pipeline_id: str,
        message: WebSocketMessage,
    ) -> None:
        """Broadcast message to all subscribers of a pipeline."""
        async with self._lock:
            if pipeline_id not in self.subscriptions:
                return
            connection_ids = list(self.subscriptions[pipeline_id])
        
        for connection_id in connection_ids:
            try:
                await self.send_to_connection(connection_id, message)
            except Exception as e:
                logger.error(f"Failed to send to {connection_id}: {e}")
                self.disconnect(connection_id)
    
    async def send_to_connection(
        self,
        connection_id: str,
        message: WebSocketMessage,
    ) -> None:
        """Send message to specific connection."""
        async with self._lock:
            if connection_id not in self.active_connections:
                return
            websocket = self.active_connections[connection_id]
            
            if websocket.client_state != WebSocketState.CONNECTED:
                # Release lock before calling disconnect to avoid deadlock.
                pass
            else:
                # Release lock and send outside to avoid holding it during I/O.
                pass
        
        if websocket.client_state != WebSocketState.CONNECTED:
            self.disconnect(connection_id)
            return
        
        try:
            await websocket.send_text(message.to_json())
        except Exception as e:
            logger.error(f"Send error to {connection_id}: {e}")
            self.disconnect(connection_id)
    
    async def broadcast_event(
        self,
        event: dict[str, Any],
        pipeline_id: str,
    ) -> None:
        """Broadcast domain event to pipeline subscribers."""
        message = WebSocketMessage(
            type='event',
            data=event,
            pipeline_id=pipeline_id,
        )
        await self.broadcast_to_pipeline(pipeline_id, message)
    
    async def broadcast_progress(
        self,
        phase: str,
        status: str,
        pipeline_id: str,
        progress: dict[str, Any] | None = None,
    ) -> None:
        """Broadcast pipeline progress update."""
        message = WebSocketMessage(
            type='progress',
            data={
                'phase': phase,
                'status': status,
                'progress': progress or {},
            },
            pipeline_id=pipeline_id,
        )
        await self.broadcast_to_pipeline(pipeline_id, message)
    
    async def broadcast_complete(
        self,
        result: dict[str, Any],
        pipeline_id: str,
    ) -> None:
        """Broadcast pipeline completion."""
        message = WebSocketMessage(
            type='complete',
            data={'result': result},
            pipeline_id=pipeline_id,
        )
        await self.broadcast_to_pipeline(pipeline_id, message)
    
    async def broadcast_error(
        self,
        error: str,
        pipeline_id: str,
    ) -> None:
        """Broadcast error to pipeline subscribers."""
        message = WebSocketMessage(
            type='error',
            data={'error': error},
            pipeline_id=pipeline_id,
        )
        await self.broadcast_to_pipeline(pipeline_id, message)
    
    def get_connection_count(self) -> int:
        """Get number of active connections."""
        return len(self.active_connections)
    
    def get_subscriber_count(self, pipeline_id: str) -> int:
        """Get number of subscribers for a pipeline."""
        return len(self.subscriptions.get(pipeline_id, set()))
    
    async def start_heartbeat(self, interval: float = DEFAULT_HEARTBEAT_INTERVAL) -> None:
        """Start heartbeat task to detect dead connections."""
        async def heartbeat_loop():
            while True:
                await asyncio.sleep(interval)
                
                # Snapshot connections under lock, then ping outside the lock.
                async with self._lock:
                    connection_ids = list(self.active_connections.keys())
                
                for connection_id in connection_ids:
                    try:
                        async with self._lock:
                            if connection_id not in self.active_connections:
                                continue
                            websocket = self.active_connections[connection_id]
                        await websocket.send_json({'type': 'ping'})
                    except Exception:
                        self.disconnect(connection_id)
        
        self._heartbeat_task = asyncio.create_task(heartbeat_loop())
    
    async def stop_heartbeat(self) -> None:
        """Stop heartbeat task."""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass


# ─────────────────────────────────────────────────────────────────────
# GLOBAL MANAGER
# ─────────────────────────────────────────────────────────────────────

_ws_manager: WebSocketManager | None = None


def get_websocket_manager() -> WebSocketManager:
    """Get or create WebSocket manager."""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager


# ─────────────────────────────────────────────────────────────────────
# FASTAPI WEBSOCKET ENDPOINT
# ─────────────────────────────────────────────────────────────────────

async def websocket_endpoint(
    websocket: WebSocket,
    pipeline_id: str | None = None,
):
    """
    WebSocket endpoint for real-time updates.
    
    Usage:
        ws://localhost:8000/ws
        ws://localhost:8000/ws?pipeline_id=xxx
    """
    manager = get_websocket_manager()
    
    # Generate connection ID
    import uuid
    connection_id = str(uuid.uuid4())
    
    # Get metadata from query params
    metadata = {
        'pipeline_id': pipeline_id,
        'user_agent': websocket.headers.get('user-agent', ''),
    }
    
    await manager.connect(websocket, connection_id, metadata)
    
    # Subscribe to pipeline if provided
    if pipeline_id:
        await manager.subscribe(connection_id, pipeline_id)
    
    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await handle_websocket_message(
                    manager, connection_id, message
                )
            except json.JSONDecodeError:
                await manager.send_to_connection(
                    connection_id,
                    WebSocketMessage(
                        type='error',
                        data={'error': 'Invalid JSON'},
                    ),
                )
    
    except WebSocketDisconnect:
        manager.disconnect(connection_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(connection_id)


async def handle_websocket_message(
    manager: WebSocketManager,
    connection_id: str,
    message: dict[str, Any],
) -> None:
    """Handle incoming WebSocket message."""
    msg_type = message.get('type')
    
    if msg_type == 'subscribe':
        pipeline_id = message.get('pipeline_id')
        if pipeline_id:
            await manager.subscribe(connection_id, pipeline_id)
            await manager.send_to_connection(
                connection_id,
                WebSocketMessage(
                    type='subscribed',
                    data={'pipeline_id': pipeline_id},
                ),
            )
    
    elif msg_type == 'unsubscribe':
        pipeline_id = message.get('pipeline_id')
        if pipeline_id:
            await manager.unsubscribe(connection_id, pipeline_id)
    
    elif msg_type == 'ping':
        await manager.send_to_connection(
            connection_id,
            WebSocketMessage(type='pong', data={}),
        )


# ─────────────────────────────────────────────────────────────────────
# EVENT BUS INTEGRATION
# ─────────────────────────────────────────────────────────────────────

async def setup_event_bus_integration() -> None:
    """Subscribe WebSocket manager to event bus."""
    from reasoner.application.event_bus import get_event_bus, handle_all_events
    from reasoner.core.events.domain_events import DomainEvent
    
    manager = get_websocket_manager()
    
    @handle_all_events()
    async def broadcast_to_websocket(event: DomainEvent):
        """Broadcast all events to WebSocket subscribers."""
        # Extract pipeline_id from event
        pipeline_id = event.aggregate_id
        
        # Convert event to dict
        event_data = {
            'event_type': event.event_type.value,
            'aggregate_id': event.aggregate_id,
            'version': event.version,
            'timestamp': event.timestamp,
        }
        
        # Add event-specific data
        from reasoner.core.events.domain_events import (
            PhaseCompleted, PhaseFailed, PipelineCompleted, PipelineFailed,
        )
        
        if isinstance(event, PhaseCompleted):
            event_data['phase'] = event.phase_name
            event_data['model_used'] = event.model_used
            event_data['tokens'] = event.tokens
        elif isinstance(event, PipelineCompleted):
            event_data['total_tokens'] = event.total_tokens
            event_data['duration'] = event.total_duration_seconds
        
        await manager.broadcast_event(event_data, pipeline_id)
