"""Integration tests for auth API routes."""

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
    )


@pytest.fixture
async def client(app_config: AppConfig) -> AsyncIterator[httpx.AsyncClient]:
    application = create_app(app_config)
    db_manager = DatabaseManager(app_config.database)
    await initialize_databases(db_manager)
    application.state.db_manager = db_manager
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as c:
        yield c
    await db_manager.close()


async def _setup_admin(client: httpx.AsyncClient) -> dict[str, str]:
    """Create admin user via setup endpoint, return tokens."""
    resp = await client.post(
        "/api/auth/setup",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    assert resp.status_code == 200

    resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    assert resp.status_code == 200
    return resp.json()


class TestSetup:
    """Verify first-run admin setup endpoint."""

    async def test_setup_creates_admin(self, client: httpx.AsyncClient) -> None:
        resp = await client.post(
            "/api/auth/setup",
            json={"username": "admin", "password": "AdminPass123!"},
        )
        assert resp.status_code == 200
        assert "user_id" in resp.json()

    async def test_setup_only_works_once(self, client: httpx.AsyncClient) -> None:
        await client.post(
            "/api/auth/setup",
            json={"username": "admin", "password": "AdminPass123!"},
        )
        resp = await client.post(
            "/api/auth/setup",
            json={"username": "admin2", "password": "AnotherPass12!"},
        )
        assert resp.status_code == 400

    async def test_setup_validates_password(
        self, client: httpx.AsyncClient
    ) -> None:
        resp = await client.post(
            "/api/auth/setup",
            json={"username": "admin", "password": "weak"},
        )
        assert resp.status_code == 422  # Pydantic validation (min_length)


class TestLogin:
    """Verify login endpoint."""

    async def test_successful_login(self, client: httpx.AsyncClient) -> None:
        tokens = await _setup_admin(client)
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"  # noqa: S105

    async def test_invalid_username(self, client: httpx.AsyncClient) -> None:
        await _setup_admin(client)
        resp = await client.post(
            "/api/auth/login",
            json={"username": "nobody", "password": "AdminPass123!"},
        )
        assert resp.status_code == 401

    async def test_invalid_password(self, client: httpx.AsyncClient) -> None:
        await _setup_admin(client)
        resp = await client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "WrongPassword1!"},
        )
        assert resp.status_code == 401

    async def test_account_lockout_after_failures(
        self, client: httpx.AsyncClient
    ) -> None:
        await _setup_admin(client)
        # Fail 5 times
        for _ in range(5):
            await client.post(
                "/api/auth/login",
                json={"username": "admin", "password": "WrongPass123!"},
            )
        # 6th attempt should show locked
        resp = await client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "AdminPass123!"},
        )
        assert resp.status_code == 401
        assert "locked" in resp.json()["detail"].lower()


class TestRefresh:
    """Verify token refresh endpoint."""

    async def test_refresh_returns_new_tokens(
        self, client: httpx.AsyncClient
    ) -> None:
        tokens = await _setup_admin(client)
        resp = await client.post(
            "/api/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert resp.status_code == 200
        new_tokens = resp.json()
        assert new_tokens["access_token"] != tokens["access_token"]
        assert new_tokens["refresh_token"] != tokens["refresh_token"]

    async def test_refresh_invalid_token(
        self, client: httpx.AsyncClient
    ) -> None:
        resp = await client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid"},
        )
        assert resp.status_code == 401


class TestLogout:
    """Verify logout endpoint."""

    async def test_logout_revokes_tokens(
        self, client: httpx.AsyncClient
    ) -> None:
        tokens = await _setup_admin(client)
        resp = await client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert resp.status_code == 200

        # Refresh token should now be invalid
        resp = await client.post(
            "/api/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert resp.status_code == 401

    async def test_logout_requires_auth(
        self, client: httpx.AsyncClient
    ) -> None:
        resp = await client.post("/api/auth/logout")
        assert resp.status_code == 401


class TestChangePassword:
    """Verify change-password endpoint."""

    async def test_change_password_success(
        self, client: httpx.AsyncClient
    ) -> None:
        tokens = await _setup_admin(client)
        resp = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "AdminPass123!",
                "new_password": "NewSecure456!",
            },
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert resp.status_code == 200

        # Old password should no longer work
        resp = await client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "AdminPass123!"},
        )
        assert resp.status_code == 401

        # New password should work
        resp = await client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "NewSecure456!"},
        )
        assert resp.status_code == 200

    async def test_change_password_wrong_current(
        self, client: httpx.AsyncClient
    ) -> None:
        tokens = await _setup_admin(client)
        resp = await client.post(
            "/api/auth/change-password",
            json={
                "current_password": "WrongPass123!",
                "new_password": "NewSecure456!",
            },
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert resp.status_code == 400
