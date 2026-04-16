"""
Simple Token-Based Authentication Middleware
Production-ready auth with API key validation and scoped access control.
"""

from __future__ import annotations

import os
import secrets
import hashlib
from typing import Optional, Dict, Set, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import asyncio


class Scope(str, Enum):
    """Permission scopes for API access control."""
    READ = "read"           # Read-only access (run pipelines, view history)
    WRITE = "write"         # Write access (modify settings, clear cache)
    ADMIN = "admin"         # Full administrative access
    PRESET_READ = "preset:read"     # View available presets
    PRESET_WRITE = "preset:write"   # Create/modify presets
    HISTORY_READ = "history:read"   # View pipeline history
    HISTORY_DELETE = "history:delete"  # Delete history entries
    CACHE_CLEAR = "cache:clear"     # Clear response cache
    KEY_MANAGE = "key:manage"       # Manage API keys (admin only)


# Default scope sets for common roles
DEFAULT_SCOPES = {
    "viewer": {Scope.READ, Scope.PRESET_READ, Scope.HISTORY_READ},
    "user": {Scope.READ, Scope.WRITE, Scope.PRESET_READ, Scope.HISTORY_READ, Scope.HISTORY_DELETE},
    "admin": {s for s in Scope},  # All scopes
}


@dataclass
class APIKey:
    """API key with metadata."""
    key_hash: str
    name: str
    created_at: datetime
    expires_at: Optional[datetime]
    scopes: Set[str] = field(default_factory=set)
    is_active: bool = True
    rate_limit_tier: str = "default"  # default, high, unlimited
    created_by: Optional[str] = None  # Admin who created this key
    last_used_at: Optional[datetime] = None
    usage_count: int = 0


class AuthenticationError(Exception):
    """Authentication failed."""
    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AuthorizationError(Exception):
    """Authorization failed - insufficient permissions."""
    def __init__(self, message: str, required_scope: str):
        self.message = message
        self.required_scope = required_scope
        self.status_code = 403
        super().__init__(message)


class AuthManager:
    """
    Production-ready API key authentication manager.

    Features:
    - Secure key hashing (SHA-256)
    - Key expiration
    - Scope-based authorization
    - Rate limit tiers
    - Usage tracking
    - Async-safe
    """

    def __init__(self):
        self._keys: Dict[str, APIKey] = {}
        self._lock = asyncio.Lock()
        self._admin_keys: Set[str] = set()

        # Load admin key from environment
        admin_key = os.environ.get("ADMIN_API_KEY")
        if admin_key:
            self._admin_keys.add(self._hash_key(admin_key))

    def _hash_key(self, key: str) -> str:
        """Hash API key using SHA-256."""
        return hashlib.sha256(key.encode()).hexdigest()

    def generate_key(
        self,
        name: str,
        expires_in_days: Optional[int] = None,
        scopes: Optional[Set[str]] = None,
        role: str = "user",
        rate_limit_tier: str = "default",
        created_by: Optional[str] = None,
    ) -> str:
        """
        Generate a new API key.

        Args:
            name: Human-readable name for the key
            expires_in_days: Key expiration in days (None = never)
            scopes: Allowed scopes (overrides role default)
            role: Predefined role (viewer, user, admin)
            rate_limit_tier: Rate limit tier (default, high, unlimited)
            created_by: Admin key hash that created this key

        Returns:
            The raw API key (store this securely - cannot be recovered)
        """
        raw_key = secrets.token_urlsafe(32)
        key_hash = self._hash_key(raw_key)

        expires_at = None
        if expires_in_days:
            expires_at = datetime.now() + timedelta(days=expires_in_days)

        # Use provided scopes or default for role
        if scopes is None:
            scopes = DEFAULT_SCOPES.get(role, DEFAULT_SCOPES["user"])

        api_key = APIKey(
            key_hash=key_hash,
            name=name,
            created_at=datetime.now(),
            expires_at=expires_at,
            scopes={s.value if isinstance(s, Scope) else s for s in scopes},
            rate_limit_tier=rate_limit_tier,
            created_by=created_by,
        )

        self._keys[key_hash] = api_key
        return raw_key

    async def authenticate(self, api_key: Optional[str]) -> Optional[APIKey]:
        """
        Authenticate request with API key.

        Args:
            api_key: Raw API key from request

        Returns:
            APIKey if valid, None otherwise

        Raises:
            AuthenticationError: If key is invalid/expired
        """
        if not api_key:
            raise AuthenticationError("Missing API key")

        key_hash = self._hash_key(api_key)

        async with self._lock:
            stored_key = self._keys.get(key_hash)

            # Check if key exists
            if not stored_key:
                # Check admin keys
                if key_hash in self._admin_keys:
                    return APIKey(
                        key_hash=key_hash,
                        name="admin",
                        created_at=datetime.now(),
                        expires_at=None,
                        scopes={s.value for s in DEFAULT_SCOPES["admin"]},
                        rate_limit_tier="unlimited",
                    )
                raise AuthenticationError("Invalid API key")

            # Check if key is active
            if not stored_key.is_active:
                raise AuthenticationError("API key is deactivated")

            # Check expiration
            if stored_key.expires_at and datetime.now() > stored_key.expires_at:
                stored_key.is_active = False
                raise AuthenticationError("API key has expired")

            # Update usage tracking
            stored_key.last_used_at = datetime.now()
            stored_key.usage_count += 1

            return stored_key

    async def authorize(self, api_key: APIKey, required_scope: str) -> bool:
        """
        Check if key has required scope.

        Args:
            api_key: Authenticated API key
            required_scope: Required scope (e.g., "read", "write", "admin")

        Returns:
            True if authorized

        Raises:
            AuthorizationError: If not authorized
        """
        if required_scope not in api_key.scopes:
            raise AuthenticationError(
                f"Insufficient permissions. Required: {required_scope}",
            )
        return True

    async def check_scopes(self, api_key: APIKey, required_scopes: List[str]) -> bool:
        """
        Check if key has ALL required scopes.

        Args:
            api_key: Authenticated API key
            required_scopes: List of required scopes

        Returns:
            True if all scopes present

        Raises:
            AuthorizationError: If any scope missing
        """
        missing = [s for s in required_scopes if s not in api_key.scopes]
        if missing:
            raise AuthorizationError(
                f"Missing required scopes: {', '.join(missing)}",
                required_scope=missing[0],
            )
        return True

    async def revoke_key(self, key_hash: str) -> bool:
        """Revoke an API key."""
        async with self._lock:
            if key_hash in self._keys:
                self._keys[key_hash].is_active = False
                return True
            return False

    async def list_keys(self, requester_scopes: Optional[Set[str]] = None) -> list[dict]:
        """
        List all active keys (without exposing hashes).
        
        Args:
            requester_scopes: Scopes of the requesting user (for filtering)
        """
        async with self._lock:
            keys = []
            for key in self._keys.values():
                key_info = {
                    "name": key.name,
                    "created_at": key.created_at.isoformat(),
                    "expires_at": key.expires_at.isoformat() if key.expires_at else None,
                    "scopes": list(key.scopes),
                    "is_active": key.is_active,
                    "rate_limit_tier": key.rate_limit_tier,
                    "usage_count": key.usage_count,
                    "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
                }
                # Only show created_by to admins
                if requester_scopes and Scope.ADMIN.value in requester_scopes:
                    key_info["created_by"] = key.created_by
                keys.append(key_info)
            return keys

    def get_rate_limit_tier(self, api_key: Optional[APIKey]) -> str:
        """Get rate limit tier for an API key."""
        if api_key is None:
            return "default"
        return api_key.rate_limit_tier


# Global auth manager
_auth_manager: Optional[AuthManager] = None


def get_auth_manager() -> AuthManager:
    """Get or create global auth manager."""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager
