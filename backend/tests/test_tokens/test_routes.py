"""Integration tests for /api/users/me/tokens (ADR-127, SPEC-127-A).

Boots the full FastAPI app with a temporary SQLite DB. Verifies:
- caller can create, list, and revoke PATs
- secret is returned exactly once
- list responses never include the secret
- another user's PATs are not visible / revocable (404)
- a PAT authenticates subsequent API calls (parity with JWT)
- revoked PATs return 401
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
        # Give the tests headroom — rate-limit specifics are unit-tested elsewhere.
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


async def _setup_admin_jwt(client: httpx.AsyncClient, username: str = "admin") -> str:
    """Create an admin user and return a JWT access token."""
    await client.post(
        "/api/auth/setup",
        json={"username": username, "password": "AdminPass123!"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": username, "password": "AdminPass123!"},
    )
    return resp.json()["access_token"]


class TestCreateAndList:
    async def test_create_returns_token_once(self, client: httpx.AsyncClient) -> None:
        jwt = await _setup_admin_jwt(client)
        headers = {"Authorization": f"Bearer {jwt}"}

        resp = await client.post(
            "/api/users/me/tokens",
            headers=headers,
            json={"name": "laptop"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "laptop"
        assert body["token"].startswith("iris_pat_")
        assert body["prefix"]
        assert body["revoked_at"] is None
        assert body["last_used_at"] is None

    async def test_list_hides_token_secret(self, client: httpx.AsyncClient) -> None:
        jwt = await _setup_admin_jwt(client)
        headers = {"Authorization": f"Bearer {jwt}"}

        await client.post("/api/users/me/tokens", headers=headers, json={"name": "a"})
        await client.post("/api/users/me/tokens", headers=headers, json={"name": "b"})

        resp = await client.get("/api/users/me/tokens", headers=headers)
        assert resp.status_code == 200
        records = resp.json()
        assert {r["name"] for r in records} == {"a", "b"}
        for r in records:
            assert "token" not in r  # never return secret
            assert r["prefix"]

    async def test_empty_name_rejected(self, client: httpx.AsyncClient) -> None:
        jwt = await _setup_admin_jwt(client)
        headers = {"Authorization": f"Bearer {jwt}"}
        resp = await client.post(
            "/api/users/me/tokens",
            headers=headers,
            json={"name": ""},
        )
        assert resp.status_code == 422


class TestRevoke:
    async def test_owner_can_revoke(self, client: httpx.AsyncClient) -> None:
        jwt = await _setup_admin_jwt(client)
        headers = {"Authorization": f"Bearer {jwt}"}
        created = (await client.post(
            "/api/users/me/tokens", headers=headers, json={"name": "revokable"},
        )).json()

        resp = await client.delete(
            f"/api/users/me/tokens/{created['id']}", headers=headers,
        )
        assert resp.status_code == 204

        listed = (await client.get("/api/users/me/tokens", headers=headers)).json()
        assert listed[0]["revoked_at"] is not None

    async def test_revoke_unknown_404(self, client: httpx.AsyncClient) -> None:
        jwt = await _setup_admin_jwt(client)
        headers = {"Authorization": f"Bearer {jwt}"}
        resp = await client.delete(
            "/api/users/me/tokens/does-not-exist", headers=headers,
        )
        assert resp.status_code == 404

    async def test_revoke_is_idempotent(self, client: httpx.AsyncClient) -> None:
        jwt = await _setup_admin_jwt(client)
        headers = {"Authorization": f"Bearer {jwt}"}
        created = (await client.post(
            "/api/users/me/tokens", headers=headers, json={"name": "idemp"},
        )).json()

        first = await client.delete(
            f"/api/users/me/tokens/{created['id']}", headers=headers,
        )
        second = await client.delete(
            f"/api/users/me/tokens/{created['id']}", headers=headers,
        )
        assert first.status_code == 204
        assert second.status_code == 204


class TestPatAuthenticatesApi:
    async def test_pat_works_as_bearer(self, client: httpx.AsyncClient) -> None:
        jwt = await _setup_admin_jwt(client)
        jwt_headers = {"Authorization": f"Bearer {jwt}"}
        created = (await client.post(
            "/api/users/me/tokens", headers=jwt_headers, json={"name": "cli"},
        )).json()

        # Now use the PAT instead of the JWT — should still authenticate.
        pat_headers = {"Authorization": f"Bearer {created['token']}"}
        resp = await client.get("/api/users/me/tokens", headers=pat_headers)
        assert resp.status_code == 200

    async def test_revoked_pat_returns_401(self, client: httpx.AsyncClient) -> None:
        jwt = await _setup_admin_jwt(client)
        jwt_headers = {"Authorization": f"Bearer {jwt}"}
        created = (await client.post(
            "/api/users/me/tokens", headers=jwt_headers, json={"name": "short"},
        )).json()

        await client.delete(
            f"/api/users/me/tokens/{created['id']}", headers=jwt_headers,
        )

        pat_headers = {"Authorization": f"Bearer {created['token']}"}
        resp = await client.get("/api/users/me/tokens", headers=pat_headers)
        assert resp.status_code == 401

    async def test_garbled_pat_returns_401(self, client: httpx.AsyncClient) -> None:
        headers = {"Authorization": "Bearer iris_pat_notareal_token"}
        resp = await client.get("/api/users/me/tokens", headers=headers)
        assert resp.status_code == 401


class TestCrossUserIsolation:
    async def test_cannot_see_other_users_tokens(self, client: httpx.AsyncClient) -> None:
        alice_jwt = await _setup_admin_jwt(client, username="admin")
        alice_headers = {"Authorization": f"Bearer {alice_jwt}"}

        # Create an Architect role user separately; the setup endpoint only
        # works once, so use the users admin router.
        resp = await client.post(
            "/api/users",
            headers=alice_headers,
            json={"username": "bob", "password": "BobPassword123!", "role": "architect"},
        )
        assert resp.status_code in (200, 201)

        bob_tokens = (await client.post(
            "/api/auth/login",
            json={"username": "bob", "password": "BobPassword123!"},
        )).json()
        bob_headers = {"Authorization": f"Bearer {bob_tokens['access_token']}"}

        alice_pat = (await client.post(
            "/api/users/me/tokens", headers=alice_headers, json={"name": "alice-pat"},
        )).json()

        # Bob cannot see Alice's PATs.
        listed = (await client.get("/api/users/me/tokens", headers=bob_headers)).json()
        assert all(r["name"] != "alice-pat" for r in listed)

        # Bob cannot revoke Alice's PATs (404 — not visible to him).
        resp = await client.delete(
            f"/api/users/me/tokens/{alice_pat['id']}", headers=bob_headers,
        )
        assert resp.status_code == 404
