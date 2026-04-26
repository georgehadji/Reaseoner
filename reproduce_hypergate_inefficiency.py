"""Reproduce script: HyperGate creative-writing regex bug — now fixed."""
from __future__ import annotations

import sys

sys.path.insert(0, "src")

from reasoner.hypergate.hyperagent import _is_creative_writing


def test_repro() -> bool:
    prompts = [
        ("Write a poem about cats", True),
        ("Write a story about a brave knight", True),
        ("Write an article about climate change", False),
        ("Write a poem", True),
    ]

    all_pass = True
    for prompt, expected in prompts:
        actual = _is_creative_writing(prompt)
        status = "PASS" if actual == expected else "FAIL"
        if status == "FAIL":
            all_pass = False
        print(f"Prompt: '{prompt}' | Expected: {expected} | Actual: {actual} | {status}")

    return all_pass


if __name__ == "__main__":
    ok = test_repro()
    sys.exit(0 if ok else 1)
