"""
Per-run cancellation state management for the ARA API.

Encapsulates the _run_cancel_events dict and _active_runs set,
using an asyncio.Lock for async-context safety.

.. note::
    RunStateStore is an in-process singleton. For horizontal scaling
    (multi-worker/multi-process), replace with a Redis-backed store
    or external pub/sub system.
"""

from __future__ import annotations

import asyncio


class RunStateStore:
    """
    Thread-safe / asyncio-safe store for per-run cancellation state.

    Encapsulates the cancel-event dict and active-run set,
    using an asyncio.Lock for async-context safety.
    """

    def __init__(self) -> None:
        self._cancel_events: dict[str, asyncio.Event] = {}
        self._active_runs: set[str] = set()
        self._lock = asyncio.Lock()

    async def add(self, run_id: str) -> asyncio.Event:
        """Register a new run and return its cancel event."""
        async with self._lock:
            event = asyncio.Event()
            self._cancel_events[run_id] = event
            self._active_runs.add(run_id)
            return event

    async def remove(self, run_id: str) -> None:
        """Clean up a run's state. Safe to call multiple times."""
        async with self._lock:
            self._active_runs.discard(run_id)
            self._cancel_events.pop(run_id, None)

    async def get_cancel_event(self, run_id: str) -> asyncio.Event | None:
        """Get the cancel event for a run, or None if not found."""
        async with self._lock:
            return self._cancel_events.get(run_id)

    async def request_cancel(self, run_id: str) -> bool:
        """
        Signal cancellation for a run.
        Returns True if the run was found and cancelled, False otherwise.
        """
        async with self._lock:
            event = self._cancel_events.get(run_id)
            if event is not None:
                event.set()
                return True
            return False

    async def request_cancel_all(self) -> list[str]:
        """
        Signal cancellation for all active runs.
        Returns the list of run_ids that were cancelled.
        """
        async with self._lock:
            targets = list(self._active_runs)
            for rid in targets:
                event = self._cancel_events.get(rid)
                if event is not None:
                    event.set()
            return targets

    def is_active(self, run_id: str) -> bool:
        """Check if a run is currently active (non-locking, best-effort)."""
        return run_id in self._active_runs

    @property
    def active_runs(self) -> set[str]:
        """Return a snapshot of active run IDs."""
        return set(self._active_runs)

    async def reset(self) -> None:
        """Clear all state (for test isolation)."""
        async with self._lock:
            for event in self._cancel_events.values():
                event.set()
            self._cancel_events.clear()
            self._active_runs.clear()


# Module-level singleton — shared across the API layer.
# For horizontal scaling, replace this with a Redis-backed store.
_run_store = RunStateStore()
