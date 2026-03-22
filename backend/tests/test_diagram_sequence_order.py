"""Tests for diagram sequence ordering in the navigation hierarchy
(Issue #7, ADR-098, SPEC-098-A).

TDD: written before implementation.
"""

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


async def _create_package(
    client: httpx.AsyncClient, headers: dict, name: str, parent_id: str | None = None
) -> str:
    """Create a package and return its id."""
    body: dict = {"package_type": "uml", "name": name}
    if parent_id:
        body["parent_package_id"] = parent_id
    resp = await client.post("/api/packages", json=body, headers=headers)
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_diagram(
    client: httpx.AsyncClient,
    headers: dict,
    name: str,
    parent_package_id: str | None = None,
) -> str:
    """Create a diagram and return its id."""
    body: dict = {"diagram_type": "component", "name": name}
    if parent_package_id:
        body["parent_package_id"] = parent_package_id
    resp = await client.post("/api/diagrams", json=body, headers=headers)
    assert resp.status_code == 201
    return resp.json()["id"]


def _flatten_hierarchy(nodes: list[dict]) -> list[dict]:
    """Flatten a hierarchy tree into a list preserving pre-order traversal."""
    result = []
    for node in nodes:
        result.append(node)
        result.extend(_flatten_hierarchy(node.get("children", [])))
    return result


def _get_children_names(hierarchy: list[dict], parent_id: str | None) -> list[str]:
    """Get ordered names of children under a specific parent in the hierarchy."""
    if parent_id is None:
        return [n["name"] for n in hierarchy]

    all_nodes = _flatten_hierarchy(hierarchy)
    for node in all_nodes:
        if node["id"] == parent_id:
            return [c["name"] for c in node.get("children", [])]
    return []


class TestDiagramSequenceOrder:
    """Verify diagram/package sequence ordering in the navigation hierarchy."""

    async def test_default_order_is_creation_order(
        self, client: httpx.AsyncClient
    ) -> None:
        """Newly created diagrams within a package should appear in creation order."""
        headers = await _auth_headers(client)
        pkg = await _create_package(client, headers, "Order Package")

        # Create diagrams in specific order (names are NOT alphabetical)
        d_charlie = await _create_diagram(client, headers, "Charlie", pkg)
        d_alpha = await _create_diagram(client, headers, "Alpha", pkg)
        d_bravo = await _create_diagram(client, headers, "Bravo", pkg)

        resp = await client.get(
            "/api/diagrams/hierarchy", headers=headers
        )
        assert resp.status_code == 200
        hierarchy = resp.json()

        children = _get_children_names(hierarchy, pkg)
        # Should be in creation order (sequence_order), not alphabetical
        assert children == ["Charlie", "Alpha", "Bravo"]

    async def test_reorder_diagrams_via_api(
        self, client: httpx.AsyncClient
    ) -> None:
        """PUT /api/diagrams/reorder should change the sequence order."""
        headers = await _auth_headers(client)
        pkg = await _create_package(client, headers, "Reorder Package")

        d1 = await _create_diagram(client, headers, "First", pkg)
        d2 = await _create_diagram(client, headers, "Second", pkg)
        d3 = await _create_diagram(client, headers, "Third", pkg)

        # Reorder: Third, First, Second
        resp = await client.put(
            "/api/diagrams/reorder",
            json={
                "parent_package_id": pkg,
                "ordered_ids": [d3, d1, d2],
            },
            headers=headers,
        )
        assert resp.status_code == 200

        hierarchy_resp = await client.get(
            "/api/diagrams/hierarchy", headers=headers
        )
        children = _get_children_names(hierarchy_resp.json(), pkg)
        assert children == ["Third", "First", "Second"]

    async def test_reorder_packages_via_api(
        self, client: httpx.AsyncClient
    ) -> None:
        """Reorder should work for packages too (within the same parent)."""
        headers = await _auth_headers(client)
        parent = await _create_package(client, headers, "Parent Package")

        p1 = await _create_package(client, headers, "Pkg Alpha", parent)
        p2 = await _create_package(client, headers, "Pkg Bravo", parent)
        p3 = await _create_package(client, headers, "Pkg Charlie", parent)

        # Reorder packages: Charlie, Alpha, Bravo
        resp = await client.put(
            "/api/diagrams/reorder",
            json={
                "parent_package_id": parent,
                "ordered_ids": [p3, p1, p2],
            },
            headers=headers,
        )
        assert resp.status_code == 200

        hierarchy_resp = await client.get(
            "/api/diagrams/hierarchy", headers=headers
        )
        children = _get_children_names(hierarchy_resp.json(), parent)
        # Packages come before diagrams (sorted by node_type), then by sequence_order
        assert children == ["Pkg Charlie", "Pkg Alpha", "Pkg Bravo"]

    async def test_reorder_root_level(
        self, client: httpx.AsyncClient
    ) -> None:
        """Reorder should work at root level (parent_package_id = null)."""
        headers = await _auth_headers(client)

        p1 = await _create_package(client, headers, "Root Z")
        p2 = await _create_package(client, headers, "Root A")
        p3 = await _create_package(client, headers, "Root M")

        resp = await client.put(
            "/api/diagrams/reorder",
            json={
                "parent_package_id": None,
                "ordered_ids": [p2, p3, p1],
            },
            headers=headers,
        )
        assert resp.status_code == 200

        hierarchy_resp = await client.get(
            "/api/diagrams/hierarchy", headers=headers
        )
        root_names = [n["name"] for n in hierarchy_resp.json()]
        # Only check our packages (seed data may add others)
        our_names = [n for n in root_names if n.startswith("Root ")]
        assert our_names == ["Root A", "Root M", "Root Z"]

    async def test_hierarchy_includes_sequence_order(
        self, client: httpx.AsyncClient
    ) -> None:
        """The hierarchy response should include the sequence_order field."""
        headers = await _auth_headers(client)
        pkg = await _create_package(client, headers, "SeqOrder Package")
        await _create_diagram(client, headers, "SeqOrder Diagram", pkg)

        resp = await client.get("/api/diagrams/hierarchy", headers=headers)
        assert resp.status_code == 200
        hierarchy = resp.json()

        all_nodes = _flatten_hierarchy(hierarchy)
        for node in all_nodes:
            assert "sequence_order" in node, f"Node {node['name']} missing sequence_order"
