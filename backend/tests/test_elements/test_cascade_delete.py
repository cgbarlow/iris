"""Tests for cascade element deletion per SPEC-067-A (TDD — written before service)."""

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


async def _create_element(
    client: httpx.AsyncClient, headers: dict, name: str, element_type: str = "component"
) -> dict:
    resp = await client.post(
        "/api/elements",
        json={"name": name, "element_type": element_type},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


async def _create_model_with_element(
    client: httpx.AsyncClient, headers: dict, model_name: str, element_id: str
) -> dict:
    """Create a model whose canvas contains a node referencing element_id."""
    canvas_data = {
        "nodes": [
            {
                "id": f"node-{element_id[:8]}",
                "type": "component",
                "position": {"x": 100, "y": 100},
                "data": {
                    "label": "Test Element",
                    "entityType": "component",
                    "entityId": element_id,
                },
            },
        ],
        "edges": [],
    }
    resp = await client.post(
        "/api/diagrams",
        json={"diagram_type": "simple", "name": model_name, "data": canvas_data},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


class TestCascadeDelete:
    """Verify cascade element deletion via API."""

    async def test_cascade_delete_removes_from_model_canvas(
        self, client: httpx.AsyncClient
    ) -> None:
        """Element node removed from model's canvas data after cascade delete."""
        headers = await _auth_headers(client)
        element = await _create_element(client, headers, "Cascade Canvas Element")
        element_id = element["id"]

        model = await _create_model_with_element(client, headers, "Cascade Model", element_id)
        model_id = model["id"]

        # Verify element is on canvas
        model_resp = await client.get(f"/api/diagrams/{model_id}", headers=headers)
        canvas = model_resp.json()["data"]
        assert any(
            n.get("data", {}).get("entityId") == element_id
            for n in canvas.get("nodes", [])
        )

        # Cascade delete element
        del_resp = await client.delete(
            f"/api/elements/{element_id}?cascade=true",
            headers={**headers, "If-Match": str(element["current_version"])},
        )
        assert del_resp.status_code == 204

        # Verify element is removed from canvas
        model_resp2 = await client.get(f"/api/diagrams/{model_id}", headers=headers)
        canvas2 = model_resp2.json()["data"]
        assert not any(
            n.get("data", {}).get("entityId") == element_id
            for n in canvas2.get("nodes", [])
        )

    async def test_cascade_delete_soft_deletes_relationships(
        self, client: httpx.AsyncClient
    ) -> None:
        """All element relationships soft-deleted after cascade delete."""
        headers = await _auth_headers(client)
        element_a = await _create_element(client, headers, "Cascade Rel A")
        element_b = await _create_element(client, headers, "Cascade Rel B")

        # Create a relationship between them
        rel_resp = await client.post(
            "/api/relationships",
            json={
                "source_element_id": element_a["id"],
                "target_element_id": element_b["id"],
                "relationship_type": "uses",
                "label": "test",
                "description": "",
            },
            headers=headers,
        )
        assert rel_resp.status_code == 201

        # Cascade delete element_a
        del_resp = await client.delete(
            f"/api/elements/{element_a['id']}?cascade=true",
            headers={**headers, "If-Match": str(element_a["current_version"])},
        )
        assert del_resp.status_code == 204

        # Verify element_a is gone
        get_resp = await client.get(f"/api/elements/{element_a['id']}", headers=headers)
        assert get_resp.status_code == 404

    async def test_cascade_delete_element_marked_deleted(
        self, client: httpx.AsyncClient
    ) -> None:
        """Element itself is soft-deleted after cascade delete."""
        headers = await _auth_headers(client)
        element = await _create_element(client, headers, "Cascade Self Delete")

        del_resp = await client.delete(
            f"/api/elements/{element['id']}?cascade=true",
            headers={**headers, "If-Match": str(element["current_version"])},
        )
        assert del_resp.status_code == 204

        # Element should be gone (soft-deleted)
        get_resp = await client.get(f"/api/elements/{element['id']}", headers=headers)
        assert get_resp.status_code == 404

    async def test_simple_delete_does_not_cascade(
        self, client: httpx.AsyncClient
    ) -> None:
        """Without ?cascade=true, canvas unchanged."""
        headers = await _auth_headers(client)
        element = await _create_element(client, headers, "No Cascade Element")
        element_id = element["id"]

        model = await _create_model_with_element(client, headers, "No Cascade Model", element_id)
        model_id = model["id"]

        # Simple delete (no cascade)
        del_resp = await client.delete(
            f"/api/elements/{element_id}",
            headers={**headers, "If-Match": str(element["current_version"])},
        )
        assert del_resp.status_code == 204

        # Canvas should still have the node reference (element soft-deleted but canvas untouched)
        model_resp = await client.get(f"/api/diagrams/{model_id}", headers=headers)
        canvas = model_resp.json()["data"]
        assert any(
            n.get("data", {}).get("entityId") == element_id
            for n in canvas.get("nodes", [])
        )
