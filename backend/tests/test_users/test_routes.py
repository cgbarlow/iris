"""Integration tests for user management API routes."""

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


async def _admin_headers(client: httpx.AsyncClient) -> dict[str, str]:
    """Setup admin and return auth headers."""
    await client.post(
        "/api/auth/setup",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


class TestListUsers:
    """Verify user listing."""

    async def test_list_users_as_admin(self, client: httpx.AsyncClient) -> None:
        headers = await _admin_headers(client)
        resp = await client.get("/api/users", headers=headers)
        assert resp.status_code == 200
        users = resp.json()
        assert len(users) == 1
        assert users[0]["username"] == "admin"

    async def test_list_requires_auth(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/api/users")
        assert resp.status_code == 401


class TestCreateUser:
    """Verify user creation."""

    async def test_create_user(self, client: httpx.AsyncClient) -> None:
        headers = await _admin_headers(client)
        resp = await client.post(
            "/api/users",
            json={
                "username": "newuser",
                "password": "SecurePass123!",
                "role": "viewer",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["username"] == "newuser"
        assert resp.json()["role"] == "viewer"

    async def test_create_duplicate_username(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        await client.post(
            "/api/users",
            json={
                "username": "testuser",
                "password": "SecurePass123!",
                "role": "viewer",
            },
            headers=headers,
        )
        resp = await client.post(
            "/api/users",
            json={
                "username": "testuser",
                "password": "AnotherPass123!",
                "role": "viewer",
            },
            headers=headers,
        )
        assert resp.status_code == 409

    async def test_create_validates_password(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        resp = await client.post(
            "/api/users",
            json={"username": "u2", "password": "weak", "role": "viewer"},
            headers=headers,
        )
        assert resp.status_code == 422  # Pydantic min_length


class TestUpdateUser:
    """Verify user updates."""

    async def test_update_role(self, client: httpx.AsyncClient) -> None:
        headers = await _admin_headers(client)
        # Create a user first
        create_resp = await client.post(
            "/api/users",
            json={
                "username": "updatable",
                "password": "SecurePass123!",
                "role": "viewer",
            },
            headers=headers,
        )
        user_id = create_resp.json()["id"]
        resp = await client.put(
            f"/api/users/{user_id}",
            json={"role": "architect"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "architect"

    async def test_deactivate_user(self, client: httpx.AsyncClient) -> None:
        headers = await _admin_headers(client)
        create_resp = await client.post(
            "/api/users",
            json={
                "username": "deactivatable",
                "password": "SecurePass123!",
                "role": "viewer",
            },
            headers=headers,
        )
        user_id = create_resp.json()["id"]
        resp = await client.put(
            f"/api/users/{user_id}",
            json={"is_active": False},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    async def test_update_nonexistent_returns_404(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        resp = await client.put(
            "/api/users/nonexistent",
            json={"role": "admin"},
            headers=headers,
        )
        assert resp.status_code == 404
