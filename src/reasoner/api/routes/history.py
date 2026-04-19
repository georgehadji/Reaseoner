"""Search history endpoints."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from reasoner.api.history import HISTORY_DIR, _list_history

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/history")
async def get_history(limit: int = 50, offset: int = 0):
    """Get search history."""
    all_history = _list_history()
    return {
        "total": len(all_history),
        "entries": all_history[offset : offset + limit],
    }


@router.get("/api/history/tagged")
async def get_tagged_history(tag: str, limit: int = 20):
    """Get history entries by tag (e.g. method:multi-perspective or preset:research-budget)."""
    from reasoner.core.memory import TaggedMemory

    tagged = TaggedMemory(HISTORY_DIR)
    entries = tagged.get_by_tag(tag, limit=limit)
    return {
        "tag": tag,
        "total": tagged.count(tag),
        "entries": entries,
    }


@router.get("/api/history/{entry_id}")
async def get_history_entry(entry_id: str):
    """Get a specific history entry."""
    safe_id = Path(entry_id).name
    path = HISTORY_DIR / f"{safe_id}.json"
    if not path.exists() or not str(path.resolve()).startswith(str(HISTORY_DIR.resolve())):
        raise HTTPException(status_code=404, detail="Entry not found")
    return json.loads(path.read_text(encoding="utf-8"))


@router.delete("/api/history/{entry_id}")
async def delete_history_entry(entry_id: str):
    """Delete a history entry."""
    safe_id = Path(entry_id).name
    path = HISTORY_DIR / f"{safe_id}.json"
    try:
        if not path.exists() or not str(path.resolve()).startswith(str(HISTORY_DIR.resolve())):
            raise HTTPException(status_code=404, detail="Entry not found")
        path.unlink(missing_ok=True)
        return {"status": "deleted"}
    except HTTPException:
        raise
    except OSError as e:
        logger.error(f"Failed to delete history entry {entry_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete entry")


@router.delete("/api/history")
async def clear_history():
    """Clear all history."""
    cleared = 0
    failed = 0
    for f in HISTORY_DIR.glob("*.json"):
        try:
            f.unlink(missing_ok=True)
            cleared += 1
        except OSError as e:
            logger.warning(f"Failed to delete history file {f}: {e}")
            failed += 1
    return {"cleared": cleared, "failed": failed}
