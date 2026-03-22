"""Tests for diagram relationships endpoint — entity-to-entity relationships displayed
in the Relationships tab (Issue #4, ADR-097, SPEC-097-A).

TDD: written before the fix.
"""

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
    db_manager = DatabaseManager(app_config)
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


async def _create_element(
    client: httpx.AsyncClient, headers: dict, name: str, element_type: str = "component"
) -> str:
    """Create an element and return its id."""
    resp = await client.post(
        "/api/elements",
        json={"element_type": element_type, "name": name},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


class TestDiagramElementRelationships:
    """Verify that element-to-element relationships appear in the diagram relationships endpoint."""

    async def test_element_relationships_returned_for_diagram(
        self, client: httpx.AsyncClient
    ) -> None:
        """Elements on a diagram's canvas with relationships should appear in
        GET /api/diagrams/{id}/relationships under element_relationships."""
        headers = await _auth_headers(client)

        # 1. Create two elements
        elem_a = await _create_element(client, headers, "Service A")
        elem_b = await _create_element(client, headers, "Service B")

        # 2. Create a relationship between them
        rel_resp = await client.post(
            "/api/relationships",
            json={
                "source_element_id": elem_a,
                "target_element_id": elem_b,
                "relationship_type": "uses",
                "label": "calls",
            },
            headers=headers,
        )
        assert rel_resp.status_code == 201
        rel_id = rel_resp.json()["id"]

        # 3. Create a diagram with canvas nodes referencing those elements via entityId
        diag_resp = await client.post(
            "/api/diagrams",
            json={"diagram_type": "component", "name": "Test Diagram"},
            headers=headers,
        )
        assert diag_resp.status_code == 201
        diagram_id = diag_resp.json()["id"]

        canvas_data = {
            "nodes": [
                {
                    "id": "n1",
                    "type": "default",
                    "position": {"x": 0, "y": 0},
                    "data": {
                        "label": "Service A",
                        "entityType": "component",
                        "entityId": elem_a,
                    },
                },
                {
                    "id": "n2",
                    "type": "default",
                    "position": {"x": 200, "y": 0},
                    "data": {
                        "label": "Service B",
                        "entityType": "component",
                        "entityId": elem_b,
                    },
                },
            ],
            "edges": [],
        }

        put_resp = await client.put(
            f"/api/diagrams/{diagram_id}",
            json={
                "name": "Test Diagram",
                "description": "",
                "data": canvas_data,
                "change_summary": "Added entity nodes",
            },
            headers={**headers, "If-Match": "1"},
        )
        assert put_resp.status_code == 200

        # 4. Fetch diagram relationships
        rels_resp = await client.get(
            f"/api/diagrams/{diagram_id}/relationships",
            headers=headers,
        )
        assert rels_resp.status_code == 200
        data = rels_resp.json()

        # 5. Assert element_relationships contains the relationship
        element_rels = data["element_relationships"]
        assert len(element_rels) >= 1, (
            f"Expected at least 1 element relationship, got {len(element_rels)}"
        )
        matching = [r for r in element_rels if r["id"] == rel_id]
        assert len(matching) == 1
        assert matching[0]["source_element_id"] == elem_a
        assert matching[0]["target_element_id"] == elem_b
        assert matching[0]["relationship_type"] == "uses"
        assert matching[0]["source_name"] == "Service A"
        assert matching[0]["target_name"] == "Service B"

    async def test_no_element_relationships_when_no_entities(
        self, client: httpx.AsyncClient
    ) -> None:
        """A diagram with no entity nodes should return empty element_relationships."""
        headers = await _auth_headers(client)

        diag_resp = await client.post(
            "/api/diagrams",
            json={"diagram_type": "component", "name": "Empty Diagram"},
            headers=headers,
        )
        assert diag_resp.status_code == 201
        diagram_id = diag_resp.json()["id"]

        rels_resp = await client.get(
            f"/api/diagrams/{diagram_id}/relationships",
            headers=headers,
        )
        assert rels_resp.status_code == 200
        data = rels_resp.json()
        assert data["element_relationships"] == []

    async def test_element_relationships_only_for_canvas_entities(
        self, client: httpx.AsyncClient
    ) -> None:
        """Only relationships involving entities on the canvas should be returned,
        not all relationships in the system."""
        headers = await _auth_headers(client)

        # Create three elements: A, B, C
        elem_a = await _create_element(client, headers, "Entity A")
        elem_b = await _create_element(client, headers, "Entity B")
        elem_c = await _create_element(client, headers, "Entity C")

        # Create relationships: A→B and B→C
        await client.post(
            "/api/relationships",
            json={
                "source_element_id": elem_a,
                "target_element_id": elem_b,
                "relationship_type": "uses",
            },
            headers=headers,
        )
        rel_bc = await client.post(
            "/api/relationships",
            json={
                "source_element_id": elem_b,
                "target_element_id": elem_c,
                "relationship_type": "depends_on",
            },
            headers=headers,
        )
        assert rel_bc.status_code == 201

        # Create diagram with only A and B on canvas (not C)
        diag_resp = await client.post(
            "/api/diagrams",
            json={"diagram_type": "component", "name": "Partial Diagram"},
            headers=headers,
        )
        diagram_id = diag_resp.json()["id"]

        canvas_data = {
            "nodes": [
                {
                    "id": "n1",
                    "type": "default",
                    "position": {"x": 0, "y": 0},
                    "data": {"label": "A", "entityType": "component", "entityId": elem_a},
                },
                {
                    "id": "n2",
                    "type": "default",
                    "position": {"x": 200, "y": 0},
                    "data": {"label": "B", "entityType": "component", "entityId": elem_b},
                },
            ],
            "edges": [],
        }

        await client.put(
            f"/api/diagrams/{diagram_id}",
            json={
                "name": "Partial Diagram",
                "description": "",
                "data": canvas_data,
                "change_summary": "A and B only",
            },
            headers={**headers, "If-Match": "1"},
        )

        rels_resp = await client.get(
            f"/api/diagrams/{diagram_id}/relationships",
            headers=headers,
        )
        data = rels_resp.json()
        element_rels = data["element_relationships"]

        # A→B should be found (both on canvas), B→C should also be found
        # because B is on the canvas (the query uses OR, not AND)
        assert len(element_rels) >= 1
        rel_types = {r["relationship_type"] for r in element_rels}
        assert "uses" in rel_types
