#!/usr/bin/env python
"""
Kill all Reasoner-related servers and the SearXNG container.

Usage:
  python kill_servers.py
  python kill_servers.py --force   # Skip graceful termination, kill immediately
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent.resolve()
SEARXNG_COMPOSE_FILE = REPO_ROOT / "docker-compose.searxng.yml"

TARGET_KEYWORDS = [
    "uvicorn",
    "reasoner.neuro.cli",
    "start_all.py",
    "api.py",
]

# Also kill frontend node processes that are inside our repo
FRONTEND_DIR_NAME = "ui-next"


def _stop_searxng() -> None:
    """Stop the SearXNG container via docker compose."""
    if not SEARXNG_COMPOSE_FILE.exists():
        print("[SKIP] SearXNG compose file not found.")
        return

    print("[STOP] SearXNG (docker compose down)")
    result = subprocess.run(
        ["docker", "compose", "-f", str(SEARXNG_COMPOSE_FILE), "down"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print("[OK]   SearXNG stopped.")
    else:
        # Already down or docker not running — not a fatal error
        err = (result.stderr or result.stdout or "").strip()
        if err:
            print(f"[WARN] docker compose down: {err}")
        else:
            print("[WARN] docker compose down returned non-zero.")


def _kill_processes(force: bool = False) -> int:
    """Find and terminate/kill Reasoner-related processes. Returns count."""
    try:
        import psutil
    except ImportError:
        print("[WARN] psutil not installed. Falling back to taskkill / pkill.")
        return _kill_processes_fallback(force)

    killed = 0
    for proc in psutil.process_iter(["pid", "name", "cmdline", "cwd"]):
        try:
            info = proc.info
            cmdline = info.get("cmdline") or []
            cmd_str = " ".join(cmdline).lower()
            name = (info.get("name") or "").lower()
            cwd = info.get("cwd")
            pid = info["pid"]

            # Avoid killing ourselves
            if pid == sys.modules["os"].getpid():
                continue

            is_target = False
            # Match by command-line keyword
            for kw in TARGET_KEYWORDS:
                if kw.lower() in cmd_str:
                    is_target = True
                    break

            # Match frontend node/npm running inside ui-next
            if not is_target and (name in ("node.exe", "node") or "npm" in name):
                if cwd and FRONTEND_DIR_NAME in Path(cwd).as_posix():
                    is_target = True

            # Extra safety: if cwd is inside REPO_ROOT, be more aggressive with matches
            in_repo = bool(cwd and Path(cwd).resolve() == REPO_ROOT)
            if in_repo and ("python" in name and "reasoner" in cmd_str):
                is_target = True

            if not is_target:
                continue

            label = " ".join(cmdline[:3]) if cmdline else name
            print(f"[KILL] {label} (PID {pid})")
            if force:
                proc.kill()
            else:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except psutil.TimeoutExpired:
                    print(f"[FORCE] {label} (PID {pid}) did not terminate in 5s — killing.")
                    proc.kill()
                    proc.wait(timeout=5)
            killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        except Exception as exc:
            print(f"[WARN] Error handling PID {info.get('pid', '?')}: {exc}")

    return killed


def _kill_processes_fallback(force: bool = False) -> int:
    """Fallback when psutil is missing."""
    import os
    killed = 0
    if sys.platform == "win32":
        for kw in TARGET_KEYWORDS:
            result = subprocess.run(
                ["taskkill", "/F" if force else "/T", "/IM", kw],
                capture_output=True,
            )
            if result.returncode == 0:
                killed += 1
        # Node fallback
        subprocess.run(["taskkill", "/F" if force else "/T", "/IM", "node.exe"], capture_output=True)
    else:
        for kw in TARGET_KEYWORDS:
            result = subprocess.run(["pkill", "-9" if force else "-15", "-f", kw], capture_output=True)
            if result.returncode == 0:
                killed += 1
        subprocess.run(["pkill", "-9" if force else "-15", "-f", "node"], capture_output=True)
    return killed


def main() -> int:
    parser = argparse.ArgumentParser(description="Kill all Reasoner servers")
    parser.add_argument("--force", action="store_true", help="Kill immediately without graceful termination")
    args = parser.parse_args()

    print("=" * 64)
    print("  Reasoner - Server Killer")
    print("=" * 64)
    print()

    _stop_searxng()
    print()

    killed = _kill_processes(force=args.force)
    if killed:
        print(f"[OK]   Terminated {killed} process(es).")
    else:
        print("[INFO] No matching Reasoner processes found.")

    print()
    print("[DONE] All done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
