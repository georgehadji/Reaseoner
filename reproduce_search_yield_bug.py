
import asyncio
from typing import Any

def _should_include_result(result: dict[str, Any]) -> bool:
    # Simulate filtering out every other result
    return result.get("id", 0) % 2 == 0

async def mock_fetch_page(num_results: int):
    # Simulate SearXNG returning 20 results
    all_raw = [{"id": i, "url": f"https://ex.com/{i}"} for i in range(20)]
    
    # Current buggy implementation:
    raw = all_raw[:num_results]
    refined = [r for r in raw if _should_include_result(r)]
    return refined

async def test_yield():
    requested = 10
    actual_results = await mock_fetch_page(requested)
    print(f"Requested: {requested} | Got: {len(actual_results)}")
    print(f"{'PASS' if len(actual_results) == requested else 'FAIL'}")

if __name__ == "__main__":
    asyncio.run(test_yield())
