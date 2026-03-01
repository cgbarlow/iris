"""Integration tests for relationship CRUD API routes."""

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


async def _create_two_entities(
    client: httpx.AsyncClient, headers: dict[str, str],
) -> tuple[str, str]:
    """Create two entities and return their IDs."""
    r1 = await client.post(
        "/api/entities",
        json={"entity_type": "application", "name": "App A", "data": {}},
        headers=headers,
    )
    r2 = await client.post(
        "/api/entities",
        json={"entity_type": "service", "name": "Service B", "data": {}},
        headers=headers,
    )
    return r1.json()["id"], r2.json()["id"]


async def _create_relationship(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    source_id: str,
    target_id: str,
) -> dict[str, object]:
    """Helper to create a test relationship."""
    resp = await client.post(
        "/api/relationships",
        json={
            "source_entity_id": source_id,
            "target_entity_id": target_id,
            "relationship_type": "uses",
            "label": "Uses service",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


class TestCreateRelationship:
    """Verify relationship creation."""

    async def test_create_returns_201(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        src, tgt = await _create_two_entities(client, headers)
        resp = await client.post(
            "/api/relationships",
            json={
                "source_entity_id": src,
                "target_entity_id": tgt,
                "relationship_type": "uses",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["current_version"] == 1

    async def test_create_requires_auth(self, client: httpx.AsyncClient) -> None:
        resp = await client.post(
            "/api/relationships",
            json={
                "source_entity_id": "a",
                "target_entity_id": "b",
                "relationship_type": "uses",
            },
        )
        assert resp.status_code == 401


class TestGetRelationship:
    """Verify relationship retrieval."""

    async def test_get_relationship(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        src, tgt = await _create_two_entities(client, headers)
        created = await _create_relationship(client, headers, src, tgt)
        resp = await client.get(
            f"/api/relationships/{created['id']}", headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["relationship_type"] == "uses"

    async def test_get_nonexistent_returns_404(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        resp = await client.get(
            "/api/relationships/nonexistent", headers=headers,
        )
        assert resp.status_code == 404


class TestListRelationships:
    """Verify relationship listing."""

    async def test_list_empty(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/relationships", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    async def test_filter_by_entity(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        src, tgt = await _create_two_entities(client, headers)
        await _create_relationship(client, headers, src, tgt)
        resp = await client.get(
            f"/api/relationships?entity_id={src}", headers=headers,
        )
        assert resp.json()["total"] == 1


class TestUpdateRelationship:
    """Verify relationship update."""

    async def test_update_success(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        src, tgt = await _create_two_entities(client, headers)
        created = await _create_relationship(client, headers, src, tgt)
        resp = await client.put(
            f"/api/relationships/{created['id']}",
            json={"label": "Updated label", "data": {}},
            headers={**headers, "If-Match": "1"},
        )
        assert resp.status_code == 200
        assert resp.json()["label"] == "Updated label"
        assert resp.json()["current_version"] == 2

    async def test_update_version_conflict(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        src, tgt = await _create_two_entities(client, headers)
        created = await _create_relationship(client, headers, src, tgt)
        resp = await client.put(
            f"/api/relationships/{created['id']}",
            json={"label": "New", "data": {}},
            headers={**headers, "If-Match": "99"},
        )
        assert resp.status_code == 409


class TestDeleteRelationship:
    """Verify relationship soft-delete."""

    async def test_soft_delete(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        src, tgt = await _create_two_entities(client, headers)
        created = await _create_relationship(client, headers, src, tgt)
        resp = await client.delete(
            f"/api/relationships/{created['id']}",
            headers={**headers, "If-Match": "1"},
        )
        assert resp.status_code == 204

    async def test_deleted_not_found(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        src, tgt = await _create_two_entities(client, headers)
        created = await _create_relationship(client, headers, src, tgt)
        await client.delete(
            f"/api/relationships/{created['id']}",
            headers={**headers, "If-Match": "1"},
        )
        resp = await client.get(
            f"/api/relationships/{created['id']}", headers=headers,
        )
        assert resp.status_code == 404


class TestRelationshipEntityNameResolution:
    """Verify entity name resolution in relationship responses (ADR-031)."""

    async def test_list_relationships_returns_entity_names(
        self, client: httpx.AsyncClient
    ) -> None:
        headers = await _auth_headers(client)
        src, tgt = await _create_two_entities(client, headers)
        await _create_relationship(client, headers, src, tgt)
        resp = await client.get(
            f"/api/relationships?entity_id={src}", headers=headers,
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        rel = items[0]
        assert "source_entity_name" in rel
        assert "target_entity_name" in rel
        assert rel["source_entity_name"] == "App A"
        assert rel["target_entity_name"] == "Service B"

    async def test_get_relationship_returns_entity_names(
        self, client: httpx.AsyncClient
    ) -> None:
        headers = await _auth_headers(client)
        src, tgt = await _create_two_entities(client, headers)
        created = await _create_relationship(client, headers, src, tgt)
        resp = await client.get(
            f"/api/relationships/{created['id']}", headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "source_entity_name" in data
        assert "target_entity_name" in data
        assert data["source_entity_name"] == "App A"
        assert data["target_entity_name"] == "Service B"

    async def test_entity_names_default_empty_for_missing_entities(
        self, client: httpx.AsyncClient
    ) -> None:
        """Verify entity names fall back to empty string for deleted entities."""
        headers = await _auth_headers(client)
        src, tgt = await _create_two_entities(client, headers)
        created = await _create_relationship(client, headers, src, tgt)
        # Soft-delete the source entity
        # First get the entity to know its version
        src_resp = await client.get(
            f"/api/entities/{src}", headers=headers,
        )
        src_version = src_resp.json()["current_version"]
        await client.delete(
            f"/api/entities/{src}",
            headers={**headers, "If-Match": str(src_version)},
        )
        # The relationship should still exist and source name should be empty
        resp = await client.get(
            f"/api/relationships/{created['id']}", headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        # Source entity was deleted (is_deleted=1), so name should be empty
        assert data["source_entity_name"] == ""
        # Target entity still exists, so name should be present
        assert data["target_entity_name"] == "Service B"
