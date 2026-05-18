"""Tests for the element ↔ package edge type in the knowledge graph.

Issue #173 item 5, ADR-199 — elements can belong to packages
(`element.package_id` per m064_element_package_membership), but the
graph service did not previously emit edges for that relationship,
and the KG visibility settings had no toggle for it.

This module covers the backend invariants:

- `GET /api/graph?set_id=...` includes `element_package` edges for
  every element whose `package_id` is in the scoped package set.
- Edge direction is package → element (consistent with set_membership
  and hierarchy: containers point at their contents).
- Default settings include `element_package: True` so the edges are
  visible out of the box.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest

from app.config import AppConfig, AuthConfig, DatabaseConfig
from app.database import DatabaseManager
from app.graph.models import GraphDisplaySettings
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
        transport=transport, base_url="http://test",
    ) as c:
        yield c
    await db_manager.close()


async def _auth(client: httpx.AsyncClient) -> dict[str, str]:
    await client.post(
        "/api/auth/setup",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


class TestDefaults:
    def test_element_package_default_visible(self) -> None:
        defaults = GraphDisplaySettings()
        assert "element_package" in defaults.edges, (
            "element_package must appear in the defaults dict so the "
            "settings UI can render its toggle"
        )
        assert defaults.edges["element_package"] is True, (
            "default visibility for element_package should be ON"
        )


class TestGraphEmitsElementPackageEdges:
    async def test_edge_emitted_for_element_with_package_id(
        self, client: httpx.AsyncClient,
    ) -> None:
        h = await _auth(client)

        set_resp = await client.post(
            "/api/sets", json={"name": "GraphSet"}, headers=h,
        )
        assert set_resp.status_code == 201
        set_id = set_resp.json()["id"]

        pkg_resp = await client.post(
            "/api/packages",
            json={"name": "Pantry", "set_id": set_id},
            headers=h,
        )
        assert pkg_resp.status_code == 201
        pkg_id = pkg_resp.json()["id"]

        el_resp = await client.post(
            "/api/elements",
            json={
                "element_type": "component",
                "name": "Tinned Tomatoes",
                "data": {},
                "set_id": set_id,
                "package_id": pkg_id,
            },
            headers=h,
        )
        assert el_resp.status_code == 201, el_resp.text
        el_id = el_resp.json()["id"]

        graph_resp = await client.get(f"/api/graph?set_id={set_id}", headers=h)
        assert graph_resp.status_code == 200
        body = graph_resp.json()

        ep_edges = [e for e in body["edges"] if e["edge_type"] == "element_package"]
        assert len(ep_edges) == 1, (
            f"expected 1 element_package edge, got {len(ep_edges)} "
            f"(all edges: {[e['edge_type'] for e in body['edges']]})"
        )
        edge = ep_edges[0]
        assert edge["source"] == pkg_id, "edge direction should be package → element"
        assert edge["target"] == el_id

    async def test_no_edge_when_element_has_no_package(
        self, client: httpx.AsyncClient,
    ) -> None:
        h = await _auth(client)
        set_resp = await client.post(
            "/api/sets", json={"name": "GraphSet"}, headers=h,
        )
        set_id = set_resp.json()["id"]

        await client.post(
            "/api/elements",
            json={
                "element_type": "component",
                "name": "FreeFloating",
                "data": {},
                "set_id": set_id,
            },
            headers=h,
        )

        graph_resp = await client.get(f"/api/graph?set_id={set_id}", headers=h)
        body = graph_resp.json()
        ep_edges = [e for e in body["edges"] if e["edge_type"] == "element_package"]
        assert ep_edges == []

    async def test_no_redundant_set_membership_when_element_packaged(
        self, client: httpx.AsyncClient,
    ) -> None:
        """ADR-203 / issue #181: the set → package → element chain
        replaces the direct set → element edge for packaged elements.
        Only the un-packaged element's set_membership edge remains."""
        h = await _auth(client)
        set_resp = await client.post(
            "/api/sets", json={"name": "GraphSet"}, headers=h,
        )
        set_id = set_resp.json()["id"]

        pkg_resp = await client.post(
            "/api/packages",
            json={"name": "Pantry", "set_id": set_id},
            headers=h,
        )
        pkg_id = pkg_resp.json()["id"]

        packaged = (await client.post(
            "/api/elements",
            json={
                "element_type": "component",
                "name": "Tinned Tomatoes",
                "data": {},
                "set_id": set_id,
                "package_id": pkg_id,
            },
            headers=h,
        )).json()
        free_floating = (await client.post(
            "/api/elements",
            json={
                "element_type": "component",
                "name": "FreeFloating",
                "data": {},
                "set_id": set_id,
            },
            headers=h,
        )).json()

        graph_resp = await client.get(f"/api/graph?set_id={set_id}", headers=h)
        body = graph_resp.json()

        set_member_targets = {
            e["target"] for e in body["edges"]
            if e["edge_type"] == "set_membership" and e["source"] == set_id
        }
        # Free-floating element keeps its direct set→element edge.
        assert free_floating["id"] in set_member_targets
        # Packaged element does NOT — reachable via set → package → element.
        assert packaged["id"] not in set_member_targets, (
            "ADR-203: packaged elements must not duplicate their "
            "containment as a direct set → element edge"
        )
        # set → package edge still present (separate rule).
        assert pkg_id in set_member_targets

        # The element_package chain works.
        ep_edges = [e for e in body["edges"] if e["edge_type"] == "element_package"]
        assert any(
            e["source"] == pkg_id and e["target"] == packaged["id"]
            for e in ep_edges
        )

    async def test_node_type_remains_element_not_package(
        self, client: httpx.AsyncClient,
    ) -> None:
        """Sanity: adding the edge doesn't change node typing."""
        h = await _auth(client)
        set_resp = await client.post(
            "/api/sets", json={"name": "GraphSet"}, headers=h,
        )
        set_id = set_resp.json()["id"]

        pkg_resp = await client.post(
            "/api/packages",
            json={"name": "Pantry", "set_id": set_id},
            headers=h,
        )
        pkg_id = pkg_resp.json()["id"]

        el_resp = await client.post(
            "/api/elements",
            json={
                "element_type": "component",
                "name": "Tinned Tomatoes",
                "data": {},
                "set_id": set_id,
                "package_id": pkg_id,
            },
            headers=h,
        )
        el_id = el_resp.json()["id"]

        graph_resp = await client.get(f"/api/graph?set_id={set_id}", headers=h)
        body = graph_resp.json()

        el_node = next(n for n in body["nodes"] if n["id"] == el_id)
        pkg_node = next(n for n in body["nodes"] if n["id"] == pkg_id)
        assert el_node["node_type"] == "element"
        assert pkg_node["node_type"] == "package"
