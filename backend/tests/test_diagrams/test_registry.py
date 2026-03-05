"""Integration tests for the diagram type/notation registry (ADR-079)."""

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


class TestListDiagramTypes:
    @pytest.mark.anyio
    async def test_list_diagram_types(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/registry/diagram-types", headers=headers)
        assert resp.status_code == 200
        types = resp.json()
        assert len(types) == 13  # 7 original + 6 new (ADR-082)
        type_ids = [t["id"] for t in types]
        assert "component" in type_ids
        assert "sequence" in type_ids
        assert "class" in type_ids
        assert "deployment" in type_ids
        assert "free_form" in type_ids

    @pytest.mark.anyio
    async def test_diagram_types_have_notations(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/registry/diagram-types", headers=headers)
        types = resp.json()
        component = next(t for t in types if t["id"] == "component")
        assert len(component["notations"]) == 4
        notation_ids = [n["notation_id"] for n in component["notations"]]
        assert "simple" in notation_ids
        assert "uml" in notation_ids
        assert "archimate" in notation_ids
        assert "c4" in notation_ids

    @pytest.mark.anyio
    async def test_default_notation_marked(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/registry/diagram-types", headers=headers)
        types = resp.json()
        component = next(t for t in types if t["id"] == "component")
        defaults = [n for n in component["notations"] if n["is_default"]]
        assert len(defaults) == 1
        assert defaults[0]["notation_id"] == "simple"


class TestListNotations:
    @pytest.mark.anyio
    async def test_list_notations(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/registry/notations", headers=headers)
        assert resp.status_code == 200
        notations = resp.json()
        assert len(notations) == 4
        ids = [n["id"] for n in notations]
        assert "simple" in ids
        assert "uml" in ids
        assert "archimate" in ids
        assert "c4" in ids


class TestCreateDiagramWithNotation:
    @pytest.mark.anyio
    async def test_create_with_explicit_notation(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/diagrams",
            json={
                "diagram_type": "component",
                "name": "Test UML Component",
                "notation": "uml",
                "data": {},
            },
            headers=headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["notation"] == "uml"
        assert body["diagram_type"] == "component"

    @pytest.mark.anyio
    async def test_create_with_default_notation(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/diagrams",
            json={
                "diagram_type": "component",
                "name": "Test Default",
                "data": {},
            },
            headers=headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["notation"] == "simple"  # default for component

    @pytest.mark.anyio
    async def test_get_diagram_returns_notation(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        create_resp = await client.post(
            "/api/diagrams",
            json={
                "diagram_type": "deployment",
                "name": "Test Deploy",
                "notation": "c4",
                "data": {},
            },
            headers=headers,
        )
        diagram_id = create_resp.json()["id"]
        get_resp = await client.get(f"/api/diagrams/{diagram_id}", headers=headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["notation"] == "c4"

    @pytest.mark.anyio
    async def test_list_diagrams_returns_notation(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        await client.post(
            "/api/diagrams",
            json={
                "diagram_type": "component",
                "name": "Notation List Test",
                "notation": "archimate",
                "data": {},
            },
            headers=headers,
        )
        resp = await client.get("/api/diagrams", headers=headers)
        items = resp.json()["items"]
        test_items = [i for i in items if i["name"] == "Notation List Test"]
        assert len(test_items) == 1
        assert test_items[0]["notation"] == "archimate"


class TestChangeNotation:
    @pytest.mark.anyio
    async def test_change_notation(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        create_resp = await client.post(
            "/api/diagrams",
            json={
                "diagram_type": "component",
                "name": "Change Notation Test",
                "notation": "simple",
                "data": {},
            },
            headers=headers,
        )
        diagram_id = create_resp.json()["id"]

        change_resp = await client.put(
            f"/api/registry/diagrams/{diagram_id}/notation",
            json={"notation": "uml"},
            headers=headers,
        )
        assert change_resp.status_code == 200
        assert change_resp.json()["notation"] == "uml"

        # Verify via GET
        get_resp = await client.get(f"/api/diagrams/{diagram_id}", headers=headers)
        assert get_resp.json()["notation"] == "uml"

    @pytest.mark.anyio
    async def test_change_to_invalid_notation_rejected(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        create_resp = await client.post(
            "/api/diagrams",
            json={
                "diagram_type": "class",
                "name": "Invalid Notation Test",
                "data": {},
            },
            headers=headers,
        )
        diagram_id = create_resp.json()["id"]

        # Class type only supports UML — try to set it to C4
        change_resp = await client.put(
            f"/api/registry/diagrams/{diagram_id}/notation",
            json={"notation": "c4"},
            headers=headers,
        )
        assert change_resp.status_code == 400

    @pytest.mark.anyio
    async def test_change_notation_nonexistent_diagram(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.put(
            "/api/registry/diagrams/nonexistent-id/notation",
            json={"notation": "uml"},
            headers=headers,
        )
        assert resp.status_code == 404


class TestDetectedNotations:
    @pytest.mark.anyio
    async def test_detected_notations_on_create(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/diagrams",
            json={
                "diagram_type": "component",
                "name": "Detection Test",
                "notation": "simple",
                "data": {
                    "nodes": [
                        {"id": "1", "position": {"x": 0, "y": 0},
                         "data": {"label": "A", "entityType": "component"}},
                        {"id": "2", "position": {"x": 100, "y": 0},
                         "data": {"label": "B", "entityType": "class"}},
                    ],
                    "edges": [],
                },
            },
            headers=headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert sorted(body["detected_notations"]) == ["simple", "uml"]

    @pytest.mark.anyio
    async def test_detected_notations_empty_canvas(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/diagrams",
            json={
                "diagram_type": "component",
                "name": "Empty Detection",
                "data": {},
            },
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["detected_notations"] == []

    @pytest.mark.anyio
    async def test_detected_notations_updated_on_save(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        create_resp = await client.post(
            "/api/diagrams",
            json={
                "diagram_type": "free_form",
                "name": "Update Detection",
                "data": {},
            },
            headers=headers,
        )
        diagram_id = create_resp.json()["id"]
        version = create_resp.json()["current_version"]

        # Update with nodes
        await client.put(
            f"/api/diagrams/{diagram_id}",
            json={
                "name": "Update Detection",
                "data": {
                    "nodes": [
                        {"id": "1", "position": {"x": 0, "y": 0},
                         "data": {"label": "Sys", "entityType": "software_system"}},
                    ],
                    "edges": [],
                },
            },
            headers={**headers, "If-Match": str(version)},
        )

        get_resp = await client.get(f"/api/diagrams/{diagram_id}", headers=headers)
        assert get_resp.json()["detected_notations"] == ["c4"]


class TestHierarchyIncludesNotation:
    @pytest.mark.anyio
    async def test_hierarchy_nodes_have_notation(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        await client.post(
            "/api/diagrams",
            json={
                "diagram_type": "component",
                "name": "Hierarchy Notation Test",
                "notation": "archimate",
                "data": {},
            },
            headers=headers,
        )
        resp = await client.get("/api/diagrams/hierarchy", headers=headers)
        assert resp.status_code == 200
        tree = resp.json()
        # Find our test diagram in the flat list
        def find_node(nodes: list, name: str) -> dict | None:
            for n in nodes:
                if n["name"] == name:
                    return n
                found = find_node(n.get("children", []), name)
                if found:
                    return found
            return None

        node = find_node(tree, "Hierarchy Notation Test")
        assert node is not None
        assert node["notation"] == "archimate"
