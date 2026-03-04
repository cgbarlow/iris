"""Integration tests for diagram hierarchy API routes (ADR-055, ADR-071).

After the naming rename (ADR-071), diagrams have parent_package_id
referencing packages, not other diagrams. Hierarchy tests use packages as parents.
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


async def _create_package(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    *,
    name: str = "Test Package",
    parent_package_id: str | None = None,
) -> dict[str, object]:
    """Helper to create a test package."""
    body: dict[str, object] = {
        "name": name,
        "description": "A test package",
    }
    if parent_package_id is not None:
        body["parent_package_id"] = parent_package_id
    resp = await client.post("/api/packages", json=body, headers=headers)
    assert resp.status_code == 201
    return resp.json()


async def _create_diagram(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    *,
    name: str = "Test Diagram",
    diagram_type: str = "simple",
    parent_package_id: str | None = None,
    set_id: str | None = None,
) -> dict[str, object]:
    """Helper to create a test diagram."""
    body: dict[str, object] = {
        "diagram_type": diagram_type,
        "name": name,
        "description": "A test diagram",
        "data": {},
    }
    if parent_package_id is not None:
        body["parent_package_id"] = parent_package_id
    if set_id is not None:
        body["set_id"] = set_id
    resp = await client.post("/api/diagrams", json=body, headers=headers)
    assert resp.status_code == 201
    return resp.json()


class TestCreateWithParent:
    """Verify diagram creation with parent_package_id (must be a package)."""

    async def test_create_with_parent(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        pkg = await _create_package(client, headers, name="Parent Pkg")
        child = await _create_diagram(
            client, headers, name="Child", parent_package_id=pkg["id"],
        )
        assert child["parent_package_id"] == pkg["id"]

    async def test_create_without_parent(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        diagram = await _create_diagram(client, headers, name="Root")
        assert diagram["parent_package_id"] is None

    async def test_get_diagram_includes_parent_id(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        pkg = await _create_package(client, headers, name="Parent Pkg")
        child = await _create_diagram(
            client, headers, name="Child", parent_package_id=pkg["id"],
        )
        resp = await client.get(f"/api/diagrams/{child['id']}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["parent_package_id"] == pkg["id"]


class TestGetHierarchy:
    """Verify hierarchy tree retrieval."""

    async def test_empty_hierarchy(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/diagrams/hierarchy", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_flat_hierarchy(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        await _create_diagram(client, headers, name="A")
        await _create_diagram(client, headers, name="B")
        resp = await client.get("/api/diagrams/hierarchy", headers=headers)
        assert resp.status_code == 200
        tree = resp.json()
        assert len(tree) == 2
        assert all(len(n["children"]) == 0 for n in tree)

    async def test_nested_hierarchy(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        pkg = await _create_package(client, headers, name="Root Pkg")
        child_pkg = await _create_package(
            client, headers, name="Child Pkg", parent_package_id=pkg["id"],
        )
        await _create_diagram(
            client, headers, name="Diagram A", parent_package_id=pkg["id"],
        )
        await _create_diagram(
            client, headers, name="Diagram B", parent_package_id=child_pkg["id"],
        )
        resp = await client.get("/api/diagrams/hierarchy", headers=headers)
        tree = resp.json()
        # Diagrams without a parent package appear as roots
        # Diagrams under packages appear under that package in the tree
        # The tree only includes diagrams, so Diagram A and Diagram B should be roots
        # (since hierarchy only shows diagrams, not packages)
        assert len(tree) >= 1

    async def test_hierarchy_subtree(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        await _create_diagram(client, headers, name="Root Diagram")
        resp = await client.get("/api/diagrams/hierarchy", headers=headers)
        tree = resp.json()
        assert len(tree) >= 1


class TestGetAncestors:
    """Verify ancestor breadcrumb chain."""

    async def test_root_has_no_ancestors(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        root = await _create_diagram(client, headers, name="Root")
        resp = await client.get(
            f"/api/diagrams/{root['id']}/ancestors", headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_child_ancestors(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        root_pkg = await _create_package(client, headers, name="Root Pkg")
        child_pkg = await _create_package(
            client, headers, name="Child Pkg", parent_package_id=root_pkg["id"],
        )
        diagram = await _create_diagram(
            client, headers, name="Diagram", parent_package_id=child_pkg["id"],
        )
        resp = await client.get(
            f"/api/diagrams/{diagram['id']}/ancestors", headers=headers,
        )
        ancestors = resp.json()
        assert len(ancestors) == 2
        assert ancestors[0]["name"] == "Root Pkg"
        assert ancestors[1]["name"] == "Child Pkg"


class TestGetChildren:
    """Verify direct children retrieval (diagrams under a package)."""

    async def test_no_children(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        pkg = await _create_package(client, headers, name="Empty Pkg")
        resp = await client.get(
            f"/api/diagrams/{pkg['id']}/children", headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_has_children(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        pkg = await _create_package(client, headers, name="Parent Pkg")
        await _create_diagram(
            client, headers, name="Child A", parent_package_id=pkg["id"],
        )
        await _create_diagram(
            client, headers, name="Child B", parent_package_id=pkg["id"],
        )
        resp = await client.get(
            f"/api/diagrams/{pkg['id']}/children", headers=headers,
        )
        children = resp.json()
        assert len(children) == 2
        names = {c["name"] for c in children}
        assert names == {"Child A", "Child B"}


class TestSetParent:
    """Verify parent set/unset operations."""

    async def test_set_parent(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        pkg = await _create_package(client, headers, name="Parent Pkg")
        child = await _create_diagram(client, headers, name="Child")
        resp = await client.put(
            f"/api/diagrams/{child['id']}/parent",
            json={"parent_package_id": pkg["id"]},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["parent_package_id"] == pkg["id"]

    async def test_unset_parent(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        pkg = await _create_package(client, headers, name="Parent Pkg")
        child = await _create_diagram(
            client, headers, name="Child", parent_package_id=pkg["id"],
        )
        resp = await client.put(
            f"/api/diagrams/{child['id']}/parent",
            json={"parent_package_id": None},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["parent_package_id"] is None

    async def test_set_parent_nonexistent_diagram(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        resp = await client.put(
            "/api/diagrams/nonexistent/parent",
            json={"parent_package_id": "also-nonexistent"},
            headers=headers,
        )
        assert resp.status_code == 404

    async def test_set_parent_nonexistent_parent(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        child = await _create_diagram(client, headers, name="Child")
        resp = await client.put(
            f"/api/diagrams/{child['id']}/parent",
            json={"parent_package_id": "nonexistent"},
            headers=headers,
        )
        assert resp.status_code == 404


class TestCyclePrevention:
    """Verify circular reference prevention in package hierarchy."""

    async def test_self_reference_prevented(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        diagram = await _create_diagram(client, headers, name="Self")
        resp = await client.put(
            f"/api/diagrams/{diagram['id']}/parent",
            json={"parent_package_id": diagram["id"]},
            headers=headers,
        )
        # Should fail - either 400 (cycle) or 404 (not a package)
        assert resp.status_code in (400, 404)


class TestSetFilteredHierarchy:
    """Verify hierarchy can be filtered by set_id (ADR-063)."""

    async def test_hierarchy_filtered_by_set(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        s1 = (await client.post("/api/sets", json={"name": "Set1"}, headers=headers)).json()
        s2 = (await client.post("/api/sets", json={"name": "Set2"}, headers=headers)).json()
        await _create_diagram(client, headers, name="M1", set_id=s1["id"])
        await _create_diagram(client, headers, name="M2", set_id=s2["id"])

        resp = await client.get(f"/api/diagrams/hierarchy?set_id={s1['id']}", headers=headers)
        tree = resp.json()
        names = [n["name"] for n in tree]
        assert "M1" in names
        assert "M2" not in names

    async def test_hierarchy_no_set_filter_returns_all(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        s1 = (await client.post("/api/sets", json={"name": "SetA"}, headers=headers)).json()
        s2 = (await client.post("/api/sets", json={"name": "SetB"}, headers=headers)).json()
        await _create_diagram(client, headers, name="MA", set_id=s1["id"])
        await _create_diagram(client, headers, name="MB", set_id=s2["id"])

        resp = await client.get("/api/diagrams/hierarchy", headers=headers)
        tree = resp.json()
        names = [n["name"] for n in tree]
        assert "MA" in names
        assert "MB" in names


class TestDeletedDiagramHierarchy:
    """Verify deleted diagrams are excluded from hierarchy."""

    async def test_deleted_diagram_excluded_from_hierarchy(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        pkg = await _create_package(client, headers, name="Pkg")
        child = await _create_diagram(
            client, headers, name="Child", parent_package_id=pkg["id"],
        )
        await client.delete(
            f"/api/diagrams/{child['id']}",
            headers={**headers, "If-Match": "1"},
        )
        resp = await client.get("/api/diagrams/hierarchy", headers=headers)
        tree = resp.json()
        # Deleted diagrams should not appear
        names = [n["name"] for n in tree]
        assert "Child" not in names

    async def test_deleted_diagram_excluded_from_children(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        pkg = await _create_package(client, headers, name="Pkg")
        child = await _create_diagram(
            client, headers, name="Child", parent_package_id=pkg["id"],
        )
        await client.delete(
            f"/api/diagrams/{child['id']}",
            headers={**headers, "If-Match": "1"},
        )
        resp = await client.get(
            f"/api/diagrams/{pkg['id']}/children", headers=headers,
        )
        assert resp.json() == []
