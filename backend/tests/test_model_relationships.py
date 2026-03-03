"""Tests for model relationships per SPEC-066-A (TDD — written before service)."""

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


async def _create_model(client: httpx.AsyncClient, headers: dict, name: str) -> str:
    """Create a model and return its id."""
    resp = await client.post(
        "/api/models",
        json={"model_type": "uml", "name": name},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


class TestModelRelationships:
    """Verify model relationship CRUD via API."""

    async def test_create_model_relationship(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        model_a = await _create_model(client, headers, "Model A")
        model_b = await _create_model(client, headers, "Model B")

        resp = await client.post(
            f"/api/models/{model_a}/relationships",
            json={
                "target_model_id": model_b,
                "relationship_type": "dependency",
                "label": "depends on",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["source_model_id"] == model_a
        assert data["target_model_id"] == model_b
        assert data["relationship_type"] == "dependency"
        assert data["label"] == "depends on"

    async def test_list_model_relationships(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        model_a = await _create_model(client, headers, "List Model A")
        model_b = await _create_model(client, headers, "List Model B")

        await client.post(
            f"/api/models/{model_a}/relationships",
            json={
                "target_model_id": model_b,
                "relationship_type": "dependency",
            },
            headers=headers,
        )

        resp = await client.get(
            f"/api/models/{model_a}/relationships",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "model_relationships" in data
        assert "entity_relationships" in data
        rels = data["model_relationships"]
        assert len(rels) >= 1
        assert rels[0]["source_model_id"] == model_a
        assert rels[0]["source_name"] == "List Model A"
        assert rels[0]["target_name"] == "List Model B"

    async def test_delete_model_relationship(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        model_a = await _create_model(client, headers, "Del Model A")
        model_b = await _create_model(client, headers, "Del Model B")

        create_resp = await client.post(
            f"/api/models/{model_a}/relationships",
            json={
                "target_model_id": model_b,
                "relationship_type": "dependency",
            },
            headers=headers,
        )
        rel_id = create_resp.json()["id"]

        del_resp = await client.delete(
            f"/api/model-relationships/{rel_id}",
            headers=headers,
        )
        assert del_resp.status_code == 204

        # Verify gone
        list_resp = await client.get(
            f"/api/models/{model_a}/relationships",
            headers=headers,
        )
        assert len(list_resp.json()["model_relationships"]) == 0

    async def test_duplicate_model_relationship(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        model_a = await _create_model(client, headers, "Dup Model A")
        model_b = await _create_model(client, headers, "Dup Model B")

        await client.post(
            f"/api/models/{model_a}/relationships",
            json={
                "target_model_id": model_b,
                "relationship_type": "dependency",
            },
            headers=headers,
        )

        # Second create with same type should 409
        resp = await client.post(
            f"/api/models/{model_a}/relationships",
            json={
                "target_model_id": model_b,
                "relationship_type": "dependency",
            },
            headers=headers,
        )
        assert resp.status_code == 409

    async def test_model_relationship_not_found_delete(
        self, client: httpx.AsyncClient
    ) -> None:
        headers = await _auth_headers(client)

        # Delete nonexistent relationship returns 404
        del_resp = await client.delete(
            "/api/model-relationships/nonexistent-id",
            headers=headers,
        )
        assert del_resp.status_code == 404

    async def test_auto_create_model_relationship_on_canvas_save(
        self, client: httpx.AsyncClient
    ) -> None:
        """PUT model with two modelref nodes + edge → model_relationships row created."""
        headers = await _auth_headers(client)
        model_a = await _create_model(client, headers, "Canvas Model A")
        model_b = await _create_model(client, headers, "Canvas Model B")
        model_c = await _create_model(client, headers, "Canvas Model C")

        # Save model_c with canvas containing modelref nodes for A and B, plus an edge
        canvas_data = {
            "nodes": [
                {
                    "id": "node-a",
                    "type": "modelref",
                    "position": {"x": 0, "y": 0},
                    "data": {
                        "label": "Model A",
                        "entityType": "component",
                        "linkedModelId": model_a,
                    },
                },
                {
                    "id": "node-b",
                    "type": "modelref",
                    "position": {"x": 200, "y": 0},
                    "data": {
                        "label": "Model B",
                        "entityType": "component",
                        "linkedModelId": model_b,
                    },
                },
            ],
            "edges": [
                {
                    "id": "e-a-b",
                    "source": "node-a",
                    "target": "node-b",
                    "type": "uses",
                    "data": {"relationshipType": "dependency"},
                },
            ],
        }

        resp = await client.put(
            f"/api/models/{model_c}",
            json={
                "name": "Canvas Model C",
                "description": "",
                "data": canvas_data,
                "change_summary": "Added modelref edges",
            },
            headers={**headers, "If-Match": "1"},
        )
        assert resp.status_code == 200

        # Verify model_relationships row was created
        # Query model_a's relationships (since the auto-created relationship is A → B)
        rel_resp = await client.get(
            f"/api/models/{model_a}/relationships",
            headers=headers,
        )
        assert rel_resp.status_code == 200
        rels = rel_resp.json()["model_relationships"]
        matching = [
            r for r in rels
            if r["source_model_id"] == model_a and r["target_model_id"] == model_b
        ]
        assert len(matching) == 1
        assert matching[0]["relationship_type"] == "dependency"

    async def test_auto_create_model_relationship_no_duplicate(
        self, client: httpx.AsyncClient
    ) -> None:
        """Saving canvas twice with same modelref edge → only one model_relationships row."""
        headers = await _auth_headers(client)
        model_a = await _create_model(client, headers, "NoDup Model A")
        model_b = await _create_model(client, headers, "NoDup Model B")
        model_c = await _create_model(client, headers, "NoDup Model C")

        canvas_data = {
            "nodes": [
                {
                    "id": "n1",
                    "type": "modelref",
                    "position": {"x": 0, "y": 0},
                    "data": {"label": "A", "entityType": "component", "linkedModelId": model_a},
                },
                {
                    "id": "n2",
                    "type": "modelref",
                    "position": {"x": 200, "y": 0},
                    "data": {"label": "B", "entityType": "component", "linkedModelId": model_b},
                },
            ],
            "edges": [
                {
                    "id": "e1",
                    "source": "n1",
                    "target": "n2",
                    "type": "uses",
                    "data": {"relationshipType": "uses"},
                },
            ],
        }

        # First save
        resp1 = await client.put(
            f"/api/models/{model_c}",
            json={"name": "NoDup Model C", "description": "", "data": canvas_data, "change_summary": "save 1"},
            headers={**headers, "If-Match": "1"},
        )
        assert resp1.status_code == 200

        # Second save (same edges)
        resp2 = await client.put(
            f"/api/models/{model_c}",
            json={"name": "NoDup Model C", "description": "", "data": canvas_data, "change_summary": "save 2"},
            headers={**headers, "If-Match": "2"},
        )
        assert resp2.status_code == 200

        # Verify only one relationship exists (query model_a)
        rel_resp = await client.get(
            f"/api/models/{model_a}/relationships",
            headers=headers,
        )
        rels = rel_resp.json()["model_relationships"]
        matching = [
            r for r in rels
            if r["source_model_id"] == model_a and r["target_model_id"] == model_b
            and r["relationship_type"] == "uses"
        ]
        assert len(matching) == 1
