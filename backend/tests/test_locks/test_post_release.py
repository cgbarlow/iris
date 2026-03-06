"""Tests for POST lock release endpoint (ADR-086 sendBeacon compatibility)."""

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


async def _auth_headers(client: httpx.AsyncClient) -> dict[str, str]:
    await client.post(
        "/api/auth/setup",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


class TestPostRelease:
    """Verify POST /api/locks/{lock_id}/release works for sendBeacon."""

    @pytest.mark.anyio
    async def test_post_release_own_lock(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        # Acquire a lock
        create_resp = await client.post(
            "/api/locks",
            json={"target_type": "diagram", "target_id": "post-release-test"},
            headers=headers,
        )
        assert create_resp.status_code == 200
        lock_id = create_resp.json()["id"]

        # Release via POST (sendBeacon style)
        release_resp = await client.post(
            f"/api/locks/{lock_id}/release",
            headers=headers,
        )
        assert release_resp.status_code == 204

        # Verify unlocked
        check_resp = await client.get(
            "/api/locks/check?target_type=diagram&target_id=post-release-test",
            headers=headers,
        )
        assert check_resp.json()["locked"] is False

    @pytest.mark.anyio
    async def test_post_release_nonexistent_lock(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/locks/nonexistent-id/release",
            headers=headers,
        )
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_post_release_not_owner(self, client: httpx.AsyncClient) -> None:
        admin_headers = await _auth_headers(client)
        # Create second user
        await client.post(
            "/api/users",
            json={"username": "user2", "password": "User2Pass123!", "role": "architect"},
            headers=admin_headers,
        )
        user2_resp = await client.post(
            "/api/auth/login",
            json={"username": "user2", "password": "User2Pass123!"},
        )
        user2_headers = {"Authorization": f"Bearer {user2_resp.json()['access_token']}"}

        # Admin acquires lock
        create_resp = await client.post(
            "/api/locks",
            json={"target_type": "diagram", "target_id": "post-release-other"},
            headers=admin_headers,
        )
        lock_id = create_resp.json()["id"]

        # User2 tries to release via POST
        resp = await client.post(
            f"/api/locks/{lock_id}/release",
            headers=user2_headers,
        )
        assert resp.status_code == 404  # not found or not owned
