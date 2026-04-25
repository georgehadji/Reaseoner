"""
Backend CSRF token generation and validation.

Implements a stateless Double-Submit Cookie pattern using HMAC-SHA256,
compatible with the Next.js frontend CSRF implementation in
ui-next/src/lib/security-server.ts.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from typing import Optional


# Token validity window in seconds (24 hours)
_CSRF_TOKEN_MAX_AGE = 86400


def _get_csrf_secret() -> bytes:
    """Get the CSRF signing secret. CSRF_SECRET must be set independently of ADMIN_API_KEY."""
    raw = os.environ.get("CSRF_SECRET") or ""
    if not raw:
        raise RuntimeError(
            "CSRF_SECRET must be set for CSRF protection. "
            "Set CSRF_SECRET in your .env file (do not reuse ADMIN_API_KEY)."
        )
    return hashlib.sha256(raw.encode()).digest()


def generate_csrf_token() -> str:
    """Generate a token that embeds the current timestamp for expiry validation."""
    ts = int(time.time())
    rand = secrets.token_hex(24)
    return f"{ts}:{rand}"


def sign_csrf_token(token: str) -> str:
    """Sign a token with HMAC-SHA256. Returns 'token.signature_hex'."""
    secret = _get_csrf_secret()
    sig = hmac.new(secret, token.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{token}.{sig}"


def verify_csrf_token(signed: str) -> bool:
    """Verify a signed CSRF token: signature validity + expiry check."""
    if not signed or "." not in signed:
        return False
    # Split on the last dot to handle token values that may contain dots
    token, _, provided_sig = signed.rpartition(".")
    if not token or not provided_sig:
        return False

    secret = _get_csrf_secret()
    expected_sig = hmac.new(secret, token.encode("utf-8"), hashlib.sha256).hexdigest()

    # Constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(provided_sig, expected_sig):
        return False

    # Validate embedded timestamp to enforce token max-age
    try:
        ts_str, _ = token.split(":", 1)
        if time.time() - int(ts_str) > _CSRF_TOKEN_MAX_AGE:
            return False
    except (ValueError, IndexError):
        return False

    return True


def generate_signed_csrf_token() -> str:
    """Generate and sign a fresh CSRF token."""
    return sign_csrf_token(generate_csrf_token())
