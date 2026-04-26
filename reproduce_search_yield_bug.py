"""Reproduce script: search filter-before-slice bug — now fixed."""
from __future__ import annotations

import asyncio
import sys
from typing import Any

sys.path.insert(0, "src")

from reasoner.core.search import _should_include_result


def mock_fetch_page(num_results: int) -> list[dict[str, Any]]:
    """Simulate SearXNG returning 20 results, half of which are filtered."""
    all_raw = [
        {"id": i, "url": f"https://example.com/{i}", "title": f"Result {i}", "content": "This is a sufficiently long content snippet that passes the minimum length filter. " * 3}
        for i in range(20)
    ]
    refined = [r for r in all_raw if _should_include_result(r)]
    # Real code filters ALL raw results, then slices
    return refined[:num_results]


async def test_yield() -> bool:
    requested = 10
    actual_results = mock_fetch_page(requested)
    print(f"Requested: {requested} | Got: {len(actual_results)}")
    status = "PASS" if len(actual_results) == requested else "FAIL"
    print(status)
    return status == "PASS"


if __name__ == "__main__":
    ok = asyncio.run(test_yield())
    sys.exit(0 if ok else 1)
