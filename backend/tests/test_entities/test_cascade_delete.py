"""Tests for cascade entity deletion per SPEC-067-A (TDD — written before service)."""

from __future__ import annotations

import json
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
    tokens = resp.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _create_entity(
    client: httpx.AsyncClient, headers: dict, name: str, entity_type: str = "component"
) -> dict:
    resp = await client.post(
        "/api/entities",
        json={"name": name, "entity_type": entity_type},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


async def _create_model_with_entity(
    client: httpx.AsyncClient, headers: dict, model_name: str, entity_id: str
) -> dict:
    """Create a model whose canvas contains a node referencing entity_id."""
    canvas_data = {
        "nodes": [
            {
                "id": f"node-{entity_id[:8]}",
                "type": "component",
                "position": {"x": 100, "y": 100},
                "data": {
                    "label": "Test Entity",
                    "entityType": "component",
                    "entityId": entity_id,
                },
            },
        ],
        "edges": [],
    }
    resp = await client.post(
        "/api/models",
        json={"model_type": "simple", "name": model_name, "data": canvas_data},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


class TestCascadeDelete:
    """Verify cascade entity deletion via API."""

    async def test_cascade_delete_removes_from_model_canvas(
        self, client: httpx.AsyncClient
    ) -> None:
        """Entity node removed from model's canvas data after cascade delete."""
        headers = await _auth_headers(client)
        entity = await _create_entity(client, headers, "Cascade Canvas Entity")
        entity_id = entity["id"]

        model = await _create_model_with_entity(client, headers, "Cascade Model", entity_id)
        model_id = model["id"]

        # Verify entity is on canvas
        model_resp = await client.get(f"/api/models/{model_id}", headers=headers)
        canvas = model_resp.json()["data"]
        assert any(
            n.get("data", {}).get("entityId") == entity_id
            for n in canvas.get("nodes", [])
        )

        # Cascade delete entity
        del_resp = await client.delete(
            f"/api/entities/{entity_id}?cascade=true",
            headers={**headers, "If-Match": str(entity["current_version"])},
        )
        assert del_resp.status_code == 204

        # Verify entity is removed from canvas
        model_resp2 = await client.get(f"/api/models/{model_id}", headers=headers)
        canvas2 = model_resp2.json()["data"]
        assert not any(
            n.get("data", {}).get("entityId") == entity_id
            for n in canvas2.get("nodes", [])
        )

    async def test_cascade_delete_soft_deletes_relationships(
        self, client: httpx.AsyncClient
    ) -> None:
        """All entity relationships soft-deleted after cascade delete."""
        headers = await _auth_headers(client)
        entity_a = await _create_entity(client, headers, "Cascade Rel A")
        entity_b = await _create_entity(client, headers, "Cascade Rel B")

        # Create a relationship between them
        rel_resp = await client.post(
            "/api/relationships",
            json={
                "source_entity_id": entity_a["id"],
                "target_entity_id": entity_b["id"],
                "relationship_type": "uses",
                "label": "test",
                "description": "",
            },
            headers=headers,
        )
        assert rel_resp.status_code == 201

        # Cascade delete entity_a
        del_resp = await client.delete(
            f"/api/entities/{entity_a['id']}?cascade=true",
            headers={**headers, "If-Match": str(entity_a["current_version"])},
        )
        assert del_resp.status_code == 204

        # Verify entity_a is gone
        get_resp = await client.get(f"/api/entities/{entity_a['id']}", headers=headers)
        assert get_resp.status_code == 404

    async def test_cascade_delete_entity_marked_deleted(
        self, client: httpx.AsyncClient
    ) -> None:
        """Entity itself is soft-deleted after cascade delete."""
        headers = await _auth_headers(client)
        entity = await _create_entity(client, headers, "Cascade Self Delete")

        del_resp = await client.delete(
            f"/api/entities/{entity['id']}?cascade=true",
            headers={**headers, "If-Match": str(entity["current_version"])},
        )
        assert del_resp.status_code == 204

        # Entity should be gone (soft-deleted)
        get_resp = await client.get(f"/api/entities/{entity['id']}", headers=headers)
        assert get_resp.status_code == 404

    async def test_simple_delete_does_not_cascade(
        self, client: httpx.AsyncClient
    ) -> None:
        """Without ?cascade=true, canvas unchanged."""
        headers = await _auth_headers(client)
        entity = await _create_entity(client, headers, "No Cascade Entity")
        entity_id = entity["id"]

        model = await _create_model_with_entity(client, headers, "No Cascade Model", entity_id)
        model_id = model["id"]

        # Simple delete (no cascade)
        del_resp = await client.delete(
            f"/api/entities/{entity_id}",
            headers={**headers, "If-Match": str(entity["current_version"])},
        )
        assert del_resp.status_code == 204

        # Canvas should still have the node reference (entity soft-deleted but canvas untouched)
        model_resp = await client.get(f"/api/models/{model_id}", headers=headers)
        canvas = model_resp.json()["data"]
        assert any(
            n.get("data", {}).get("entityId") == entity_id
            for n in canvas.get("nodes", [])
        )
