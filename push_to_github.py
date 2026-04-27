#!/usr/bin/env python
"""
Push current changes to GitHub.

Usage:
  python push_to_github.py
  python push_to_github.py "feat: add timing tracking"
"""

import os
import subprocess
import sys
from datetime import datetime


def run(cmd: list[str], check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, check=check, capture_output=capture, text=True)


def unlock_git_index() -> None:
    """Remove stale git index.lock if present."""
    lock_file = ".git/index.lock"
    if os.path.exists(lock_file):
        try:
            os.remove(lock_file)
            print("[INFO] Removed stale .git/index.lock")
        except OSError as exc:
            print(f"[WARN] Could not remove {lock_file}: {exc}")


def main() -> int:
    custom_msg = sys.argv[1] if len(sys.argv) > 1 else None

    unlock_git_index()

    # Show status
    run(["git", "status", "--short"], check=False)
    print()

    # Check if there are changes
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    )
    if not result.stdout.strip():
        print("Nothing to commit. Working tree clean.")
        return 0

    # Stage all
    run(["git", "add", "-A"])

    # Commit message
    msg = custom_msg if custom_msg else f"update: {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    run(["git", "commit", "-m", msg])

    # Push
    run(["git", "push", "origin", "HEAD"])

    print("\n[OK] Pushed to GitHub successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
