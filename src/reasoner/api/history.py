from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

HISTORY_DIR = Path(__file__).parent.parent / "history"
HISTORY_DIR.mkdir(exist_ok=True)

_PIPELINE_OWNERS_PATH = HISTORY_DIR / "pipeline_owners.json"


def _get_pipeline_owner(pipeline_id: str) -> str | None:
    """Return the user_id that owns *pipeline_id*, or None if not tracked."""
    if not _PIPELINE_OWNERS_PATH.exists():
        return None
    try:
        mapping = json.loads(_PIPELINE_OWNERS_PATH.read_text(encoding="utf-8"))
        return mapping.get(pipeline_id)
    except Exception:
        return None


def _save_pipeline_owner(pipeline_id: str, user_id: str | None) -> None:
    """Persist ownership mapping for a pipeline run."""
    mapping: dict[str, str | None] = {}
    if _PIPELINE_OWNERS_PATH.exists():
        try:
            mapping = json.loads(_PIPELINE_OWNERS_PATH.read_text(encoding="utf-8"))
        except Exception:
            mapping = {}
    mapping[pipeline_id] = user_id
    _PIPELINE_OWNERS_PATH.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")


class HistoryEntry(BaseModel):
    id: str
    user_id: str | None = None
    problem: str
    preset: str
    method: str
    timestamp: str
    tokens: dict[str, int]
    status: str  # "completed", "error", "cancelled"


def _list_history(
    user_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[HistoryEntry], int]:
    """List history entries, sorted by timestamp descending.

    If user_id is provided, only entries belonging to that user are returned.
    Returns (entries, total_count) for client-side pagination.
    """
    entries = []
    for f in HISTORY_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            entry = HistoryEntry(**data)
            if user_id is not None and entry.user_id != user_id:
                continue
            entries.append(entry)
        except Exception:
            pass

    entries = sorted(entries, key=lambda x: x.timestamp, reverse=True)
    total = len(entries)
    return entries[offset:offset + limit], total


def _save_history_entry(entry: HistoryEntry) -> None:
    """Save a history entry to disk."""
    path = HISTORY_DIR / f"{entry.id}.json"
    path.write_text(json.dumps(entry.model_dump(), ensure_ascii=False), encoding="utf-8")
