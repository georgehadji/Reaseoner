#!/usr/bin/env python
"""
Smart GitHub push script with runtime artifact filtering.

Usage:
  python push_to_github.py                    # Push source code only
  python push_to_github.py "feat: X"          # Custom commit message
  python push_to_github.py --all              # Include runtime artifacts
  python push_to_github.py --dry-run          # Preview only
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime

# Patterns considered runtime artifacts (not committed by default)
RUNTIME_PATTERNS = [
    re.compile(r"^cache/"),
    re.compile(r"^src/reasoner/cache/"),
    re.compile(r"^src/reasoner/history/"),
    re.compile(r"^src/reasoner/infrastructure/.*\.db$"),
    re.compile(r"^src/reasoner/feedback\.db$"),
    re.compile(r"^src/reasoner/\.upload_hash_index\.json$"),
    re.compile(r"^src/reasoner/history/pipeline_owners\.json$"),
    re.compile(r"^\.?claude/worktrees/"),
    re.compile(r"^\.tmp_"),
    re.compile(r"^tmp[a-z0-9]+/"),
    re.compile(r"^.*\.pyc$"),
    re.compile(r"^__pycache__/"),
    re.compile(r"^\.mypy_cache/"),
    re.compile(r"^\.pytest_cache/"),
    re.compile(r"^\.ruff_cache/"),
    re.compile(r"^node_modules/"),
    re.compile(r"^\.tmp_pytest/"),
    re.compile(r"^\.tmp_base/"),
    re.compile(r"^\.tmp_base2/"),
    re.compile(r"^\.tmp_manual_temp/"),
    re.compile(r"^\.reports/"),
    re.compile(r"^Humanizer/"),
    re.compile(r"^meta-orchestration-assessment\.md$"),
]

# Terminal colors
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


def color(text: str, code: str) -> str:
    return f"{code}{text}{RESET}" if sys.stdout.isatty() else text


def run(cmd: list[str], check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, check=check, capture_output=capture, text=True)


def unlock_git_index() -> None:
    """Remove stale git index.lock if present."""
    lock_file = ".git/index.lock"
    if os.path.exists(lock_file):
        try:
            os.remove(lock_file)
            print(color("[INFO] Removed stale .git/index.lock", YELLOW))
        except OSError as exc:
            print(color(f"[WARN] Could not remove {lock_file}: {exc}", YELLOW))


def is_runtime_artifact(path: str) -> bool:
    """Check if a file path matches runtime artifact patterns."""
    for pattern in RUNTIME_PATTERNS:
        if pattern.search(path):
            return True
    return False


def parse_status() -> tuple[list[str], list[str]]:
    """Parse git status --porcelain and split into source vs runtime files."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    )
    source_files: list[str] = []
    runtime_files: list[str] = []

    for raw_line in result.stdout.split("\n"):
        line = raw_line.rstrip("\r\n")
        if not line or len(line) < 4:
            continue
        # Format: "XY path" or "XY path -> new_path" (always exactly 2 status chars + space)
        status = line[:2]
        rest = line[3:]
        # Handle renames
        if " -> " in rest:
            path = rest.split(" -> ")[-1]
        else:
            path = rest
        path = path.strip()
        if not path:
            continue

        if is_runtime_artifact(path):
            runtime_files.append(f"{status}\t{path}")
        else:
            source_files.append(f"{status}\t{path}")

    return source_files, runtime_files


def get_current_branch() -> str:
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Smart GitHub push with artifact filtering")
    parser.add_argument("message", nargs="?", help="Custom commit message")
    parser.add_argument("--all", action="store_true", help="Include runtime artifacts in commit")
    parser.add_argument("--dry-run", action="store_true", help="Preview what would be committed")
    args = parser.parse_args()

    unlock_git_index()

    branch = get_current_branch()
    print(color(f"Branch: {branch}", CYAN))
    if branch not in ("main", "master"):
        print(color(f"[WARN] You are on '{branch}', not main/master.", YELLOW))
        if not args.dry_run:
            response = input("Continue anyway? [y/N]: ").strip().lower()
            if response not in ("y", "yes"):
                print("Aborted.")
                return 0

    source_files, runtime_files = parse_status()
    all_files = source_files + runtime_files

    if not all_files:
        print(color("Nothing to commit. Working tree clean.", GREEN))
        return 0

    # Display categorized status
    print()
    def _fmt(entry: str) -> str:
        parts = entry.split("\t", 1)
        return f"{parts[0]} {parts[1]}" if len(parts) == 2 else entry

    if source_files:
        print(color(f"Source code files ({len(source_files)}):", BOLD + GREEN))
        for f in source_files:
            print(f"  {color(_fmt(f), GREEN)}")

    if runtime_files:
        skip_msg = " (skipped — use --all to include)" if not args.all else " (included via --all)"
        print(color(f"Runtime artifacts ({len(runtime_files)}){skip_msg}:", BOLD + YELLOW))
        for f in runtime_files:
            print(f"  {color(_fmt(f), YELLOW)}")

    files_to_commit = all_files if args.all else source_files

    if not files_to_commit:
        print(color("\nNo source code changes to commit.", YELLOW))
        if runtime_files:
            print(f"{len(runtime_files)} runtime artifact(s) ignored.")
        return 0

    if args.dry_run:
        print(color(f"\n[DRY-RUN] Would commit {len(files_to_commit)} file(s).", CYAN))
        return 0

    # Stage only the files we want
    print()
    for line in files_to_commit:
        # Entries are stored as "XY\tpath" — split on tab to get the clean path
        path = line.split("\t", 1)[-1].strip()
        if not path:
            continue
        try:
            run(["git", "add", "--", path])
        except subprocess.CalledProcessError as exc:
            print(color(f"[WARN] Could not stage '{path}': {exc}", YELLOW))

    # Commit message
    msg = args.message if args.message else f"update: {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    run(["git", "commit", "-m", msg])
    run(["git", "push", "origin", "HEAD"])

    print(color("\n[OK] Pushed to GitHub successfully!", GREEN))
    return 0


if __name__ == "__main__":
    sys.exit(main())
