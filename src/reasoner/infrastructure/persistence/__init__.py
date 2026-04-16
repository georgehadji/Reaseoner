"""
Infrastructure Persistence Package

Event storage and retrieval for event-sourced aggregates.
Supports SQLite (default) and PostgreSQL (production).
"""

from reasoner.infrastructure.persistence.event_store import (
    EventStore,
    get_event_store,
    reset_event_store,
)
from reasoner.infrastructure.persistence.postgres_store import (
    PostgreSQLEventStore,
    get_postgres_store,
    initialize_postgres_store,
)
from reasoner.infrastructure.persistence.snapshots import (
    SnapshotStrategy,
    SnapshotManager,
    ReadModelProjection,
    setup_read_model_projections,
)

__all__ = [
    # SQLite
    'EventStore',
    'get_event_store',
    'reset_event_store',
    # PostgreSQL
    'PostgreSQLEventStore',
    'get_postgres_store',
    'initialize_postgres_store',
    # Snapshots & CQRS
    'SnapshotStrategy',
    'SnapshotManager',
    'ReadModelProjection',
    'setup_read_model_projections',
]
