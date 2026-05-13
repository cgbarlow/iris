"""v6.0.0 (ADR-164, SPEC-164-A): iris-mcp Protected Resource metadata
+ WWW-Authenticate helper.
"""

from __future__ import annotations

import os

import pytest

from iris_mcp.oauth_resource import (
    build_resource_metadata,
    resource_metadata_url_from_env,
    www_authenticate_header,
)


class TestProtectedResourceMetadata:
    def test_required_fields_present(self) -> None:
        meta = build_resource_metadata(
            resource="https://iris-mcp.example.com",
            authorization_server="https://iris-backend.example.com",
        )
        assert meta["resource"] == "https://iris-mcp.example.com"
        assert meta["authorization_servers"] == ["https://iris-backend.example.com"]
        assert "iris" in meta["scopes_supported"]
        assert "header" in meta["bearer_methods_supported"]

    def test_custom_scopes(self) -> None:
        meta = build_resource_metadata(
            resource="https://iris-mcp.example.com",
            authorization_server="https://iris-backend.example.com",
            scopes=["iris:read", "iris:write"],
        )
        assert meta["scopes_supported"] == ["iris:read", "iris:write"]


class TestWwwAuthenticateHeader:
    def test_includes_resource_metadata_url(self) -> None:
        header = www_authenticate_header(
            "https://iris-mcp.example.com/.well-known/oauth-protected-resource",
        )
        assert header.startswith("Bearer ")
        assert (
            'resource_metadata="https://iris-mcp.example.com/.well-known/oauth-protected-resource"'
            in header
        )
        assert 'error="invalid_token"' in header


class TestResourceMetadataUrlFromEnv:
    def test_prefers_public_url_env(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("IRIS_MCP_PUBLIC_URL", "https://iris-mcp.example.com")
        url = resource_metadata_url_from_env(default_host="ignored")
        assert url == "https://iris-mcp.example.com/.well-known/oauth-protected-resource"

    def test_falls_back_to_default_host(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("IRIS_MCP_PUBLIC_URL", raising=False)
        url = resource_metadata_url_from_env(default_host="https://fallback")
        assert url == "https://fallback/.well-known/oauth-protected-resource"


class TestHttpMainEndpointMounted:
    @pytest.mark.asyncio
    async def test_metadata_endpoint_returns_200(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import httpx
        from iris_mcp.http_main import create_app
        monkeypatch.setenv("IRIS_API_URL", "https://iris-backend.example.com")
        monkeypatch.setenv("IRIS_MCP_PUBLIC_URL", "https://iris-mcp.example.com")
        # ADR-169 (v6.0.9): IRIS_WEB_URL must NOT appear in the OAuth
        # metadata. Set it to a known wrong value so the test would fail
        # if the v6.0.0–v6.0.8 buggy behaviour re-emerged.
        monkeypatch.setenv("IRIS_WEB_URL", "https://wrong-host.example.com")
        app = create_app()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/.well-known/oauth-protected-resource")
        assert resp.status_code == 200
        body = resp.json()
        assert body["resource"] == "https://iris-mcp.example.com"
        # ADR-169 (v6.0.9): the Authorization Server URL must point at
        # the API (where /oauth/* and /.well-known/oauth-authorization-server
        # actually live), NOT at the frontend (which serves a SvelteKit
        # SPA and returns index.html for unknown paths — silently breaking
        # the OAuth discovery chain).
        assert body["authorization_servers"] == [
            "https://iris-backend.example.com",
        ]
        assert "wrong-host" not in body["authorization_servers"][0]
        assert "wrong-host" not in body["resource"]

    @pytest.mark.asyncio
    async def test_metadata_falls_back_to_api_url_without_public_url(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """ADR-169: without `IRIS_MCP_PUBLIC_URL`, both `resource` and
        `authorization_server` fall back to `IRIS_API_URL` (same host,
        consistent with the AS-and-resource-co-located dev setup). The
        v6.0.0–v6.0.8 buggy fallback used `IRIS_WEB_URL` for both,
        which broke OAuth discovery."""
        import httpx
        from iris_mcp.http_main import create_app
        monkeypatch.setenv("IRIS_API_URL", "https://iris-backend.example.com")
        monkeypatch.delenv("IRIS_MCP_PUBLIC_URL", raising=False)
        monkeypatch.setenv("IRIS_WEB_URL", "https://wrong-host.example.com")
        app = create_app()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/.well-known/oauth-protected-resource")
        body = resp.json()
        assert body["resource"] == "https://iris-backend.example.com"
        assert body["authorization_servers"] == [
            "https://iris-backend.example.com",
        ]
