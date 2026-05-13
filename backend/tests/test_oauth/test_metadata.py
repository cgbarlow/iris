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
