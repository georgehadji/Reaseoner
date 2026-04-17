from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# In-memory hot-cache layer to avoid disk I/O on repeated identical requests
_MEMORY_CACHE: dict[str, list[dict]] = {}
_MEMORY_CACHE_MAX_SIZE = 256


def _prune_memory_cache() -> None:
    """Simple FIFO eviction for the in-memory cache."""
    # Back-compat: allow monkey-patching from importing modules (e.g. tests)
    max_size = _MEMORY_CACHE_MAX_SIZE
    try:
        import reasoner.api as _api
        max_size = getattr(_api, '_MEMORY_CACHE_MAX_SIZE', max_size)
    except Exception:
        pass
    excess = len(_MEMORY_CACHE) - max_size
    if excess > 0:
        for _ in range(excess):
            _MEMORY_CACHE.pop(next(iter(_MEMORY_CACHE)), None)


def _cache_key(req: "RunRequest") -> str:
    # v=3 invalidates old caches after GateAgent introduction
    payload = json.dumps({
        "problem": req.problem,
        "preset":  req.preset,
        "top_k":   req.top_k,
        "routing": req.routing,
        "force_pipeline": req.force_pipeline,
        "v": 3,
    }, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def _load_cache(key: str) -> list[dict] | None:
    # 1. Check in-memory hot cache first
    if key in _MEMORY_CACHE:
        return _MEMORY_CACHE[key]

    # 2. Fall back to disk
    path = CACHE_DIR / f"{key}.json"
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            _MEMORY_CACHE[key] = data
            _prune_memory_cache()
            return data
        except (json.JSONDecodeError, OSError):
            # Treat a corrupt or unreadable cache file as a cache miss and
            # remove it so the next run can write a clean file.
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
    return None


_MAX_CACHE_FILES: int = 1000


def _prune_disk_cache() -> None:
    """Remove oldest cache files if the directory exceeds the max size."""
    files = sorted(CACHE_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime)
    excess = len(files) - _MAX_CACHE_FILES
    for f in files[:excess]:
        try:
            f.unlink(missing_ok=True)
        except OSError:
            pass


def _save_cache(key: str, events: list[dict]) -> None:
    # Update in-memory hot cache immediately
    _MEMORY_CACHE[key] = events.copy()
    _prune_memory_cache()

    # Write to a sibling temp file then rename so that a crash during the
    # write never leaves a corrupt (partial) JSON file at the target path.
    # FIX BUG-007: Use unique temp filename per writer to prevent race conditions
    # on Windows where os.replace() is not atomic. Include PID and timestamp for uniqueness.
    path = CACHE_DIR / f"{key}.json"
    # Unique temp file: key.{pid}.{timestamp}.tmp
    tmp = CACHE_DIR / f"{key}.{os.getpid()}.{int(time.time() * 1000)}.tmp"
    try:
        tmp.write_text(json.dumps(events), encoding="utf-8")
        # On Windows, os.replace() may not be atomic, but with unique temp filenames
        # we avoid overwriting another writer's temp file. The last writer wins,
        # but data is never corrupted from interleaved writes.
        tmp.replace(path)
        # Clean up any old temp files for this key (from crashed writers)
        for old_tmp in CACHE_DIR.glob(f"{key}.*.tmp"):
            try:
                old_tmp.unlink(missing_ok=True)
            except OSError:
                pass
        _prune_disk_cache()
    except OSError:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
