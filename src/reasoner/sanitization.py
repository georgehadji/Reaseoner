"""
ARA Pipeline - Input Sanitization
Comprehensive input validation and sanitization for security.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Any

from reasoner.core.constants import DEFAULT_SANITIZER_MAX_LENGTH


@dataclass
class SanitizationResult:
    """Result of sanitization operation."""
    is_valid: bool
    sanitized: str
    warnings: list[str]
    blocked: bool = False


class InputSanitizer:
    """
    Comprehensive input sanitization for user-provided text.
    """

    # Characters that might indicate prompt injection
    INJECTION_PATTERNS = [
        r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions?|rules?|commands?)",
        r"disregard\s+(?:all\s+)?(?:previous|prior|above)",
        r"forget\s+(?:everything|all)\s+you\s+(?:know|were\s+told)",
        r"new\s+instruction[s]?:",
        r"system\s*:\s*",
        r"assistant\s*:\s*",
        r"\[INST\]",
        r"\[/INST\]",
        r"<<SYS>>",
        r"<<\/SYS>>",
        r"#{3,}\s*system",
    ]

    # Compile patterns for efficiency
    _injection_regex = re.compile(
        "|".join(INJECTION_PATTERNS),
        re.IGNORECASE | re.MULTILINE,
    )

    # Characters to strip
    STRIP_CHARS = "\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f"

    def __init__(
        self,
        max_length: int = DEFAULT_SANITIZER_MAX_LENGTH,
        allow_html: bool = False,
        block_injection: bool = True,
    ):
        self.max_length = max_length
        self.allow_html = allow_html
        self.block_injection = block_injection

    def sanitize(self, text: str) -> SanitizationResult:
        """
        Sanitize input text.

        Args:
            text: Input text to sanitize

        Returns:
            SanitizationResult with sanitized text and any warnings
        """
        warnings = []
        sanitized = text

        # Check for empty input
        if not sanitized or not sanitized.strip():
            return SanitizationResult(
                is_valid=False,
                sanitized="",
                warnings=["Empty input"],
                blocked=True,
            )

        # Remove null bytes and other control characters
        original = sanitized
        sanitized = sanitized.translate({ord(c): None for c in self.STRIP_CHARS})

        if original != sanitized:
            warnings.append("Removed control characters")

        # Check for prompt injection patterns BEFORE truncation
        # so that malicious payloads cannot evade detection by exceeding
        # the length limit and getting silently truncated.
        if self.block_injection:
            injection_match = self._injection_regex.search(sanitized)
            if injection_match:
                # Block the input entirely if injection detected
                return SanitizationResult(
                    is_valid=False,
                    sanitized="",
                    warnings=["Potential prompt injection detected"],
                    blocked=True,
                )

        # Check length
        if len(sanitized) > self.max_length:
            sanitized = sanitized[:self.max_length]
            warnings.append(f"Truncated to {self.max_length} characters")

        # HTML escape if not allowed
        if not self.allow_html:
            original = sanitized
            sanitized = html.escape(sanitized)
            if original != sanitized:
                warnings.append("Escaped HTML entities")

        # Check for excessive repetition (potential abuse)
        if self._has_excessive_repetition(sanitized):
            warnings.append("Excessive character repetition detected")

        # Check for suspicious patterns
        suspicious = self._check_suspicious_patterns(sanitized)
        if suspicious:
            warnings.extend(suspicious)

        return SanitizationResult(
            is_valid=True,
            sanitized=sanitized,
            warnings=warnings,
        )

    def _has_excessive_repetition(self, text: str) -> bool:
        """Check for excessive character repetition."""
        # Check for same character repeated more than 5 times
        if re.search(r"(.)\1{5,}", text):
            return True
        # Check for same word repeated more than 3 times
        if re.search(r"\b(\w+)(?:\s+\1){3,}", text, re.IGNORECASE):
            return True
        return False

    def _check_suspicious_patterns(self, text: str) -> list[str]:
        """Check for other suspicious patterns."""
        warnings = []

        # Check for very long words (potential encoding attempt)
        words = text.split()
        long_words = [w for w in words if len(w) > 100]
        if long_words:
            warnings.append(f"Found {len(long_words)} unusually long words")

        # Check for high ratio of special characters
        special_chars = len(re.findall(r"[^\w\s]", text))
        total_chars = len(text.replace(" ", ""))
        if total_chars > 0 and special_chars / total_chars > 0.5:
            warnings.append("High ratio of special characters")

        return warnings


def sanitize_problem(problem: str) -> tuple[str, list[str]]:
    """
    Sanitize problem input.

    Args:
        problem: Problem text from user

    Returns:
        Tuple of (sanitized_problem, warnings)
    """
    sanitizer = InputSanitizer(max_length=10000, block_injection=True)
    result = sanitizer.sanitize(problem)

    if result.blocked:
        raise ValueError("Input blocked due to security concerns")

    return result.sanitized, result.warnings


def sanitize_for_prompt(text: str) -> tuple[str, list[str]]:
    """
    Sanitize text for LLM prompts without HTML escaping.

    Reuses InputSanitizer but preserves <, >, & characters so that
    legitimate math/code questions are not mangled in prompts.
    """
    sanitizer = InputSanitizer(
        max_length=DEFAULT_SANITIZER_MAX_LENGTH,
        allow_html=True,
        block_injection=True,
    )
    result = sanitizer.sanitize(text)

    if result.blocked:
        raise ValueError("Input blocked: potential prompt injection detected")

    return result.sanitized, result.warnings


def sanitize_for_logging(text: str, max_length: int = 200) -> str:
    """
    Sanitize text for logging (removes sensitive patterns).
    """
    # Remove potential API keys
    sanitized = re.sub(
        r"(api[_-]?key|token|secret|password)[=:]\s*[\w\-]{8,}",
        r"\1=***REDACTED***",
        text,
        flags=re.IGNORECASE,
    )

    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."

    return sanitized