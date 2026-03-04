"""Integration tests for set force-delete functionality."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest

from app.config import AppConfig, AuthConfig, DatabaseConfig
from app.database import DatabaseManager
from app.main import create_app
from app.migrations.m012_sets import DEFAULT_SET_ID
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


class TestForceDeleteSet:
    async def test_force_delete_empty_set(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        create_resp = await client.post(
            "/api/sets",
            json={"name": "Empty Force"},
            headers=headers,
        )
        set_id = create_resp.json()["id"]
        resp = await client.delete(
            f"/api/sets/{set_id}?force=true", headers=headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["diagrams_deleted"] == 0
        assert data["elements_deleted"] == 0

        # Verify set is gone
        get_resp = await client.get(f"/api/sets/{set_id}", headers=headers)
        assert get_resp.status_code == 404

    async def test_force_delete_nonempty_set_returns_counts(
        self, client: httpx.AsyncClient
    ) -> None:
        headers = await _auth_headers(client)
        s = (
            await client.post(
                "/api/sets", json={"name": "Full Force"}, headers=headers
            )
        ).json()
        set_id = s["id"]

        # Create 2 diagrams and 1 element in this set
        await client.post(
            "/api/diagrams",
            json={
                "diagram_type": "simple-view",
                "name": "M1",
                "data": {},
                "set_id": set_id,
            },
            headers=headers,
        )
        await client.post(
            "/api/diagrams",
            json={
                "diagram_type": "simple-view",
                "name": "M2",
                "data": {},
                "set_id": set_id,
            },
            headers=headers,
        )
        await client.post(
            "/api/elements",
            json={
                "element_type": "component",
                "name": "E1",
                "data": {},
                "set_id": set_id,
            },
            headers=headers,
        )

        resp = await client.delete(
            f"/api/sets/{set_id}?force=true", headers=headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["diagrams_deleted"] == 2
        assert data["elements_deleted"] == 1

    async def test_force_delete_default_set_returns_403(
        self, client: httpx.AsyncClient
    ) -> None:
        headers = await _auth_headers(client)
        resp = await client.delete(
            f"/api/sets/{DEFAULT_SET_ID}?force=true", headers=headers
        )
        assert resp.status_code == 403

    async def test_force_delete_nonexistent_returns_404(
        self, client: httpx.AsyncClient
    ) -> None:
        headers = await _auth_headers(client)
        resp = await client.delete(
            "/api/sets/nonexistent-id?force=true", headers=headers
        )
        assert resp.status_code == 404

    async def test_regular_delete_nonempty_still_409(
        self, client: httpx.AsyncClient
    ) -> None:
        headers = await _auth_headers(client)
        s = (
            await client.post(
                "/api/sets", json={"name": "Regular 409"}, headers=headers
            )
        ).json()
        set_id = s["id"]
        await client.post(
            "/api/diagrams",
            json={
                "diagram_type": "simple-view",
                "name": "M1",
                "data": {},
                "set_id": set_id,
            },
            headers=headers,
        )

        # Regular delete (no force) should still be 409
        resp = await client.delete(f"/api/sets/{set_id}", headers=headers)
        assert resp.status_code == 409
