"""Reproduce script: Discovery client singleton URL bug — now fixed."""
from __future__ import annotations

import asyncio
import sys

sys.path.insert(0, "src")

from reasoner.core.search import get_discovery_client, reset_discovery_client


async def test_client() -> None:
    reset_discovery_client()
    c1, _ = await get_discovery_client("http://A")
    print(f"Client 1 URL: {c1.base_url}")

    c2, _ = await get_discovery_client("http://B")
    print(f"Client 2 URL: {c2.base_url}")

    status = "PASS" if c2.base_url == "http://B" else "FAIL"
    print(status)
    return status == "PASS"


if __name__ == "__main__":
    ok = asyncio.run(test_client())
    sys.exit(0 if ok else 1)
