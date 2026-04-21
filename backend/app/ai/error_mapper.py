"""Map provider exceptions to user-facing messages (ADR-124 related work).

Reuses the same exception taxonomy already classified by `_is_retryable`
in `app.ai.client`, so retry logic and error messaging stay aligned.
The raw exception (including URL and upstream payload) is always logged
— only the user-facing `detail` string is friendly.
"""

from __future__ import annotations

import httpx

_TIMEOUT_MSG = (
    "AI provider took too long to respond. Try again in a few minutes."
)
_NETWORK_MSG = (
    "Couldn't reach the AI provider. Check provider URL and network "
    "connectivity, then try again."
)
_UPSTREAM_MSG = (
    "AI provider is temporarily unavailable (upstream returned "
    "{status}). Try again in a few minutes or switch to a different "
    "provider."
)
_RATE_LIMIT_MSG = (
    "AI provider rate-limited the request. Wait a moment and try again."
)
_AUTH_MSG = (
    "AI provider rejected the request credentials. Check the provider's "
    "API key in admin settings."
)
_CLIENT_MSG = (
    "AI provider rejected the request ({status}). The configured model "
    "name or parameters may be invalid — check admin AI settings."
)
_GENERIC_MSG = "AI provider error — contact an administrator."


def map_provider_error(exc: BaseException) -> str:
    """Return a short, user-facing string for a provider-layer exception.

    The mapping mirrors the exception taxonomy in `client._is_retryable`
    so error messaging stays consistent with retry behaviour:

    - Timeout → user waits and retries; we don't auto-retry.
    - Network / connect / remote-protocol → retryable by client;
      surfaces as transient connectivity error when exhausted.
    - HTTP 429 → rate limit; user waits.
    - HTTP 5xx → upstream outage (this is the common case that produced
      the v4.1.0 UAT 502s against api.agentics.org.nz).
    - HTTP 401/403 → provider credentials; admin action needed.
    - HTTP 4xx (other) → bad request — typically wrong model name.
    - Anything else → generic fallback.
    """
    if isinstance(exc, httpx.TimeoutException):
        return _TIMEOUT_MSG
    if isinstance(exc, (httpx.NetworkError, httpx.ConnectError, httpx.RemoteProtocolError)):
        return _NETWORK_MSG
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status == 429:  # noqa: PLR2004
            return _RATE_LIMIT_MSG
        if status in (401, 403):  # noqa: PLR2004
            return _AUTH_MSG
        if status >= 500:  # noqa: PLR2004
            return _UPSTREAM_MSG.format(status=status)
        if 400 <= status < 500:  # noqa: PLR2004
            return _CLIENT_MSG.format(status=status)
    return _GENERIC_MSG
