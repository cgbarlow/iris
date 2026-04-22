"""HTTP → MCP tool-error mapping."""

from __future__ import annotations

from iris_client import IrisAuthError, IrisHTTPError, IrisRateLimitError


def format_error(exc: Exception) -> str:
    """Produce a one-line human-readable message for an MCP tool error."""
    if isinstance(exc, IrisAuthError):
        return f"Unauthenticated ({exc.status_code}): {exc.detail}. Check IRIS_TOKEN."
    if isinstance(exc, IrisRateLimitError):
        return f"Rate-limited ({exc.status_code}): {exc.detail}. Try again shortly."
    if isinstance(exc, IrisHTTPError):
        return f"HTTP {exc.status_code}: {exc.detail}"
    return f"Error: {exc}"
