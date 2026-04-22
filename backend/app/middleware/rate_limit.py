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


def _get_rate_category(request: Request) -> str:
    """Categorize a request for rate limiting.

    Buckets (ADR-123, ADR-127, ADR-129):

    - ``login`` — POST /api/auth/login
    - ``refresh`` — POST /api/auth/refresh
    - ``anon_ai`` — anonymous calls on /api/ai/* (stricter, 1h window)
    - ``pat`` — PAT-authenticated calls (Authorization: Bearer iris_pat_...)
    - ``anon`` — other anonymous calls (no Authorization header)
    - ``general`` — JWT-authenticated (or other Bearer) calls

    Buckets are independent: exhausting one never blocks another.
    """
    path = request.url.path
    if path == "/api/auth/login":
        return "login"
    if path == "/api/auth/refresh":
        return "refresh"
    auth = request.headers.get("Authorization", "")
    is_anon = not auth
    if path.startswith("/api/ai/") and is_anon:
        return "anon_ai"
    if auth.startswith("Bearer iris_pat_"):
        return "pat"
    if is_anon:
        return "anon"
    return "general"


# Windows per category. Anonymous AI uses 1 hour so the small bucket
# (default 10 requests) smooths over bursty interactive use on UAT
# without regenerating every minute. All other buckets use a 60 s window.
_CATEGORY_WINDOWS: dict[str, int] = {
    "login": 60,
    "refresh": 60,
    "general": 60,
    "anon_ai": 3600,
    "pat": 60,
    "anon": 60,
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding window rate limiting middleware."""

    def __init__(self, app: object, **kwargs: int) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.limiter = SlidingWindowRateLimiter()
        self.limits: dict[str, int] = {
            "login": kwargs.get("login", 10),
            "refresh": kwargs.get("refresh", 30),
            "general": kwargs.get("general", 100),
            "anon_ai": kwargs.get("anon_ai", 10),
            "pat": kwargs.get("pat", 60),
            "anon": kwargs.get("anon", 30),
        }

    async def dispatch(
        self, request: Request, call_next: Callable[..., Response]
    ) -> Response:
        """Check rate limit before processing request."""
        client_ip = _get_client_ip(request)
        category = _get_rate_category(request)
        limit = self.limits[category]
        window = _CATEGORY_WINDOWS.get(category, 60)
        key = f"{client_ip}:{category}"

        if not self.limiter.is_allowed(key, limit, window=window):
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests"},
                headers={"Retry-After": str(window)},
            )

        return await call_next(request)  # type: ignore[misc]
