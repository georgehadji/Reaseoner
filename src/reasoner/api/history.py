from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

HISTORY_DIR = Path(__file__).parent.parent / "history"
HISTORY_DIR.mkdir(exist_ok=True)


class HistoryEntry(BaseModel):
    id: str
    problem: str
    preset: str
    method: str
    timestamp: str
    tokens: dict[str, int]
    status: str  # "completed", "error", "cancelled"


def _list_history() -> list[HistoryEntry]:
    """List all history entries, sorted by timestamp descending."""
    entries = []
    for f in HISTORY_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            entries.append(HistoryEntry(**data))
        except Exception:
            pass
    return sorted(entries, key=lambda x: x.timestamp, reverse=True)


def _save_history_entry(entry: HistoryEntry) -> None:
    """Save a history entry to disk."""
    path = HISTORY_DIR / f"{entry.id}.json"
    path.write_text(json.dumps(entry.model_dump(), ensure_ascii=False), encoding="utf-8")
