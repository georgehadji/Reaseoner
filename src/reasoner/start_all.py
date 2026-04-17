#!/usr/bin/env python
"""
Start all Reasoner servers.

By default starts:
  - Main API server      : http://localhost:8001
  - Neuro memory server  : http://localhost:50001

Usage:
  python start_all.py
  python start_all.py --no-neuro    # Skip standalone neuro server
  python start_all.py --check       # Run pre-flight checks first
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

from reasoner.core.settings import settings
from reasoner.core.constants import DEFAULT_SEARXNG_URL

# ─────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
MAIN_SERVER_CMD = [sys.executable, "-m", "uvicorn", "asgi:app", "--host", "0.0.0.0", "--port", "8000"]
NEURO_SERVER_CMD = [sys.executable, "-m", "reasoner.neuro.cli", "start"]
FRONTEND_DIR = REPO_ROOT / "ui-next"
FRONTEND_CMD = ["npm", "run", "dev"]
SEARXNG_COMPOSE_FILE = REPO_ROOT / "docker-compose.searxng.yml"
SEARXNG_URL = settings.SEARXNG_URL.rstrip("/")

# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

def print_banner():
    print("=" * 64)
    print("  Reasoner - AI Reasoning Platform")
    print("  Server Orchestrator")
    print("=" * 64)
    print()


def run_preflight_checks() -> bool:
    """Run server_check.py and return True if all passed."""
    print("Running pre-flight checks...")
    result = subprocess.run([sys.executable, str(REPO_ROOT / "src" / "reasoner" / "server_check.py")], cwd=REPO_ROOT)
    print()
    return result.returncode == 0


def spawn_process(
    name: str,
    cmd: list[str] | str,
    env: dict | None = None,
    cwd: Path | None = None,
    shell: bool = False,
) -> subprocess.Popen:
    """Start a subprocess and return the handle."""
    print(f"[START] {name}")
    print(f"        {cmd if isinstance(cmd, str) else ' '.join(cmd)}")
    process_env = {**os.environ, **(env or {})}
    work_dir = cwd or REPO_ROOT
    # Windows: use creationflags to allow clean termination
    kwargs: dict = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    if shell:
        kwargs["shell"] = True
    proc = subprocess.Popen(cmd, cwd=str(work_dir), env=process_env, **kwargs)
    return proc


def _searxng_is_healthy() -> bool:
    """Check if SearXNG is already responding."""
    import urllib.request
    try:
        urllib.request.urlopen(f"{SEARXNG_URL}/healthz", timeout=3)
        return True
    except Exception:
        pass
    try:
        urllib.request.urlopen(f"{SEARXNG_URL}/", timeout=3)
        return True
    except Exception:
        return False


def _docker_available() -> bool:
    """Check if docker compose CLI is available."""
    return shutil.which("docker") is not None


def _start_searxng() -> bool:
    """Start SearXNG via docker compose. Returns True on success."""
    if not SEARXNG_COMPOSE_FILE.exists():
        print(f"[WARN] SearXNG compose file not found at {SEARXNG_COMPOSE_FILE}")
        return False
    cmd = [
        "docker", "compose",
        "-f", str(SEARXNG_COMPOSE_FILE),
        "up", "-d", "--wait",
    ]
    print(f"[START] SearXNG via Docker Compose ({SEARXNG_URL})")
    result = subprocess.run(cmd, cwd=str(REPO_ROOT))
    if result.returncode != 0:
        print("[WARN] Failed to start SearXNG container.")
        return False
    # Poll health endpoint
    for _ in range(30):
        if _searxng_is_healthy():
            print("[OK]    SearXNG is healthy")
            return True
        time.sleep(1)
    print("[WARN] SearXNG container started but health check timed out.")
    return False


def _stop_searxng() -> None:
    """Stop the SearXNG container if we started it."""
    if not SEARXNG_COMPOSE_FILE.exists():
        return
    cmd = [
        "docker", "compose",
        "-f", str(SEARXNG_COMPOSE_FILE),
        "down",
    ]
    print("[STOP]  SearXNG (docker compose down)")
    subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True)


def shutdown_process(name: str, proc: subprocess.Popen):
    """Gracefully terminate a subprocess."""
    if proc.poll() is not None:
        return
    print(f"[STOP]  {name} (PID {proc.pid})")
    try:
        if sys.platform == "win32" and not getattr(proc, "_reasoner_shell", False):
            proc.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
        proc.wait()


def main() -> int:
    parser = argparse.ArgumentParser(description="Start all Reasoner servers")
    parser.add_argument("--no-neuro", action="store_true", help="Skip the standalone neuro server")
    parser.add_argument("--no-frontend", action="store_true", help="Skip the Next.js frontend dev server")
    parser.add_argument("--no-searxng", action="store_true", help="Skip auto-starting SearXNG")
    parser.add_argument("--check", action="store_true", help="Run pre-flight checks before starting")
    parser.add_argument("--main-port", type=int, default=8001, help="Port for the main API server")
    parser.add_argument("--neuro-port", type=int, default=50001, help="Port for the standalone neuro server")
    parser.add_argument("--frontend-port", type=int, default=3000, help="Port for the Next.js frontend dev server")
    args = parser.parse_args()

    print_banner()

    if args.check:
        if not run_preflight_checks():
            print("Pre-flight checks failed. Aborting.")
            return 1

    processes: list[tuple[str, subprocess.Popen]] = []
    searxng_started_by_us = False

    try:
        # ── SearXNG ──────────────────────────────────────────────────
        if not args.no_searxng:
            if _searxng_is_healthy():
                print(f"[OK]    SearXNG already running at {SEARXNG_URL}")
            elif _docker_available():
                searxng_started_by_us = _start_searxng()
                if not searxng_started_by_us:
                    print("[WARN]  SearXNG unavailable. Web search will return empty results.")
            else:
                print("[WARN]  Docker not found. SearXNG cannot be auto-started.")
                print("        Install Docker or start SearXNG manually on port 8888.")

        # Start Next.js frontend dev server first (it takes longest to boot)
        if not args.no_frontend:
            if not (FRONTEND_DIR / "package.json").exists():
                print(f"[WARN] Frontend directory not found at {FRONTEND_DIR}, skipping.")
            elif shutil.which("npm") is None:
                print("[WARN] npm not found in PATH, skipping frontend start.")
            else:
                frontend_env = {
                    **os.environ,
                    "PORT": str(args.frontend_port),
                    "NEXT_PUBLIC_API_BASE": f"http://localhost:{args.main_port}",
                }
                # On Windows npm is a .cmd file and needs shell=True to be found by CreateProcess
                frontend_shell = sys.platform == "win32"
                frontend_cmd = " ".join(FRONTEND_CMD) if frontend_shell else FRONTEND_CMD.copy()
                frontend_proc = spawn_process(
                    "Next.js Frontend",
                    frontend_cmd,
                    env=frontend_env,
                    cwd=FRONTEND_DIR,
                    shell=frontend_shell,
                )
                # Tag the process so shutdown can use kill() if shell=True prevents clean CTRL_BREAK
                if frontend_shell:
                    frontend_proc._reasoner_shell = True  # type: ignore[attr-defined]
                processes.append(("Next.js Frontend", frontend_proc))
                time.sleep(3)

        # Start main API server
        main_cmd = MAIN_SERVER_CMD.copy()
        if "--port" in main_cmd:
            main_cmd[main_cmd.index("--port") + 1] = str(args.main_port)
        main_proc = spawn_process("Main API Server", main_cmd)
        processes.append(("Main API Server", main_proc))

        # Give the main server a moment to bind
        time.sleep(1)

        # Start standalone neuro server if requested
        if not args.no_neuro:
            neuro_cmd = NEURO_SERVER_CMD.copy()
            neuro_cmd.extend(["--port", str(args.neuro_port)])
            neuro_env = {
                **os.environ,
                "PYTHONPATH": str(REPO_ROOT / "src"),
            }
            neuro_proc = spawn_process("Neuro Server", neuro_cmd, env=neuro_env)
            processes.append(("Neuro Server", neuro_proc))
            time.sleep(1)

        print()
        print("-" * 64)
        print("  Servers started successfully!")
        print()
        print(f"  Main API:     http://localhost:{args.main_port}")
        print(f"  API Docs:     http://localhost:{args.main_port}/docs")
        print(f"  WebSocket:    ws://localhost:{args.main_port}/ws")
        if not args.no_frontend:
            print(f"  Frontend:     http://localhost:{args.frontend_port}")
        if not args.no_neuro:
            print(f"  Neuro API:    http://localhost:{args.neuro_port}/neuro/health")
        print(f"  SearXNG:      {SEARXNG_URL}")
        print()
        print("  Press Ctrl+C to stop all servers")
        print("-" * 64)
        print()

        # Wait for all processes
        while True:
            for name, proc in processes:
                ret = proc.poll()
                if ret is not None:
                    print(f"[EXIT] {name} exited with code {ret}")
                    # If one dies, shut down the rest
                    raise SystemExit(ret or 0)
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n[INTERRUPT] Shutting down servers...")
    finally:
        for name, proc in processes:
            shutdown_process(name, proc)
        if searxng_started_by_us:
            _stop_searxng()
        print("[DONE] All servers stopped.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
