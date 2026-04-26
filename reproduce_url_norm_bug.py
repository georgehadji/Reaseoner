"""Reproduce script: URL normalization trailing-slash bug — now fixed."""
from __future__ import annotations

import sys

sys.path.insert(0, "src")

from reasoner.core.search import _normalize_url


def test_norm() -> bool:
    test_cases = [
        ("https://example.com/path/", "https://example.com/path"),
        ("https://example.com/path/?a=1", "https://example.com/path?a=1"),
    ]

    all_pass = True
    for u1, u2 in test_cases:
        n1 = _normalize_url(u1)
        n2 = _normalize_url(u2)
        equal = n1 == n2
        status = "PASS" if equal else "FAIL"
        if not equal:
            all_pass = False
        print(f"URL 1: {u1} -> {n1}")
        print(f"URL 2: {u2} -> {n2}")
        print(f"Equal: {equal} | {status}")

    return all_pass


if __name__ == "__main__":
    ok = test_norm()
    sys.exit(0 if ok else 1)
