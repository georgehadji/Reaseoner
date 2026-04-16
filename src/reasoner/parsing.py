"""
ARA Pipeline - Response Parsing Utilities
Robust JSON extraction from LLM responses.
"""

from __future__ import annotations

import json
import re
from typing import Any


class ParseError(Exception):
    """Raised when LLM response cannot be parsed into expected structure."""


def strip_perplexity_citations(text: str) -> str:
    """Remove Perplexity-style citation markers and source sections."""
    text = re.sub(r"\s*\[\d+\]", "", text)
    for header in ("Sources:", "Citations:"):
        idx = text.find(header)
        if idx != -1:
            text = text[:idx].rstrip()
    return text


def strip_prose_preamble(text: str) -> str:
    """Remove leading prose before the first JSON object or array."""
    start = min(
        (text.find("{"), text.find("[")),
        default=-1,
        key=lambda x: float("inf") if x == -1 else x,
    )
    return text[start:] if start != -1 else text


def extract_json(text: str) -> dict[str, Any]:
    """
    Extract JSON from LLM response. Handles:
    - Clean JSON
    - JSON wrapped in outer markdown fences (stripped safely)
    - JSON with leading/trailing prose
    - Trailing commas
    - Truncated JSON (token limit cut-off)
    
    Security: Input length limited to prevent ReDoS attacks.
    """
    # CRITICAL: Limit input length to prevent regex DoS (ReDoS) attacks
    # Regex patterns below can exhibit catastrophic backtracking on malicious input
    MAX_INPUT_LENGTH = 100000  # 100KB should be more than enough for any LLM response
    if len(text) > MAX_INPUT_LENGTH:
        text = text[:MAX_INPUT_LENGTH]
    
    text = strip_perplexity_citations(text.strip())

    # Try multiple approaches to extract JSON from code fences
    # Approach 1: Match ```json ... ``` or ``` ... ``` anywhere
    # Updated to handle both newline and non-newline endings for code blocks
    # Note: Patterns use non-greedy matching but still vulnerable to ReDoS on very long input
    fence_patterns = [
        r"```json\s*\n([\s\S]*?)\n```",      # ```json with newline ending
        r"```\s*\n([\s\S]*?)\n```",          # ``` with newline ending
        r"```json\s*\n([\s\S]*?)```",        # ```json without newline ending
        r"```\s*\n([\s\S]*?)```",            # ``` without newline ending
        r"^```json\s*\n([\s\S]*?)```\s*$",   # Full text with ```json
        r"^```\s*\n([\s\S]*?)```\s*$",      # Full text with ```
        r"```json\s*([\s\S]*?)\s*```",       # ```json with flexible spacing
        r"```\s*([\s\S]*?)\s*```",           # ``` with flexible spacing
    ]

    for pattern in fence_patterns:
        match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
        if match:
            extracted = match.group(1).strip()
            try:
                return json.loads(extracted)
            except json.JSONDecodeError:
                pass  # Try next pattern

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to extract partial JSON with just core_analysis if full parse fails
    # This helps with graceful degradation
    partial_match = re.search(r'"core_analysis"\s*:\s*"((?:[^"\\]|\\.)*?)"(?:,\s*"|\s*})', text, re.DOTALL)
    if partial_match:
        core_analysis = partial_match.group(1)
        # Try to extract other fields too
        insights_match = re.search(r'"key_insights"\s*:\s*\[(.*?)\]', text, re.DOTALL)
        insights = []
        if insights_match:
            insights_str = insights_match.group(1)
            # Extract individual insights
            for match in re.finditer(r'"((?:[^"\\]|\\.)*)"', insights_str):
                insights.append(match.group(1))

        return {
            "core_analysis": core_analysis,
            "key_insights": insights[:5],
        }

    # Find outermost JSON object by bracket counting
    start = text.find("{")
    if start != -1:
        depth, in_str, escape = 0, False, False
        for i, ch in enumerate(text[start:], start):
            if escape:
                escape = False
                continue
            if ch == "\\" and in_str:
                escape = True
                continue
            if ch == '"' and not escape:
                in_str = not in_str
                continue
            if not in_str:
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        candidate = text[start : i + 1]
                        try:
                            return json.loads(candidate)
                        except json.JSONDecodeError:
                            cleaned = re.sub(r",\s*([}\]])", r"\1", candidate)
                            try:
                                return json.loads(cleaned)
                            except json.JSONDecodeError:
                                break  # found boundary but still invalid; try repair

        # Last resort: truncated JSON repair — close any open brackets/strings
        candidate = text[start:]
        repaired = _repair_truncated_json(candidate)
        if repaired:
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                pass

    raise ParseError(
        f"Could not extract valid JSON from response. "
        f"First 200 chars: {text[:200]!r}"
    )


def _repair_truncated_json(text: str) -> str | None:
    """
    Close unclosed strings/arrays/objects caused by token-limit truncation.
    Returns repaired string, or None if structure is unrecoverable.
    """
    stack: list[str] = []
    in_str, escape = False, False

    for ch in text:
        if escape:
            escape = False
            continue
        if ch == "\\" and in_str:
            escape = True
            continue
        if ch == '"':
            if in_str:
                in_str = False
            else:
                in_str = True
            continue
        if not in_str:
            if ch in "{[":
                stack.append("}" if ch == "{" else "]")
            elif ch in "}]" and stack and stack[-1] == ch:
                stack.pop()

    if not stack and not in_str:
        return None  # already balanced — not a truncation issue

    suffix = ""
    if in_str:
        suffix += '"'  # close open string
    # Trim trailing incomplete key/value (e.g. `"key": ` with no value)
    tail = (text + suffix).rstrip()
    tail = re.sub(r',\s*"[^"]*"\s*:\s*$', "", tail)  # drop incomplete key-value
    tail = re.sub(r',\s*$', "", tail)                  # drop trailing comma
    suffix = "".join(reversed(stack))
    return tail + suffix


def extract_solution_prose(text: str) -> str | None:
    """
    Extract [SOLUTION]...[/SOLUTION] prose block from synthesis response.
    
    Returns:
        - The stripped prose content if found and non-empty
        - None if marker is absent OR if content is empty/whitespace-only
          (old JSON format or malformed response)
    """
    match = re.search(r"\[SOLUTION\]\s*(.*?)\s*\[/SOLUTION\]", text, re.DOTALL)
    if not match:
        return None
    
    # CRITICAL FIX: Return None for empty/whitespace-only content
    # This allows callers to distinguish between "no solution" and "empty solution"
    content = match.group(1).strip()
    return content if content else None


def strip_json_fences(text: str) -> str:
    """Remove markdown JSON code fences and any raw JSON block from text."""
    # Remove fenced code blocks
    text = re.sub(r"```json\s*.*?\s*```", "", text, flags=re.DOTALL)
    text = re.sub(r"```\s*.*?\s*```", "", text, flags=re.DOTALL)
    # Remove inline backtick wrappers
    text = re.sub(r"`[^`]*`", "", text)
    # Clean up extra whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def safe_float(value: Any, default: float = 0.0, min_val: float = 0.0, max_val: float = 10.0) -> float:
    """Safely coerce a value to float within bounds."""
    try:
        return max(min_val, min(max_val, float(value)))
    except (TypeError, ValueError):
        return default


def safe_list(value: Any) -> list[str]:
    """
    Safely coerce to list of strings.
    
    Handles:
    - list: Convert each item to string
    - str: Wrap in single-item list
    - dict: Extract values and convert to strings (preserves data)
    - None/other: Return empty list
    
    Note: Does not handle circular references in dict values.
    """
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        # CRITICAL FIX: Extract dict values instead of silently returning empty list
        # This preserves data when LLM returns dict instead of list
        try:
            return [str(v) for v in value.values()]
        except (Exception, RecursionError):
            # Handle edge cases like circular references or unconvertible values
            return []
    return []
