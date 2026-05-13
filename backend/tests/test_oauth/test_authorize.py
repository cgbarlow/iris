"""v6.0.0 (ADR-164, SPEC-164-A): /api/oauth/authorize/prepare validates
the request and caches a ConsentPayload; /api/oauth/authorize/decision
processes Allow/Deny and returns the final redirect URL.

The user-facing /oauth/authorize page is served by SvelteKit; these
are the backend helpers behind it.
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


async def _setup_admin_jwt(client: httpx.AsyncClient) -> str:
    await client.post(
        "/api/auth/setup",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    return resp.json()["access_token"]


async def _register_client(client: httpx.AsyncClient, redirect_uri: str) -> str:
    resp = await client.post(
        "/oauth/register",
        json={
            "client_name": "Test client",
            "redirect_uris": [redirect_uri],
        },
    )
    return resp.json()["client_id"]


class TestPrepareAuthorize:
    async def test_unauthenticated_returns_401(
        self, client: httpx.AsyncClient,
    ) -> None:
        client_id = await _register_client(client, "https://example.com/cb")
        resp = await client.post(
            "/api/oauth/authorize/prepare",
            json={
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": "https://example.com/cb",
                "code_challenge": "abc",
                "code_challenge_method": "S256",
            },
        )
        assert resp.status_code == 401

    async def test_authenticated_returns_consent_payload(
        self, client: httpx.AsyncClient,
    ) -> None:
        jwt = await _setup_admin_jwt(client)
        client_id = await _register_client(client, "https://example.com/cb")
        resp = await client.post(
            "/api/oauth/authorize/prepare",
            headers={"Authorization": f"Bearer {jwt}"},
            json={
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": "https://example.com/cb",
                "code_challenge": "abcd1234",
                "code_challenge_method": "S256",
                "state": "xyz",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["client_id"] == client_id
        assert body["client_name"] == "Test client"
        assert body["username"] == "admin"
        assert body["redirect_uri"] == "https://example.com/cb"
        assert body["state"] == "xyz"
        assert body["scope"] == "iris"
        assert body["request_id"]

    async def test_unknown_client_id_returns_400(
        self, client: httpx.AsyncClient,
    ) -> None:
        jwt = await _setup_admin_jwt(client)
        resp = await client.post(
            "/api/oauth/authorize/prepare",
            headers={"Authorization": f"Bearer {jwt}"},
            json={
                "response_type": "code",
                "client_id": "iris-mcp-bogus",
                "redirect_uri": "https://example.com/cb",
                "code_challenge": "abc",
                "code_challenge_method": "S256",
            },
        )
        assert resp.status_code == 400

    async def test_redirect_uri_mismatch_returns_400(
        self, client: httpx.AsyncClient,
    ) -> None:
        jwt = await _setup_admin_jwt(client)
        client_id = await _register_client(client, "https://example.com/cb")
        resp = await client.post(
            "/api/oauth/authorize/prepare",
            headers={"Authorization": f"Bearer {jwt}"},
            json={
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": "https://evil.example/cb",
                "code_challenge": "abc",
                "code_challenge_method": "S256",
            },
        )
        assert resp.status_code == 400

    async def test_missing_pkce_returns_400(
        self, client: httpx.AsyncClient,
    ) -> None:
        jwt = await _setup_admin_jwt(client)
        client_id = await _register_client(client, "https://example.com/cb")
        resp = await client.post(
            "/api/oauth/authorize/prepare",
            headers={"Authorization": f"Bearer {jwt}"},
            json={
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": "https://example.com/cb",
            },
        )
        assert resp.status_code == 400


class TestAuthorizeDecision:
    async def _prepare(
        self, client: httpx.AsyncClient, jwt: str, code_challenge: str = "abc",
    ) -> tuple[str, str]:
        client_id = await _register_client(client, "https://example.com/cb")
        resp = await client.post(
            "/api/oauth/authorize/prepare",
            headers={"Authorization": f"Bearer {jwt}"},
            json={
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": "https://example.com/cb",
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
                "state": "test-state",
            },
        )
        return resp.json()["request_id"], client_id

    async def test_allow_returns_code_redirect(
        self, client: httpx.AsyncClient,
    ) -> None:
        jwt = await _setup_admin_jwt(client)
        request_id, _ = await self._prepare(client, jwt)
        resp = await client.post(
            "/api/oauth/authorize/decision",
            headers={"Authorization": f"Bearer {jwt}"},
            json={"request_id": request_id, "decision": "allow"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["redirect_to"].startswith("https://example.com/cb?")
        assert "code=" in body["redirect_to"]
        assert "state=test-state" in body["redirect_to"]

    async def test_deny_returns_error_redirect(
        self, client: httpx.AsyncClient,
    ) -> None:
        jwt = await _setup_admin_jwt(client)
        request_id, _ = await self._prepare(client, jwt)
        resp = await client.post(
            "/api/oauth/authorize/decision",
            headers={"Authorization": f"Bearer {jwt}"},
            json={"request_id": request_id, "decision": "deny"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "error=access_denied" in body["redirect_to"]
        assert "state=test-state" in body["redirect_to"]

    async def test_unknown_request_id_returns_400(
        self, client: httpx.AsyncClient,
    ) -> None:
        jwt = await _setup_admin_jwt(client)
        resp = await client.post(
            "/api/oauth/authorize/decision",
            headers={"Authorization": f"Bearer {jwt}"},
            json={"request_id": "bogus", "decision": "allow"},
        )
        assert resp.status_code == 400

    async def test_request_id_is_single_use(
        self, client: httpx.AsyncClient,
    ) -> None:
        jwt = await _setup_admin_jwt(client)
        request_id, _ = await self._prepare(client, jwt)
        # First call succeeds.
        r1 = await client.post(
            "/api/oauth/authorize/decision",
            headers={"Authorization": f"Bearer {jwt}"},
            json={"request_id": request_id, "decision": "allow"},
        )
        assert r1.status_code == 200
        # Second call: request_id was consumed.
        r2 = await client.post(
            "/api/oauth/authorize/decision",
            headers={"Authorization": f"Bearer {jwt}"},
            json={"request_id": request_id, "decision": "allow"},
        )
        assert r2.status_code == 400
