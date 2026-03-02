"""Integration tests for model hierarchy API routes (ADR-055)."""

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


async def _create_model(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    *,
    name: str = "Test Model",
    model_type: str = "simple",
    parent_model_id: str | None = None,
) -> dict[str, object]:
    """Helper to create a test model."""
    body: dict[str, object] = {
        "model_type": model_type,
        "name": name,
        "description": "A test model",
        "data": {},
    }
    if parent_model_id is not None:
        body["parent_model_id"] = parent_model_id
    resp = await client.post("/api/models", json=body, headers=headers)
    assert resp.status_code == 201
    return resp.json()


class TestCreateWithParent:
    """Verify model creation with parent_model_id."""

    async def test_create_with_parent(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        parent = await _create_model(client, headers, name="Parent")
        child = await _create_model(
            client, headers, name="Child", parent_model_id=parent["id"],
        )
        assert child["parent_model_id"] == parent["id"]

    async def test_create_without_parent(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        model = await _create_model(client, headers, name="Root")
        assert model["parent_model_id"] is None

    async def test_get_model_includes_parent_id(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        parent = await _create_model(client, headers, name="Parent")
        child = await _create_model(
            client, headers, name="Child", parent_model_id=parent["id"],
        )
        resp = await client.get(f"/api/models/{child['id']}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["parent_model_id"] == parent["id"]


class TestGetHierarchy:
    """Verify hierarchy tree retrieval."""

    async def test_empty_hierarchy(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/models/hierarchy", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_flat_hierarchy(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        await _create_model(client, headers, name="A")
        await _create_model(client, headers, name="B")
        resp = await client.get("/api/models/hierarchy", headers=headers)
        assert resp.status_code == 200
        tree = resp.json()
        assert len(tree) == 2
        assert all(len(n["children"]) == 0 for n in tree)

    async def test_nested_hierarchy(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        root = await _create_model(client, headers, name="Root")
        child = await _create_model(
            client, headers, name="Child", parent_model_id=root["id"],
        )
        await _create_model(
            client, headers, name="Grandchild", parent_model_id=child["id"],
        )
        resp = await client.get("/api/models/hierarchy", headers=headers)
        tree = resp.json()
        assert len(tree) == 1
        assert tree[0]["name"] == "Root"
        assert len(tree[0]["children"]) == 1
        assert tree[0]["children"][0]["name"] == "Child"
        assert len(tree[0]["children"][0]["children"]) == 1
        assert tree[0]["children"][0]["children"][0]["name"] == "Grandchild"

    async def test_hierarchy_subtree(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        root = await _create_model(client, headers, name="Root")
        child = await _create_model(
            client, headers, name="Child", parent_model_id=root["id"],
        )
        await _create_model(
            client, headers, name="Grandchild", parent_model_id=child["id"],
        )
        resp = await client.get(
            f"/api/models/hierarchy?root_id={child['id']}", headers=headers,
        )
        tree = resp.json()
        assert len(tree) == 1
        assert tree[0]["name"] == "Child"
        assert len(tree[0]["children"]) == 1


class TestGetAncestors:
    """Verify ancestor breadcrumb chain."""

    async def test_root_has_no_ancestors(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        root = await _create_model(client, headers, name="Root")
        resp = await client.get(
            f"/api/models/{root['id']}/ancestors", headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_child_ancestors(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        root = await _create_model(client, headers, name="Root")
        child = await _create_model(
            client, headers, name="Child", parent_model_id=root["id"],
        )
        grandchild = await _create_model(
            client, headers, name="Grandchild", parent_model_id=child["id"],
        )
        resp = await client.get(
            f"/api/models/{grandchild['id']}/ancestors", headers=headers,
        )
        ancestors = resp.json()
        assert len(ancestors) == 2
        assert ancestors[0]["name"] == "Root"
        assert ancestors[1]["name"] == "Child"


class TestGetChildren:
    """Verify direct children retrieval."""

    async def test_no_children(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        root = await _create_model(client, headers, name="Root")
        resp = await client.get(
            f"/api/models/{root['id']}/children", headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_has_children(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        root = await _create_model(client, headers, name="Root")
        await _create_model(
            client, headers, name="Child A", parent_model_id=root["id"],
        )
        await _create_model(
            client, headers, name="Child B", parent_model_id=root["id"],
        )
        resp = await client.get(
            f"/api/models/{root['id']}/children", headers=headers,
        )
        children = resp.json()
        assert len(children) == 2
        names = {c["name"] for c in children}
        assert names == {"Child A", "Child B"}


class TestSetParent:
    """Verify parent set/unset operations."""

    async def test_set_parent(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        parent = await _create_model(client, headers, name="Parent")
        child = await _create_model(client, headers, name="Child")
        resp = await client.put(
            f"/api/models/{child['id']}/parent",
            json={"parent_model_id": parent["id"]},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["parent_model_id"] == parent["id"]

        # Verify via get
        get_resp = await client.get(
            f"/api/models/{child['id']}", headers=headers,
        )
        assert get_resp.json()["parent_model_id"] == parent["id"]

    async def test_unset_parent(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        parent = await _create_model(client, headers, name="Parent")
        child = await _create_model(
            client, headers, name="Child", parent_model_id=parent["id"],
        )
        resp = await client.put(
            f"/api/models/{child['id']}/parent",
            json={"parent_model_id": None},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["parent_model_id"] is None

    async def test_set_parent_nonexistent_model(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        resp = await client.put(
            "/api/models/nonexistent/parent",
            json={"parent_model_id": "also-nonexistent"},
            headers=headers,
        )
        assert resp.status_code == 404

    async def test_set_parent_nonexistent_parent(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        child = await _create_model(client, headers, name="Child")
        resp = await client.put(
            f"/api/models/{child['id']}/parent",
            json={"parent_model_id": "nonexistent"},
            headers=headers,
        )
        assert resp.status_code == 404


class TestCyclePrevention:
    """Verify circular reference prevention."""

    async def test_self_reference_prevented(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        model = await _create_model(client, headers, name="Self")
        resp = await client.put(
            f"/api/models/{model['id']}/parent",
            json={"parent_model_id": model["id"]},
            headers=headers,
        )
        assert resp.status_code == 400
        assert "cycle" in resp.json()["detail"].lower()

    async def test_two_node_cycle_prevented(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        a = await _create_model(client, headers, name="A")
        b = await _create_model(
            client, headers, name="B", parent_model_id=a["id"],
        )
        # Try to make A a child of B — would create A→B→A cycle
        resp = await client.put(
            f"/api/models/{a['id']}/parent",
            json={"parent_model_id": b["id"]},
            headers=headers,
        )
        assert resp.status_code == 400

    async def test_three_node_cycle_prevented(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        a = await _create_model(client, headers, name="A")
        b = await _create_model(
            client, headers, name="B", parent_model_id=a["id"],
        )
        c = await _create_model(
            client, headers, name="C", parent_model_id=b["id"],
        )
        # Try to make A a child of C — would create A→B→C→A cycle
        resp = await client.put(
            f"/api/models/{a['id']}/parent",
            json={"parent_model_id": c["id"]},
            headers=headers,
        )
        assert resp.status_code == 400


class TestDeletedModelHierarchy:
    """Verify deleted models are excluded from hierarchy."""

    async def test_deleted_model_excluded_from_hierarchy(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        root = await _create_model(client, headers, name="Root")
        child = await _create_model(
            client, headers, name="Child", parent_model_id=root["id"],
        )
        # Delete child
        await client.delete(
            f"/api/models/{child['id']}",
            headers={**headers, "If-Match": "1"},
        )
        resp = await client.get("/api/models/hierarchy", headers=headers)
        tree = resp.json()
        assert len(tree) == 1
        assert tree[0]["name"] == "Root"
        assert len(tree[0]["children"]) == 0

    async def test_deleted_model_excluded_from_children(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        root = await _create_model(client, headers, name="Root")
        child = await _create_model(
            client, headers, name="Child", parent_model_id=root["id"],
        )
        await client.delete(
            f"/api/models/{child['id']}",
            headers={**headers, "If-Match": "1"},
        )
        resp = await client.get(
            f"/api/models/{root['id']}/children", headers=headers,
        )
        assert resp.json() == []
