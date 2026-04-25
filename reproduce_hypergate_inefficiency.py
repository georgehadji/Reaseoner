
import re
import asyncio
from unittest.mock import MagicMock

# Mocking enough to run the logic from hyperagent.py
_CREATIVE_PATTERNS = [
    re.compile(r"\b(write|compose|draft|create)\s+(me\s+)?(an?\s+)?(poem|story|narrative|letter|speech|script)\b", re.I),
    re.compile(r"\b(tell\s+me\s+a\s+story|make\s+up\s+a\s+story|write\s+me\s+a\s+poem)\b", re.I),
]

_RESEARCH_INDICATORS = [
    re.compile(r"\b(research\s+(article|paper|essay)|informative\s+(article|essay)|academic\s+(article|essay))\b", re.I),
    re.compile(r"\b(with\s+(sources|citations|references)|based\s+on\s+(sources|research|data))\b", re.I),
    re.compile(r"\b(about|on|regarding|concerning|explaining|analyzing)\s+\w{4,}\b", re.I),
]

def _is_creative_writing(problem: str) -> bool:
    if not any(p.search(problem) for p in _CREATIVE_PATTERNS):
        return False
    if any(p.search(problem) for p in _RESEARCH_INDICATORS):
        return False
    return True

def test_repro():
    prompts = [
        ("Write a poem about cats", False), # Expected True (it's pure creative), but returns False
        ("Write a story about a brave knight", False), # Expected True, but returns False
        ("Write an article about climate change", False), # Expected False (it IS research-backed)
        ("Write a poem", True), # Expected True
    ]
    
    for prompt, expected in prompts:
        actual = _is_creative_writing(prompt)
        print(f"Prompt: '{prompt}' | Expected: {expected} | Actual: {actual} | {'PASS' if actual == expected else 'FAIL'}")

if __name__ == "__main__":
    test_repro()
