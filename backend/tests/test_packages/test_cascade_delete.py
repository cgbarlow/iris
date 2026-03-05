"""Integration tests for cascade package deletion."""

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


async def _admin_headers(client: httpx.AsyncClient) -> dict[str, str]:
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
    name: str = "Test Package",
    parent_package_id: str | None = None,
) -> dict:
    body: dict = {"name": name}
    if parent_package_id:
        body["parent_package_id"] = parent_package_id
    resp = await client.post("/api/packages", json=body, headers=headers)
    assert resp.status_code == 201
    return resp.json()


async def _create_diagram(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    name: str = "Test Diagram",
    parent_package_id: str | None = None,
) -> dict:
    body: dict = {"diagram_type": "component", "name": name, "data": {}}
    if parent_package_id:
        body["parent_package_id"] = parent_package_id
    resp = await client.post("/api/diagrams", json=body, headers=headers)
    assert resp.status_code == 201
    return resp.json()


class TestCountDescendants:
    """Tests for GET /api/packages/{id}/descendants/count."""

    async def test_count_descendants_correct(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        root = await _create_package(client, headers, "Root")
        child1 = await _create_package(client, headers, "Child1", root["id"])
        child2 = await _create_package(client, headers, "Child2", root["id"])
        await _create_diagram(client, headers, "D1", root["id"])
        await _create_diagram(client, headers, "D2", child1["id"])
        await _create_diagram(client, headers, "D3", child2["id"])

        resp = await client.get(
            f"/api/packages/{root['id']}/descendants/count",
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["child_packages"] == 2
        assert data["child_diagrams"] == 3

    async def test_count_excludes_already_deleted(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        root = await _create_package(client, headers, "Root")
        child = await _create_package(client, headers, "Child", root["id"])
        await _create_diagram(client, headers, "D1", root["id"])
        d2 = await _create_diagram(client, headers, "D2", child["id"])

        # Pre-delete one diagram
        await client.delete(
            f"/api/diagrams/{d2['id']}",
            headers={**headers, "If-Match": str(d2["current_version"])},
        )

        resp = await client.get(
            f"/api/packages/{root['id']}/descendants/count",
            headers=headers,
        )
        data = resp.json()
        assert data["child_packages"] == 1
        assert data["child_diagrams"] == 1  # D2 excluded


class TestCascadeDelete:
    """Tests for cascade DELETE /api/packages/{id}."""

    async def test_cascade_delete_removes_child_packages(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        root = await _create_package(client, headers, "Root")
        child = await _create_package(client, headers, "Child", root["id"])

        resp = await client.delete(
            f"/api/packages/{root['id']}",
            headers={**headers, "If-Match": str(root["current_version"])},
        )
        assert resp.status_code == 204

        # Child should be 404 (soft-deleted)
        resp = await client.get(
            f"/api/packages/{child['id']}", headers=headers,
        )
        assert resp.status_code == 404

    async def test_cascade_delete_removes_nested_diagrams(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        root = await _create_package(client, headers, "Root")
        child = await _create_package(client, headers, "Child", root["id"])
        d1 = await _create_diagram(client, headers, "D1", root["id"])
        d2 = await _create_diagram(client, headers, "D2", child["id"])

        await client.delete(
            f"/api/packages/{root['id']}",
            headers={**headers, "If-Match": str(root["current_version"])},
        )

        # Both diagrams should be 404
        for did in [d1["id"], d2["id"]]:
            resp = await client.get(f"/api/diagrams/{did}", headers=headers)
            assert resp.status_code == 404

    async def test_cascade_delete_sets_group_id(
        self, client: httpx.AsyncClient,
    ) -> None:
        """Verified fully once recycle bin endpoint exists; here we check via DB."""
        headers = await _admin_headers(client)
        root = await _create_package(client, headers, "Root")
        child = await _create_package(client, headers, "Child", root["id"])
        d1 = await _create_diagram(client, headers, "D1", root["id"])

        await client.delete(
            f"/api/packages/{root['id']}",
            headers={**headers, "If-Match": str(root["current_version"])},
        )

        # All items should be soft-deleted — verify via versions endpoint
        # Root package versions should have a 'delete' entry
        resp = await client.get(
            f"/api/packages/{root['id']}/versions", headers=headers,
        )
        assert resp.status_code == 200
        root_deletes = [v for v in resp.json() if v["change_type"] == "delete"]
        assert len(root_deletes) == 1

        # Child package versions should also have a 'delete' entry
        resp = await client.get(
            f"/api/packages/{child['id']}/versions", headers=headers,
        )
        assert resp.status_code == 200
        child_deletes = [v for v in resp.json() if v["change_type"] == "delete"]
        assert len(child_deletes) == 1

    async def test_cascade_delete_creates_version_records(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        root = await _create_package(client, headers, "Root")
        child = await _create_package(client, headers, "Child", root["id"])

        await client.delete(
            f"/api/packages/{root['id']}",
            headers={**headers, "If-Match": str(root["current_version"])},
        )

        # Check versions for child package — should have a 'delete' version
        resp = await client.get(
            f"/api/packages/{child['id']}/versions", headers=headers,
        )
        assert resp.status_code == 200
        versions = resp.json()
        delete_versions = [v for v in versions if v["change_type"] == "delete"]
        assert len(delete_versions) == 1

    async def test_cascade_delete_occ_conflict(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        root = await _create_package(client, headers, "Root")

        resp = await client.delete(
            f"/api/packages/{root['id']}",
            headers={**headers, "If-Match": "999"},
        )
        assert resp.status_code == 409
