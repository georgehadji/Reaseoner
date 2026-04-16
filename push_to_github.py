#!/usr/bin/env python
"""
Push current changes to GitHub.

Usage:
  python push_to_github.py
  python push_to_github.py "feat: add timing tracking"
"""

import subprocess
import sys
from datetime import datetime


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, check=check)


def main() -> int:
    # Check for custom message
    custom_msg = sys.argv[1] if len(sys.argv) > 1 else None

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
    if custom_msg:
        msg = custom_msg
    else:
        msg = f"update: {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    run(["git", "commit", "-m", msg])

    # Push
    run(["git", "push", "origin", "HEAD"])

    print("\n✅ Pushed to GitHub successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
