"""Tests for the AI provider error mapper (ADR-124 / v4.1.1)."""

from __future__ import annotations

import httpx

from app.ai.error_mapper import map_provider_error


def _http_status_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "https://example.test/v1/chat/completions")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError("Server error", request=request, response=response)


class TestMapProviderError:
    """Each classification returns a distinct, user-readable message."""

    def test_timeout_returns_wait_and_retry(self) -> None:
        msg = map_provider_error(httpx.TimeoutException("read timed out"))
        assert "too long" in msg.lower()

    def test_connect_error_returns_network_message(self) -> None:
        msg = map_provider_error(httpx.ConnectError("connection refused"))
        assert "couldn't reach" in msg.lower()

    def test_network_error_returns_network_message(self) -> None:
        msg = map_provider_error(httpx.NetworkError("dns failure"))
        assert "couldn't reach" in msg.lower()

    def test_502_returns_upstream_unavailable(self) -> None:
        """This is the exact case that prompted ADR-124 — provider edge 502."""
        msg = map_provider_error(_http_status_error(502))
        assert "temporarily unavailable" in msg.lower()
        assert "502" in msg  # surfaces the code so ops can diagnose

    def test_503_returns_upstream_unavailable(self) -> None:
        msg = map_provider_error(_http_status_error(503))
        assert "temporarily unavailable" in msg.lower()

    def test_429_returns_rate_limit(self) -> None:
        msg = map_provider_error(_http_status_error(429))
        assert "rate-limited" in msg.lower()

    def test_401_returns_auth_message(self) -> None:
        msg = map_provider_error(_http_status_error(401))
        assert "credentials" in msg.lower() or "api key" in msg.lower()

    def test_403_returns_auth_message(self) -> None:
        msg = map_provider_error(_http_status_error(403))
        assert "credentials" in msg.lower() or "api key" in msg.lower()

    def test_400_returns_client_error(self) -> None:
        """400 typically means a wrong model name — admin-actionable."""
        msg = map_provider_error(_http_status_error(400))
        assert "400" in msg
        assert "model" in msg.lower() or "parameters" in msg.lower()

    def test_unknown_exception_returns_generic(self) -> None:
        msg = map_provider_error(RuntimeError("something weird"))
        assert "administrator" in msg.lower()

    def test_never_leaks_raw_url(self) -> None:
        """The raw URL in httpx errors must not appear in user-facing text
        (ADR-124 — the v4.1.0 UAT error exposed api.agentics.org.nz)."""
        request = httpx.Request("POST", "https://api.agentics.org.nz/v1/chat/completions")
        response = httpx.Response(502, request=request)
        exc = httpx.HTTPStatusError(
            f"Server error '502 Bad Gateway' for url '{request.url}'",
            request=request,
            response=response,
        )
        msg = map_provider_error(exc)
        assert "agentics.org.nz" not in msg
        assert "http" not in msg.lower()  # no URL in user-facing text
