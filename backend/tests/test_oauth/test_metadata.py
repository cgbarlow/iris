"""v6.0.0 (ADR-164, SPEC-164-A): /.well-known/oauth-authorization-server
returns RFC 8414 metadata. Anonymous-readable; MCP clients consume this
to discover the AS endpoints.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest

from app.config import AppConfig, AuthConfig, DatabaseConfig
from app.database import DatabaseManager
from app.main import create_app
from app.startup import initialize_databases

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from pathlib import Path


@pytest.fixture
def app_config(tmp_path: Path) -> AppConfig:
    return AppConfig(
        debug=True,
        cors_origins=["http://localhost:5173"],
        database=DatabaseConfig(data_dir=str(tmp_path / "data")),
        auth=AuthConfig(
            jwt_secret="test-secret-key-that-is-at-least-32-bytes-long-for-hs256",
            argon2_time_cost=1,
            argon2_memory_cost=8192,
            argon2_parallelism=1,
        ),
        rate_limit_general=1000,
        rate_limit_pat=1000,
    )


@pytest.fixture
async def client(app_config: AppConfig) -> AsyncIterator[httpx.AsyncClient]:
    application = create_app(app_config)
    db_manager = DatabaseManager(app_config)
    await initialize_databases(db_manager)
    application.state.db_manager = db_manager
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test",
    ) as c:
        yield c
    await db_manager.close()


class TestAuthorizationServerMetadata:
    async def test_returns_required_fields(
        self, client: httpx.AsyncClient,
    ) -> None:
        resp = await client.get("/.well-known/oauth-authorization-server")
        assert resp.status_code == 200
        meta = resp.json()
        # RFC 8414 required + recommended fields.
        for field in (
            "issuer",
            "authorization_endpoint",
            "token_endpoint",
            "registration_endpoint",
            "revocation_endpoint",
            "scopes_supported",
            "response_types_supported",
            "grant_types_supported",
            "code_challenge_methods_supported",
            "token_endpoint_auth_methods_supported",
        ):
            assert field in meta, f"missing field {field}"

    async def test_iris_scope_supported(
        self, client: httpx.AsyncClient,
    ) -> None:
        resp = await client.get("/.well-known/oauth-authorization-server")
        meta = resp.json()
        assert meta["scopes_supported"] == ["iris"]

    async def test_s256_pkce_supported(
        self, client: httpx.AsyncClient,
    ) -> None:
        resp = await client.get("/.well-known/oauth-authorization-server")
        meta = resp.json()
        assert "S256" in meta["code_challenge_methods_supported"]

    async def test_anonymous_readable(
        self, client: httpx.AsyncClient,
    ) -> None:
        # No Authorization header.
        resp = await client.get("/.well-known/oauth-authorization-server")
        assert resp.status_code == 200


class TestAuthorizationEndpointFromIrisWebUrl:
    """v6.0.11 (ADR-171): the `authorization_endpoint` must point at the
    SvelteKit frontend page (where the consent screen lives), NOT at the
    API host. The token / registration / revocation endpoints stay on
    the API host."""

    async def test_authorization_endpoint_uses_iris_web_url(
        self,
        client: httpx.AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("IRIS_WEB_URL", "https://web.example.com")
        resp = await client.get("/.well-known/oauth-authorization-server")
        meta = resp.json()
        assert meta["authorization_endpoint"] == (
            "https://web.example.com/oauth/authorize"
        )
        # Machine endpoints stay on the API host (the issuer).
        issuer = meta["issuer"]
        assert meta["token_endpoint"] == f"{issuer}/oauth/token"
        assert meta["registration_endpoint"] == f"{issuer}/oauth/register"
        assert meta["revocation_endpoint"] == f"{issuer}/oauth/revoke"

    async def test_authorization_endpoint_strips_trailing_slash(
        self,
        client: httpx.AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("IRIS_WEB_URL", "https://web.example.com/")
        resp = await client.get("/.well-known/oauth-authorization-server")
        meta = resp.json()
        # No double-slash even when operator's env var has a trailing slash.
        assert meta["authorization_endpoint"] == (
            "https://web.example.com/oauth/authorize"
        )

    async def test_authorization_endpoint_falls_back_to_api_when_unset(
        self,
        client: httpx.AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Dev environments without a separately-running frontend get
        the API host fallback — produces a 404 if the user actually
        clicks through, but the metadata document is at least
        well-formed."""
        monkeypatch.delenv("IRIS_WEB_URL", raising=False)
        resp = await client.get("/.well-known/oauth-authorization-server")
        meta = resp.json()
        issuer = meta["issuer"]
        assert meta["authorization_endpoint"] == f"{issuer}/oauth/authorize"
