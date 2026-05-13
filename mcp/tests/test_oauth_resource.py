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
        app = create_app()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/.well-known/oauth-protected-resource")
        assert resp.status_code == 200
        body = resp.json()
        assert body["resource"] == "https://iris-mcp.example.com"
        assert body["authorization_servers"] == ["https://iris-backend.example.com"]
