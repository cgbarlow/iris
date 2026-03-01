"""Integration tests for model CRUD API routes."""

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


async def _create_model(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    *,
    name: str = "Test Model",
    model_type: str = "simple-view",
) -> dict[str, object]:
    """Helper to create a test model."""
    resp = await client.post(
        "/api/models",
        json={
            "model_type": model_type,
            "name": name,
            "description": "A test model",
            "data": {"placements": []},
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


class TestCreateModel:
    """Verify model creation."""

    async def test_create_returns_201(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/models",
            json={"model_type": "simple-view", "name": "My Model", "data": {}},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["current_version"] == 1

    async def test_create_requires_auth(self, client: httpx.AsyncClient) -> None:
        resp = await client.post(
            "/api/models",
            json={"model_type": "simple-view", "name": "test", "data": {}},
        )
        assert resp.status_code == 401


class TestGetModel:
    """Verify model retrieval."""

    async def test_get_model(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        created = await _create_model(client, headers)
        resp = await client.get(
            f"/api/models/{created['id']}", headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Test Model"

    async def test_get_nonexistent_returns_404(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/models/nonexistent", headers=headers)
        assert resp.status_code == 404


class TestListModels:
    """Verify model listing."""

    async def test_list_empty(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/models", headers=headers)
        assert resp.json()["total"] == 0

    async def test_filter_by_type(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        await _create_model(client, headers, model_type="simple-view")
        await _create_model(client, headers, model_type="uml-class")
        resp = await client.get(
            "/api/models?model_type=uml-class", headers=headers,
        )
        assert resp.json()["total"] == 1


class TestUpdateModel:
    """Verify model update."""

    async def test_update_success(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        created = await _create_model(client, headers)
        resp = await client.put(
            f"/api/models/{created['id']}",
            json={"name": "Updated", "data": {"placements": [{"id": "1"}]}},
            headers={**headers, "If-Match": "1"},
        )
        assert resp.status_code == 200
        assert resp.json()["current_version"] == 2

    async def test_update_conflict(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        created = await _create_model(client, headers)
        resp = await client.put(
            f"/api/models/{created['id']}",
            json={"name": "New", "data": {}},
            headers={**headers, "If-Match": "99"},
        )
        assert resp.status_code == 409


class TestDeleteModel:
    """Verify model soft-delete."""

    async def test_soft_delete(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        created = await _create_model(client, headers)
        resp = await client.delete(
            f"/api/models/{created['id']}",
            headers={**headers, "If-Match": "1"},
        )
        assert resp.status_code == 204

    async def test_deleted_not_found(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        created = await _create_model(client, headers)
        await client.delete(
            f"/api/models/{created['id']}",
            headers={**headers, "If-Match": "1"},
        )
        resp = await client.get(
            f"/api/models/{created['id']}", headers=headers,
        )
        assert resp.status_code == 404


class TestModelVersions:
    """Verify version history."""

    async def test_get_versions(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        created = await _create_model(client, headers)
        resp = await client.get(
            f"/api/models/{created['id']}/versions", headers=headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["change_type"] == "create"


class TestModelUsernameResolution:
    """Verify GUID-to-username resolution in model responses (ADR-031)."""

    async def test_get_model_returns_created_by_username(
        self, client: httpx.AsyncClient
    ) -> None:
        headers = await _auth_headers(client)
        created = await _create_model(client, headers)
        resp = await client.get(
            f"/api/models/{created['id']}", headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "created_by_username" in data
        assert data["created_by_username"] == "admin"

    async def test_model_versions_return_created_by_username(
        self, client: httpx.AsyncClient
    ) -> None:
        headers = await _auth_headers(client)
        created = await _create_model(client, headers)
        resp = await client.get(
            f"/api/models/{created['id']}/versions", headers=headers,
        )
        assert resp.status_code == 200
        versions = resp.json()
        assert len(versions) >= 1
        for v in versions:
            assert "created_by_username" in v
            assert v["created_by_username"] == "admin"
