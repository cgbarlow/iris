"""v6.0.0 (ADR-164, SPEC-164-A): POST /oauth/register — RFC 7591 DCR.
Open registration; any caller can self-register.
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


class TestDynamicClientRegistration:
    async def test_happy_path(self, client: httpx.AsyncClient) -> None:
        resp = await client.post(
            "/oauth/register",
            json={
                "client_name": "Claude.ai Connector",
                "redirect_uris": ["https://claude.ai/oauth/callback"],
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["client_id"].startswith("iris-mcp-")
        assert body["client_name"] == "Claude.ai Connector"
        # Public client (default) — no secret returned.
        assert body["client_secret"] is None
        assert body["token_endpoint_auth_method"] == "none"
        assert "client_id_issued_at" in body

    async def test_confidential_client_gets_secret(
        self, client: httpx.AsyncClient,
    ) -> None:
        resp = await client.post(
            "/oauth/register",
            json={
                "client_name": "Confidential client",
                "redirect_uris": ["https://example.com/callback"],
                "token_endpoint_auth_method": "client_secret_basic",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["client_secret"] is not None
        assert len(body["client_secret"]) >= 32

    async def test_missing_redirect_uris_is_422(
        self, client: httpx.AsyncClient,
    ) -> None:
        resp = await client.post(
            "/oauth/register",
            json={"client_name": "Missing uris"},
        )
        assert resp.status_code == 422

    async def test_each_registration_gets_unique_client_id(
        self, client: httpx.AsyncClient,
    ) -> None:
        body = {
            "client_name": "Same name",
            "redirect_uris": ["https://example.com/callback"],
        }
        r1 = await client.post("/oauth/register", json=body)
        r2 = await client.post("/oauth/register", json=body)
        assert r1.json()["client_id"] != r2.json()["client_id"]

    async def test_open_registration_no_auth_required(
        self, client: httpx.AsyncClient,
    ) -> None:
        resp = await client.post(
            "/oauth/register",
            json={
                "client_name": "Anonymous registration",
                "redirect_uris": ["https://example.com/callback"],
            },
        )
        # No Authorization header sent — should still succeed.
        assert resp.status_code == 201
