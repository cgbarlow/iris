"""Integration tests for entity CRUD API routes."""

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
    """Setup admin user and return auth headers."""
    await client.post(
        "/api/auth/setup",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    tokens = resp.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _create_entity(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    *,
    name: str = "Test Entity",
    entity_type: str = "application",
) -> dict[str, object]:
    """Helper to create a test entity."""
    resp = await client.post(
        "/api/entities",
        json={
            "entity_type": entity_type,
            "name": name,
            "description": "A test entity",
            "data": {"key": "value"},
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


class TestCreateEntity:
    """Verify entity creation."""

    async def test_create_returns_201(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/entities",
            json={
                "entity_type": "application",
                "name": "My App",
                "data": {},
            },
            headers=headers,
        )
        assert resp.status_code == 201

    async def test_create_returns_entity_data(
        self, client: httpx.AsyncClient
    ) -> None:
        headers = await _auth_headers(client)
        entity = await _create_entity(client, headers)
        assert entity["name"] == "Test Entity"
        assert entity["entity_type"] == "application"
        assert entity["current_version"] == 1

    async def test_create_requires_auth(self, client: httpx.AsyncClient) -> None:
        resp = await client.post(
            "/api/entities",
            json={"entity_type": "app", "name": "test", "data": {}},
        )
        assert resp.status_code == 401


class TestGetEntity:
    """Verify entity retrieval."""

    async def test_get_entity(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        created = await _create_entity(client, headers)
        resp = await client.get(
            f"/api/entities/{created['id']}", headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Test Entity"

    async def test_get_nonexistent_returns_404(
        self, client: httpx.AsyncClient
    ) -> None:
        headers = await _auth_headers(client)
        resp = await client.get(
            "/api/entities/nonexistent-id", headers=headers,
        )
        assert resp.status_code == 404


class TestListEntities:
    """Verify entity listing."""

    async def test_list_empty(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/entities", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    async def test_list_with_entities(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        await _create_entity(client, headers, name="A")
        await _create_entity(client, headers, name="B")
        resp = await client.get("/api/entities", headers=headers)
        assert resp.json()["total"] == 2

    async def test_filter_by_type(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        await _create_entity(client, headers, entity_type="application")
        await _create_entity(client, headers, entity_type="service")
        resp = await client.get(
            "/api/entities?entity_type=service", headers=headers,
        )
        assert resp.json()["total"] == 1


class TestUpdateEntity:
    """Verify entity update with OCC."""

    async def test_update_success(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        created = await _create_entity(client, headers)
        resp = await client.put(
            f"/api/entities/{created['id']}",
            json={"name": "Updated Name", "data": {"new": "data"}},
            headers={**headers, "If-Match": "1"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"
        assert resp.json()["current_version"] == 2

    async def test_update_version_conflict(
        self, client: httpx.AsyncClient
    ) -> None:
        headers = await _auth_headers(client)
        created = await _create_entity(client, headers)
        resp = await client.put(
            f"/api/entities/{created['id']}",
            json={"name": "New", "data": {}},
            headers={**headers, "If-Match": "99"},
        )
        assert resp.status_code == 409

    async def test_update_requires_if_match(
        self, client: httpx.AsyncClient
    ) -> None:
        headers = await _auth_headers(client)
        created = await _create_entity(client, headers)
        resp = await client.put(
            f"/api/entities/{created['id']}",
            json={"name": "New", "data": {}},
            headers=headers,
        )
        assert resp.status_code == 428


class TestRollbackEntity:
    """Verify entity rollback."""

    async def test_rollback_to_version_1(
        self, client: httpx.AsyncClient
    ) -> None:
        headers = await _auth_headers(client)
        created = await _create_entity(client, headers)
        # Update to v2
        await client.put(
            f"/api/entities/{created['id']}",
            json={"name": "V2 Name", "data": {}},
            headers={**headers, "If-Match": "1"},
        )
        # Rollback to v1
        resp = await client.post(
            f"/api/entities/{created['id']}/rollback",
            json={"target_version": 1},
            headers={**headers, "If-Match": "2"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Test Entity"
        assert resp.json()["current_version"] == 3

    async def test_rollback_creates_new_version(
        self, client: httpx.AsyncClient
    ) -> None:
        headers = await _auth_headers(client)
        created = await _create_entity(client, headers)
        await client.put(
            f"/api/entities/{created['id']}",
            json={"name": "V2", "data": {}},
            headers={**headers, "If-Match": "1"},
        )
        await client.post(
            f"/api/entities/{created['id']}/rollback",
            json={"target_version": 1},
            headers={**headers, "If-Match": "2"},
        )
        resp = await client.get(
            f"/api/entities/{created['id']}/versions", headers=headers,
        )
        versions = resp.json()
        assert len(versions) == 3
        assert versions[0]["change_type"] == "rollback"


class TestDeleteEntity:
    """Verify entity soft-delete."""

    async def test_soft_delete(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        created = await _create_entity(client, headers)
        resp = await client.delete(
            f"/api/entities/{created['id']}",
            headers={**headers, "If-Match": "1"},
        )
        assert resp.status_code == 204

    async def test_deleted_entity_not_found(
        self, client: httpx.AsyncClient
    ) -> None:
        headers = await _auth_headers(client)
        created = await _create_entity(client, headers)
        await client.delete(
            f"/api/entities/{created['id']}",
            headers={**headers, "If-Match": "1"},
        )
        resp = await client.get(
            f"/api/entities/{created['id']}", headers=headers,
        )
        assert resp.status_code == 404


class TestEntityVersionHistory:
    """Verify version history endpoints."""

    async def test_get_versions(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        created = await _create_entity(client, headers)
        resp = await client.get(
            f"/api/entities/{created['id']}/versions", headers=headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    async def test_get_specific_version(
        self, client: httpx.AsyncClient
    ) -> None:
        headers = await _auth_headers(client)
        created = await _create_entity(client, headers)
        resp = await client.get(
            f"/api/entities/{created['id']}/versions/1", headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["version"] == 1

    async def test_nonexistent_version_returns_404(
        self, client: httpx.AsyncClient
    ) -> None:
        headers = await _auth_headers(client)
        created = await _create_entity(client, headers)
        resp = await client.get(
            f"/api/entities/{created['id']}/versions/99", headers=headers,
        )
        assert resp.status_code == 404
