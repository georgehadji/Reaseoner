"""FastAPI middleware classes for security, memory limits, and request timeouts."""

from __future__ import annotations

import asyncio
import logging
import os

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response


class MemoryLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce memory limits and prevent OOM.

    Configured via environment variables:
    - MEMORY_LIMIT_MB: Maximum memory in MB (default: 1024)
    - MEMORY_WARNING_MB: Warning threshold (default: 768)
    """

    def __init__(self, app, memory_limit_mb: int = 1024, warning_mb: int = 768):
        super().__init__(app)
        self.memory_limit_mb = memory_limit_mb
        self.warning_mb = warning_mb
        self._warning_logged = False

    async def dispatch(self, request: Request, call_next):
        try:
            import psutil

            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024

            if memory_mb > self.memory_limit_mb:
                logger.error(
                    f"Memory limit exceeded: {memory_mb:.1f}MB > {self.memory_limit_mb}MB"
                )
                return JSONResponse(
                    {"error": "Server memory limit exceeded. Please try again later."},
                    status_code=503,
                )

            if memory_mb > self.warning_mb and not self._warning_logged:
                logger.warning(
                    f"Memory usage high: {memory_mb:.1f}MB (limit: {self.memory_limit_mb}MB)"
                )
                self._warning_logged = True
            elif memory_mb < self.warning_mb * 0.8:
                self._warning_logged = False

        except ImportError:
            pass

        return await call_next(request)


class RequestTimeoutMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce request timeouts.

    Prevents long-running requests from blocking the server indefinitely.
    """

    def __init__(self, app, timeout_seconds: float = 300.0):
        super().__init__(app)
        self.timeout_seconds = timeout_seconds

    async def dispatch(self, request: Request, call_next):
        # Skip timeout for SSE endpoints (they're long-running by design)
        if request.url.path.startswith("/api/run"):
            return await call_next(request)

        try:
            return await asyncio.wait_for(
                call_next(request),
                timeout=self.timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.warning(f"Request timeout: {request.url.path}")
            return JSONResponse(
                {"error": "Request timeout"},
                status_code=504,
            )
