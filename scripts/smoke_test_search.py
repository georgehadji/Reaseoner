#!/usr/bin/env python3
"""
Manual smoke tests for search quality (TODO.md §13).

Run this when SearXNG is available:
    python scripts/smoke_test_search.py

Requires:
    - SearXNG running at the URL configured in settings.SEARXNG_URL
    - PYTHONPATH includes src/
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from reasoner.core.search import smart_search, _should_include_result
from reasoner.core.settings import settings


# ═════════════════════════════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════════════════════════════

async def check_searxng_health() -> bool:
    import httpx
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(settings.SEARXNG_URL)
            return r.status_code == 200
    except Exception as exc:
        print(f"[HEALTH CHECK] SearXNG at {settings.SEARXNG_URL} is unreachable: {exc}")
        return False


def analyze_results(query: str, results: list[dict]) -> dict:
    """Analyze search results and return a quality report."""
    report = {
        "query": query,
        "total_raw": len(results),
        "passed_filtering": 0,
        "rejected": [],
        "top_domains": [],
        "has_academic_sources": False,
        "has_garbage_sources": False,
    }

    academic_domains = {"arxiv.org", "scholar.google", "pubmed", "semanticscholar.org", "crossref.org", "ieee.org", "acm.org", "sciencedirect.com", "nature.com", "researchgate.net"}
    garbage_domains = {"biography.com", "wordreference.com", "reddit.com", "imdb.com", "facebook.com", "pinterest.com", "twitter.com", "x.com"}

    for r in results:
        url = r.get("url", "")
        domain = url.split("/")[2] if "/" in url else ""
        if _should_include_result(r):
            report["passed_filtering"] += 1
            report["top_domains"].append(domain)
            if any(ad in domain for ad in academic_domains):
                report["has_academic_sources"] = True
        else:
            report["rejected"].append({"url": url, "title": r.get("title", "")[:60]})

        if any(gd in domain for gd in garbage_domains):
            report["has_garbage_sources"] = True

    # Deduplicate domains
    report["top_domains"] = list(dict.fromkeys(report["top_domains"]))[:10]
    return report


# ═════════════════════════════════════════════════════════════════════
# Test 1 — Orthodox-Informed Wellbeing & Habits Coach
# ═════════════════════════════════════════════════════════════════════

async def test_orthodox_wellbeing() -> dict:
    """
    Query the Orthodox wellbeing niche and verify Deep Read gets 0 garbage sources.
    """
    query = (
        "Orthodox-Informed Wellbeing & Habits Coach\n\n"
        "Τι λες για αυτό το niche;\n\n"
        "Πως σου φαίνεται;"
    )
    print(f"\n{'='*60}")
    print("TEST 1: Orthodox-Informed Wellbeing & Habits Coach")
    print(f"{'='*60}")
    print(f"Query (truncated): {query[:80]}...")

    results = await smart_search(query, source_type="general", num_results=15)
    report = analyze_results(query, results)

    print(f"Raw results returned: {report['total_raw']}")
    print(f"Results after filtering: {report['passed_filtering']}")
    print(f"Top domains: {report['top_domains']}")
    print(f"Garbage sources present: {report['has_garbage_sources']}")
    if report["rejected"]:
        print(f"Rejected ({len(report['rejected'])}):")
        for r in report["rejected"][:5]:
            print(f"  - {r['url']}")

    # Assertion
    if report["has_garbage_sources"]:
        print("\n[FAIL] Garbage sources found — off-topic filters may be too loose.")
    else:
        print("\n[PASS] No garbage sources detected.")

    return report


# ═════════════════════════════════════════════════════════════════════
# Test 2 — Scientific method for hypothesis testing
# ═════════════════════════════════════════════════════════════════════

async def test_scientific_method() -> dict:
    """
    Query scientific method and verify relevant academic sources are still found.
    """
    query = "Scientific method for hypothesis testing"
    print(f"\n{'='*60}")
    print("TEST 2: Scientific method for hypothesis testing")
    print(f"{'='*60}")
    print(f"Query: {query}")

    results = await smart_search(query, source_type="general", num_results=15)
    report = analyze_results(query, results)

    print(f"Raw results returned: {report['total_raw']}")
    print(f"Results after filtering: {report['passed_filtering']}")
    print(f"Top domains: {report['top_domains']}")
    print(f"Academic sources present: {report['has_academic_sources']}")
    if report["rejected"]:
        print(f"Rejected ({len(report['rejected'])}):")
        for r in report["rejected"][:5]:
            print(f"  - {r['url']}")

    # Assertion
    if report["has_academic_sources"]:
        print("\n[PASS] Academic sources found.")
    else:
        print("\n[FAIL] No academic sources found — regression in search quality.")

    return report


# ═════════════════════════════════════════════════════════════════════
# Main
# ═════════════════════════════════════════════════════════════════════

async def main() -> int:
    print("Search Quality Smoke Tests")
    print(f"SearXNG endpoint: {settings.SEARXNG_URL}")

    if not await check_searxng_health():
        print("\n[ABORT] SearXNG is not healthy. Cannot run smoke tests.")
        print("Start SearXNG with:")
        print("  docker compose -f docker-compose.searxng.yml up -d")
        return 1

    r1 = await test_orthodox_wellbeing()
    r2 = await test_scientific_method()

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Test 1 (Orthodox wellbeing) — garbage sources: {r1['has_garbage_sources']} (want False)")
    print(f"Test 2 (Scientific method)  — academic sources: {r2['has_academic_sources']} (want True)")

    if not r1["has_garbage_sources"] and r2["has_academic_sources"]:
        print("\n[ALL PASS]")
        return 0
    else:
        print("\n[SOME FAILURES]")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
