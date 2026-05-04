"""Phase-2 scaffolding tests — constructor, bearer header, error mapping.

Full method-surface tests (`test_client_search.py`, etc.) are added in
Phase 6 alongside the typed method implementations.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from iris_client import IrisAuthError, IrisClient, IrisHTTPError, IrisRateLimitError


class TestConstructor:
    def test_explicit_args_win(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("IRIS_URL", "http://ignored")
        monkeypatch.setenv("IRIS_TOKEN", "ignored")
        client = IrisClient(url="http://explicit", token="explicit-token")
        assert client.url == "http://explicit"
        assert client.token == "explicit-token"

    def test_env_fills_in_when_args_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("IRIS_URL", "http://from-env")
        monkeypatch.setenv("IRIS_TOKEN", "iris_pat_envtok")
        client = IrisClient()
        assert client.url == "http://from-env"
        assert client.token == "iris_pat_envtok"

    def test_defaults_when_nothing_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("IRIS_URL", raising=False)
        monkeypatch.delenv("IRIS_TOKEN", raising=False)
        client = IrisClient()
        assert client.url == "http://localhost:8000"
        assert client.token is None
        assert client.is_anonymous is True


class TestBearerHeader:
    @pytest.mark.asyncio
    async def test_pat_token_sends_bearer_header(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.get("http://iris.test/api/auth/me").mock(
            return_value=httpx.Response(
                200,
                json={"id": "u1", "username": "alice", "role": "Architect"},
            ),
        )
        await pat_client.whoami()
        request = route.calls.last.request
        assert request.headers["authorization"] == "Bearer iris_pat_abc12345_fakefakefake"

    @pytest.mark.asyncio
    async def test_anonymous_sends_no_authorization_header(
        self, anon_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        route = respx_mock.get("http://iris.test/api/auth/me").mock(
            return_value=httpx.Response(
                200,
                json={"id": "u-anon", "username": "anon", "role": "Viewer"},
            ),
        )
        await anon_client.whoami()
        request = route.calls.last.request
        assert "authorization" not in {k.lower() for k in request.headers.keys()}


class TestErrorMapping:
    @pytest.mark.asyncio
    async def test_401_maps_to_auth_error(
        self, anon_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get("http://iris.test/api/auth/me").mock(
            return_value=httpx.Response(401, json={"detail": "Not authenticated"}),
        )
        with pytest.raises(IrisAuthError) as excinfo:
            await anon_client.whoami()
        assert excinfo.value.status_code == 401
        assert "Not authenticated" in excinfo.value.detail

    @pytest.mark.asyncio
    async def test_429_maps_to_rate_limit_error(
        self, anon_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get("http://iris.test/api/auth/me").mock(
            return_value=httpx.Response(429, json={"detail": "Too many requests"}),
        )
        with pytest.raises(IrisRateLimitError):
            await anon_client.whoami()

    @pytest.mark.asyncio
    async def test_other_4xx_maps_to_http_error(
        self, anon_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get("http://iris.test/api/auth/me").mock(
            return_value=httpx.Response(404, json={"detail": "Not found"}),
        )
        with pytest.raises(IrisHTTPError) as excinfo:
            await anon_client.whoami()
        assert excinfo.value.status_code == 404
        # Not auth or rate-limit — plain HTTP error.
        assert not isinstance(excinfo.value, IrisAuthError)
        assert not isinstance(excinfo.value, IrisRateLimitError)
