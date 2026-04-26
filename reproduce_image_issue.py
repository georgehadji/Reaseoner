"""Reproduce script: image generation smoke test — skips without valid API key."""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, "src")


def main() -> int:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("SKIP: OPENROUTER_API_KEY not configured")
        return 0

    async def _test() -> int:
        try:
            from reasoner.infrastructure.llm.image_generation import generate_images
            result = await generate_images(
                "A futuristic city with flying cars and neon lights",
                preset="budget",
                enhance=False,
            )
            if result.get("success"):
                print("PASS: image generation returned success")
                return 0
            err = result.get("error", "unknown error")
            if "401" in str(err) or "User not found" in str(err):
                print(f"SKIP: invalid API key ({err})")
                return 0
            print(f"FAIL: {err}")
            return 1
        except Exception as exc:
            if "401" in str(exc) or "User not found" in str(exc):
                print(f"SKIP: invalid API key ({exc})")
                return 0
            print(f"FAIL: {exc}")
            return 1

    return asyncio.run(_test())


if __name__ == "__main__":
    sys.exit(main())
