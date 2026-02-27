"""Sliding window rate limiting middleware per SPEC-005-B."""

from __future__ import annotations

import time
from collections import defaultdict
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastapi import Request, Response


class SlidingWindowRateLimiter:
    """In-memory sliding window rate limiter keyed by (client_ip, category)."""

    def __init__(self) -> None:
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str, limit: int, window: int = 60) -> bool:
        """Check if the request is allowed under the rate limit."""
        now = time.monotonic()
        timestamps = self._requests[key]

        # Remove expired entries
        cutoff = now - window
        self._requests[key] = [t for t in timestamps if t > cutoff]
        timestamps = self._requests[key]

        if len(timestamps) >= limit:
            return False

        timestamps.append(now)
        return True


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    if request.client:
        return request.client.host
    return "unknown"


def _get_rate_category(path: str) -> str:
    """Categorize a request path for rate limiting."""
    if path == "/api/auth/login":
        return "login"
    if path == "/api/auth/refresh":
        return "refresh"
    return "general"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding window rate limiting middleware."""

    def __init__(self, app: object, **kwargs: int) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.limiter = SlidingWindowRateLimiter()
        self.limits: dict[str, int] = {
            "login": kwargs.get("login", 10),
            "refresh": kwargs.get("refresh", 30),
            "general": kwargs.get("general", 100),
        }

    async def dispatch(
        self, request: Request, call_next: Callable[..., Response]
    ) -> Response:
        """Check rate limit before processing request."""
        client_ip = _get_client_ip(request)
        category = _get_rate_category(request.url.path)
        limit = self.limits[category]
        key = f"{client_ip}:{category}"

        if not self.limiter.is_allowed(key, limit):
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests"},
                headers={"Retry-After": "60"},
            )

        return await call_next(request)  # type: ignore[misc]
