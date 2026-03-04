"""Tests for package relationships per SPEC-066-A (TDD — written before service)."""

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


async def _create_package(client: httpx.AsyncClient, headers: dict, name: str) -> str:
    """Create a package and return its id."""
    resp = await client.post(
        "/api/packages",
        json={"package_type": "uml", "name": name},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


class TestPackageRelationships:
    """Verify package relationship CRUD via API."""

    async def test_create_package_relationship(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        package_a = await _create_package(client, headers, "Package A")
        package_b = await _create_package(client, headers, "Package B")

        resp = await client.post(
            f"/api/packages/{package_a}/relationships",
            json={
                "target_package_id": package_b,
                "relationship_type": "dependency",
                "label": "depends on",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["source_package_id"] == package_a
        assert data["target_package_id"] == package_b
        assert data["relationship_type"] == "dependency"
        assert data["label"] == "depends on"

    async def test_list_package_relationships(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        package_a = await _create_package(client, headers, "List Package A")
        package_b = await _create_package(client, headers, "List Package B")

        await client.post(
            f"/api/packages/{package_a}/relationships",
            json={
                "target_package_id": package_b,
                "relationship_type": "dependency",
            },
            headers=headers,
        )

        resp = await client.get(
            f"/api/packages/{package_a}/relationships",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "package_relationships" in data
        assert "element_relationships" in data
        rels = data["package_relationships"]
        assert len(rels) >= 1
        assert rels[0]["source_package_id"] == package_a
        assert rels[0]["source_name"] == "List Package A"
        assert rels[0]["target_name"] == "List Package B"

    async def test_delete_package_relationship(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        package_a = await _create_package(client, headers, "Del Package A")
        package_b = await _create_package(client, headers, "Del Package B")

        create_resp = await client.post(
            f"/api/packages/{package_a}/relationships",
            json={
                "target_package_id": package_b,
                "relationship_type": "dependency",
            },
            headers=headers,
        )
        rel_id = create_resp.json()["id"]

        del_resp = await client.delete(
            f"/api/package-relationships/{rel_id}",
            headers=headers,
        )
        assert del_resp.status_code == 204

        # Verify gone
        list_resp = await client.get(
            f"/api/packages/{package_a}/relationships",
            headers=headers,
        )
        assert len(list_resp.json()["package_relationships"]) == 0

    async def test_duplicate_package_relationship(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        package_a = await _create_package(client, headers, "Dup Package A")
        package_b = await _create_package(client, headers, "Dup Package B")

        await client.post(
            f"/api/packages/{package_a}/relationships",
            json={
                "target_package_id": package_b,
                "relationship_type": "dependency",
            },
            headers=headers,
        )

        # Second create with same type should 409
        resp = await client.post(
            f"/api/packages/{package_a}/relationships",
            json={
                "target_package_id": package_b,
                "relationship_type": "dependency",
            },
            headers=headers,
        )
        assert resp.status_code == 409

    async def test_package_relationship_not_found_delete(
        self, client: httpx.AsyncClient
    ) -> None:
        headers = await _auth_headers(client)

        # Delete nonexistent relationship returns 404
        del_resp = await client.delete(
            "/api/package-relationships/nonexistent-id",
            headers=headers,
        )
        assert del_resp.status_code == 404

    async def test_auto_create_package_relationship_on_canvas_save(
        self, client: httpx.AsyncClient
    ) -> None:
        """PUT diagram with two packageref nodes + edge → package_relationships row created."""
        headers = await _auth_headers(client)
        package_a = await _create_package(client, headers, "Canvas Package A")
        package_b = await _create_package(client, headers, "Canvas Package B")
        # Create a diagram to hold the canvas
        diag_resp = await client.post(
            "/api/diagrams",
            json={"diagram_type": "uml", "name": "Canvas Diagram C"},
            headers=headers,
        )
        assert diag_resp.status_code == 201
        diagram_c = diag_resp.json()["id"]

        # Save diagram_c with canvas containing packageref nodes for A and B, plus an edge
        canvas_data = {
            "nodes": [
                {
                    "id": "node-a",
                    "type": "packageref",
                    "position": {"x": 0, "y": 0},
                    "data": {
                        "label": "Package A",
                        "elementType": "component",
                        "linkedPackageId": package_a,
                    },
                },
                {
                    "id": "node-b",
                    "type": "packageref",
                    "position": {"x": 200, "y": 0},
                    "data": {
                        "label": "Package B",
                        "elementType": "component",
                        "linkedPackageId": package_b,
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
            f"/api/diagrams/{diagram_c}",
            json={
                "name": "Canvas Diagram C",
                "description": "",
                "data": canvas_data,
                "change_summary": "Added packageref edges",
            },
            headers={**headers, "If-Match": "1"},
        )
        assert resp.status_code == 200

        # Verify package_relationships row was created
        # Query package_a's relationships (since the auto-created relationship is A → B)
        rel_resp = await client.get(
            f"/api/packages/{package_a}/relationships",
            headers=headers,
        )
        assert rel_resp.status_code == 200
        rels = rel_resp.json()["package_relationships"]
        matching = [
            r for r in rels
            if r["source_package_id"] == package_a and r["target_package_id"] == package_b
        ]
        assert len(matching) == 1
        assert matching[0]["relationship_type"] == "dependency"

    async def test_auto_create_package_relationship_no_duplicate(
        self, client: httpx.AsyncClient
    ) -> None:
        """Saving canvas twice with same packageref edge → only one package_relationships row."""
        headers = await _auth_headers(client)
        package_a = await _create_package(client, headers, "NoDup Package A")
        package_b = await _create_package(client, headers, "NoDup Package B")
        # Create a diagram to hold the canvas
        diag_resp = await client.post(
            "/api/diagrams",
            json={"diagram_type": "uml", "name": "NoDup Diagram C"},
            headers=headers,
        )
        assert diag_resp.status_code == 201
        diagram_c = diag_resp.json()["id"]

        canvas_data = {
            "nodes": [
                {
                    "id": "n1",
                    "type": "packageref",
                    "position": {"x": 0, "y": 0},
                    "data": {"label": "A", "elementType": "component", "linkedPackageId": package_a},
                },
                {
                    "id": "n2",
                    "type": "packageref",
                    "position": {"x": 200, "y": 0},
                    "data": {"label": "B", "elementType": "component", "linkedPackageId": package_b},
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
            f"/api/diagrams/{diagram_c}",
            json={"name": "NoDup Diagram C", "description": "", "data": canvas_data, "change_summary": "save 1"},
            headers={**headers, "If-Match": "1"},
        )
        assert resp1.status_code == 200

        # Second save (same edges)
        resp2 = await client.put(
            f"/api/diagrams/{diagram_c}",
            json={"name": "NoDup Diagram C", "description": "", "data": canvas_data, "change_summary": "save 2"},
            headers={**headers, "If-Match": "2"},
        )
        assert resp2.status_code == 200

        # Verify only one relationship exists (query package_a)
        rel_resp = await client.get(
            f"/api/packages/{package_a}/relationships",
            headers=headers,
        )
        rels = rel_resp.json()["package_relationships"]
        matching = [
            r for r in rels
            if r["source_package_id"] == package_a and r["target_package_id"] == package_b
            and r["relationship_type"] == "uses"
        ]
        assert len(matching) == 1
