"""Exceptions raised by iris-client.

The client lets httpx errors bubble from low-level helpers, but public
methods wrap them in the hierarchy below so callers (CLI, MCP) can map
to user-facing messages without importing httpx directly.
"""

from __future__ import annotations

import httpx


class IrisClientError(Exception):
    """Base class for every error raised by iris-client."""


class IrisHTTPError(IrisClientError):
    """Raised for any non-2xx response from the backend.

    Carries the HTTP status and the backend's detail string (from
    FastAPI's `{"detail": ...}` body when present).
    """

    def __init__(
        self,
        status_code: int,
        detail: str,
        response: httpx.Response | None = None,
    ) -> None:
        super().__init__(f"HTTP {status_code}: {detail}")
        self.status_code = status_code
        self.detail = detail
        self.response = response


class IrisAuthError(IrisHTTPError):
    """401 / 403 — the token is missing, invalid, revoked, or lacks permission."""


class IrisRateLimitError(IrisHTTPError):
    """429 — rate-limit bucket exhausted."""


def from_httpx_error(exc: httpx.HTTPStatusError) -> IrisHTTPError:
    """Map an httpx status error onto the iris-client hierarchy."""
    status = exc.response.status_code
    detail = _extract_detail(exc.response)
    if status in (401, 403):
        return IrisAuthError(status, detail, exc.response)
    if status == 429:
        return IrisRateLimitError(status, detail, exc.response)
    return IrisHTTPError(status, detail, exc.response)


def _extract_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text or response.reason_phrase
    if isinstance(payload, dict) and "detail" in payload:
        detail = payload["detail"]
        if isinstance(detail, str):
            return detail
    return str(payload)
