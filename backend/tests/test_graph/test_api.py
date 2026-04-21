"""Integration tests for knowledge graph API (ADR-116)."""

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
    await client.post(
        "/api/auth/setup",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _create_element(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    name: str,
    element_type: str = "application",
    set_id: str = DEFAULT_SET_ID,
) -> str:
    resp = await client.post(
        "/api/elements",
        json={"element_type": element_type, "name": name, "data": {}, "set_id": set_id},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_relationship(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    source_id: str,
    target_id: str,
    relationship_type: str = "uses",
    label: str | None = "test link",
) -> str:
    resp = await client.post(
        "/api/relationships",
        json={
            "source_element_id": source_id,
            "target_element_id": target_id,
            "relationship_type": relationship_type,
            "label": label,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


class TestGraphAuth:
    async def test_allows_anonymous(self, client: httpx.AsyncClient) -> None:
        """Graph endpoint is public-readable (ADR-123). Anonymous returns 200."""
        resp = await client.get(f"/api/graph?set_id={DEFAULT_SET_ID}")
        assert resp.status_code == 200

    async def test_rejects_invalid_token(self, client: httpx.AsyncClient) -> None:
        """A *present-but-invalid* token still returns 401 (SPEC-123-A)."""
        resp = await client.get(
            f"/api/graph?set_id={DEFAULT_SET_ID}",
            headers={"Authorization": "Bearer not-a-real-token"},
        )
        assert resp.status_code == 401

    async def test_unscoped_returns_all(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/graph", headers=headers)
        assert resp.status_code == 200


class TestGraphNodes:
    async def test_empty_set_has_set_node_only(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get(f"/api/graph?set_id={DEFAULT_SET_ID}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        # Set itself appears as a node, but no elements/diagrams/packages
        assert len(data["nodes"]) == 1
        assert data["nodes"][0]["node_type"] == "set"

    async def test_element_nodes(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        eid = await _create_element(client, headers, "App A")
        resp = await client.get(f"/api/graph?set_id={DEFAULT_SET_ID}", headers=headers)
        nodes = [n for n in resp.json()["nodes"] if n["node_type"] == "element"]
        assert len(nodes) == 1
        assert nodes[0]["id"] == eid
        assert nodes[0]["name"] == "App A"
        assert nodes[0]["type_detail"] == "application"

    async def test_diagram_nodes(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        dr = await client.post(
            "/api/diagrams",
            json={"diagram_type": "simple", "name": "My Diagram", "data": {}, "set_id": DEFAULT_SET_ID},
            headers=headers,
        )
        assert dr.status_code == 201
        did = dr.json()["id"]
        resp = await client.get(f"/api/graph?set_id={DEFAULT_SET_ID}", headers=headers)
        diagram_nodes = [n for n in resp.json()["nodes"] if n["node_type"] == "diagram"]
        assert len(diagram_nodes) == 1
        assert diagram_nodes[0]["id"] == did
        assert diagram_nodes[0]["type_detail"] == "simple"

    async def test_package_nodes(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        pr = await client.post(
            "/api/packages",
            json={"name": "My Package", "set_id": DEFAULT_SET_ID},
            headers=headers,
        )
        assert pr.status_code == 201
        pid = pr.json()["id"]
        resp = await client.get(f"/api/graph?set_id={DEFAULT_SET_ID}", headers=headers)
        pkg_nodes = [n for n in resp.json()["nodes"] if n["node_type"] == "package"]
        assert len(pkg_nodes) == 1
        assert pkg_nodes[0]["id"] == pid

    async def test_excludes_deleted(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        eid = await _create_element(client, headers, "ToDelete")
        el = await client.get(f"/api/elements/{eid}", headers=headers)
        await client.delete(f"/api/elements/{eid}", headers={**headers, "If-Match": str(el.json()["current_version"])})
        resp = await client.get(f"/api/graph?set_id={DEFAULT_SET_ID}", headers=headers)
        element_nodes = [n for n in resp.json()["nodes"] if n["node_type"] == "element"]
        assert element_nodes == []

    async def test_scoped_to_set(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        set_resp = await client.post("/api/sets", json={"name": "Other"}, headers=headers)
        other_set_id = set_resp.json()["id"]
        await _create_element(client, headers, "In Default", set_id=DEFAULT_SET_ID)
        await _create_element(client, headers, "In Other", set_id=other_set_id)
        resp = await client.get(f"/api/graph?set_id={DEFAULT_SET_ID}", headers=headers)
        names = [n["name"] for n in resp.json()["nodes"] if n["node_type"] == "element"]
        assert "In Default" in names
        assert "In Other" not in names

    async def test_collection_scope(self, client: httpx.AsyncClient) -> None:
        """Collection-scoped graph shows collection, sets, and diagrams (no elements/packages)."""
        headers = await _auth_headers(client)
        col = await client.post("/api/collections", json={"name": "Col"}, headers=headers)
        col_id = col.json()["id"]
        s = await client.post("/api/sets", json={"name": "CS", "collection_id": col_id}, headers=headers)
        sid = s.json()["id"]
        await _create_element(client, headers, "Col El", set_id=sid)
        resp = await client.get(f"/api/graph?collection_id={col_id}", headers=headers)
        nodes = resp.json()["nodes"]
        # Collection and set appear
        assert any(n["name"] == "Col" and n["node_type"] == "collection" for n in nodes)
        assert any(n["name"] == "CS" and n["node_type"] == "set" for n in nodes)
        # Elements are excluded from collection-scoped view
        assert not any(n["node_type"] == "element" for n in nodes)


class TestGraphEdges:
    async def test_element_relationships(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        src = await _create_element(client, headers, "Src")
        tgt = await _create_element(client, headers, "Tgt", "service")
        rid = await _create_relationship(client, headers, src, tgt)
        resp = await client.get(f"/api/graph?set_id={DEFAULT_SET_ID}", headers=headers)
        el_edges = [e for e in resp.json()["edges"] if e["edge_type"] == "element_relationship"]
        assert len(el_edges) == 1
        assert el_edges[0]["source"] == src
        assert el_edges[0]["target"] == tgt

    async def test_hierarchy_edges(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        pkg = await client.post("/api/packages", json={"name": "Pkg", "set_id": DEFAULT_SET_ID}, headers=headers)
        pkg_id = pkg.json()["id"]
        diag = await client.post(
            "/api/diagrams",
            json={"diagram_type": "simple", "name": "D", "data": {}, "set_id": DEFAULT_SET_ID, "parent_package_id": pkg_id},
            headers=headers,
        )
        assert diag.status_code == 201
        resp = await client.get(f"/api/graph?set_id={DEFAULT_SET_ID}", headers=headers)
        hier_edges = [e for e in resp.json()["edges"] if e["edge_type"] == "hierarchy"]
        assert len(hier_edges) == 1
        assert hier_edges[0]["source"] == pkg_id
        assert hier_edges[0]["target"] == diag.json()["id"]

    async def test_diagram_element_edges(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        eid = await _create_element(client, headers, "Canvas El")
        # Create diagram with canvas data referencing the element
        canvas_data = {"nodes": [{"id": "n1", "type": "default", "position": {"x": 0, "y": 0}, "data": {"entityId": eid, "label": "Canvas El"}}], "edges": []}
        diag = await client.post(
            "/api/diagrams",
            json={"diagram_type": "simple", "name": "D", "data": canvas_data, "set_id": DEFAULT_SET_ID},
            headers=headers,
        )
        assert diag.status_code == 201
        resp = await client.get(f"/api/graph?set_id={DEFAULT_SET_ID}", headers=headers)
        de_edges = [e for e in resp.json()["edges"] if e["edge_type"] == "diagram_element"]
        assert len(de_edges) == 1
        assert de_edges[0]["source"] == diag.json()["id"]
        assert de_edges[0]["target"] == eid
