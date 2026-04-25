"""
Auth adapter factory.

Selects the appropriate auth adapter based on environment settings.
"""

from __future__ import annotations

import os
import threading
from typing import Optional

from reasoner.application.ports.auth_port import AuthPort

_auth_adapter: Optional[AuthPort] = None
_auth_lock = threading.Lock()


def get_auth_adapter() -> AuthPort:
    """Get or create the global auth adapter."""
    global _auth_adapter
    if _auth_adapter is not None:
        return _auth_adapter

    with _auth_lock:
        # Double-checked locking
        if _auth_adapter is not None:
            return _auth_adapter

        env = os.environ.get("ENVIRONMENT", "development")
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

        if env == "production" and supabase_url and supabase_service_key:
            from .supabase_adapter import SupabaseAuthAdapter
            _auth_adapter = SupabaseAuthAdapter(supabase_url, supabase_service_key)
        elif env == "testing":
            from .local_adapter import LocalAuthAdapter
            _auth_adapter = LocalAuthAdapter()
        else:
            # Development fallback: try Supabase, fall back to local
            if supabase_url and supabase_service_key:
                try:
                    from .supabase_adapter import SupabaseAuthAdapter
                    _auth_adapter = SupabaseAuthAdapter(supabase_url, supabase_service_key)
                except Exception:
                    from .local_adapter import LocalAuthAdapter
                    _auth_adapter = LocalAuthAdapter()
            else:
                from .local_adapter import LocalAuthAdapter
                _auth_adapter = LocalAuthAdapter()

    return _auth_adapter


def set_auth_adapter(adapter: AuthPort) -> None:
    """Override the auth adapter (useful for tests)."""
    global _auth_adapter
    with _auth_lock:
        _auth_adapter = adapter
