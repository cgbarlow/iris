"""Integration tests for recycle bin routes."""

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


async def _create_and_delete_package(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    name: str = "Test Package",
) -> dict:
    resp = await client.post("/api/packages", json={"name": name}, headers=headers)
    assert resp.status_code == 201
    pkg = resp.json()
    await client.delete(
        f"/api/packages/{pkg['id']}",
        headers={**headers, "If-Match": str(pkg["current_version"])},
    )
    return pkg


async def _create_and_delete_diagram(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    name: str = "Test Diagram",
) -> dict:
    resp = await client.post(
        "/api/diagrams",
        json={"diagram_type": "component", "name": name, "data": {}},
        headers=headers,
    )
    assert resp.status_code == 201
    d = resp.json()
    await client.delete(
        f"/api/diagrams/{d['id']}",
        headers={**headers, "If-Match": str(d["current_version"])},
    )
    return d


async def _create_and_delete_element(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    name: str = "Test Element",
) -> dict:
    resp = await client.post(
        "/api/elements",
        json={"element_type": "component", "name": name, "data": {}},
        headers=headers,
    )
    assert resp.status_code == 201
    e = resp.json()
    await client.delete(
        f"/api/elements/{e['id']}",
        headers={**headers, "If-Match": str(e["current_version"])},
    )
    return e


class TestListDeletedItems:
    async def test_list_deleted_items(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        await _create_and_delete_package(client, headers, "Deleted Pkg")
        await _create_and_delete_diagram(client, headers, "Deleted Diag")
        await _create_and_delete_element(client, headers, "Deleted Elem")

        resp = await client.get("/api/recycle-bin", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 3
        item_types = {item["item_type"] for item in data["items"]}
        assert "package" in item_types
        assert "diagram" in item_types
        assert "element" in item_types

    async def test_list_excludes_active_items(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        # Create an active package (not deleted)
        resp = await client.post(
            "/api/packages", json={"name": "Active Pkg"}, headers=headers,
        )
        active_id = resp.json()["id"]

        resp = await client.get("/api/recycle-bin", headers=headers)
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()["items"]]
        assert active_id not in ids


class TestRestoreItems:
    async def test_restore_package(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        pkg = await _create_and_delete_package(client, headers, "Restore Me")

        resp = await client.post(
            f"/api/recycle-bin/packages/{pkg['id']}/restore", headers=headers,
        )
        assert resp.status_code == 200

        # Package should be accessible again
        resp = await client.get(f"/api/packages/{pkg['id']}", headers=headers)
        assert resp.status_code == 200

        # Check version history has 'restore' entry
        resp = await client.get(
            f"/api/packages/{pkg['id']}/versions", headers=headers,
        )
        change_types = [v["change_type"] for v in resp.json()]
        assert "restore" in change_types

    async def test_restore_diagram(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        d = await _create_and_delete_diagram(client, headers, "Restore Diag")

        resp = await client.post(
            f"/api/recycle-bin/diagrams/{d['id']}/restore", headers=headers,
        )
        assert resp.status_code == 200

        resp = await client.get(f"/api/diagrams/{d['id']}", headers=headers)
        assert resp.status_code == 200

    async def test_restore_element(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        e = await _create_and_delete_element(client, headers, "Restore Elem")

        resp = await client.post(
            f"/api/recycle-bin/elements/{e['id']}/restore", headers=headers,
        )
        assert resp.status_code == 200

        resp = await client.get(f"/api/elements/{e['id']}", headers=headers)
        assert resp.status_code == 200

    async def test_cascade_restore_by_group(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        # Create hierarchy and cascade-delete
        root_resp = await client.post(
            "/api/packages", json={"name": "Root"}, headers=headers,
        )
        root = root_resp.json()
        child_resp = await client.post(
            "/api/packages",
            json={"name": "Child", "parent_package_id": root["id"]},
            headers=headers,
        )
        child = child_resp.json()

        await client.delete(
            f"/api/packages/{root['id']}",
            headers={**headers, "If-Match": str(root["current_version"])},
        )

        # Get the group_id from recycle bin
        resp = await client.get("/api/recycle-bin", headers=headers)
        items = resp.json()["items"]
        group_ids = {i["deleted_group_id"] for i in items if i["deleted_group_id"]}
        assert len(group_ids) >= 1
        group_id = group_ids.pop()

        # Restore the entire group
        resp = await client.post(
            f"/api/recycle-bin/groups/{group_id}/restore", headers=headers,
        )
        assert resp.status_code == 200

        # Both packages should be accessible
        resp = await client.get(f"/api/packages/{root['id']}", headers=headers)
        assert resp.status_code == 200
        resp = await client.get(f"/api/packages/{child['id']}", headers=headers)
        assert resp.status_code == 200

    async def test_restore_clears_group_id(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        pkg = await _create_and_delete_package(client, headers, "Clear Group")

        await client.post(
            f"/api/recycle-bin/packages/{pkg['id']}/restore", headers=headers,
        )

        # Should not appear in recycle bin
        resp = await client.get("/api/recycle-bin", headers=headers)
        ids = [item["id"] for item in resp.json()["items"]]
        assert pkg["id"] not in ids


class TestHardDelete:
    async def test_hard_delete(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        pkg = await _create_and_delete_package(client, headers, "Hard Delete")

        resp = await client.delete(
            f"/api/recycle-bin/packages/{pkg['id']}", headers=headers,
        )
        assert resp.status_code == 204

        # Should not appear in recycle bin
        resp = await client.get("/api/recycle-bin", headers=headers)
        ids = [item["id"] for item in resp.json()["items"]]
        assert pkg["id"] not in ids

        # Versions should also be gone
        resp = await client.get(
            f"/api/packages/{pkg['id']}/versions", headers=headers,
        )
        assert resp.status_code == 404

    async def test_hard_delete_only_soft_deleted(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        # Create active package
        resp = await client.post(
            "/api/packages", json={"name": "Active"}, headers=headers,
        )
        active_id = resp.json()["id"]

        resp = await client.delete(
            f"/api/recycle-bin/packages/{active_id}", headers=headers,
        )
        assert resp.status_code == 404


class TestEmptyRecycleBin:
    async def test_empty_deletes_all(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        await _create_and_delete_package(client, headers, "P1")
        await _create_and_delete_diagram(client, headers, "D1")
        await _create_and_delete_element(client, headers, "E1")

        # Verify items exist in recycle bin
        resp = await client.get("/api/recycle-bin", headers=headers)
        assert resp.json()["total"] >= 3

        # Empty recycle bin
        resp = await client.delete("/api/recycle-bin", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "emptied"
        assert data["count"] >= 3

        # Recycle bin should be empty
        resp = await client.get("/api/recycle-bin", headers=headers)
        assert resp.json()["total"] == 0

    async def test_empty_does_not_touch_active_items(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        # Create an active package and a deleted package
        resp = await client.post(
            "/api/packages", json={"name": "Active"}, headers=headers,
        )
        active_id = resp.json()["id"]
        await _create_and_delete_package(client, headers, "Deleted")

        await client.delete("/api/recycle-bin", headers=headers)

        # Active package should still be accessible
        resp = await client.get(f"/api/packages/{active_id}", headers=headers)
        assert resp.status_code == 200

    async def test_empty_returns_zero_when_already_empty(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        resp = await client.delete("/api/recycle-bin", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["count"] == 0


class TestPagination:
    async def test_paginated_results(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        # Create 3 deleted packages
        for i in range(3):
            await _create_and_delete_package(client, headers, f"Pkg {i}")

        # Page 1 with page_size=2
        resp = await client.get(
            "/api/recycle-bin?page=1&page_size=2", headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] >= 3
        assert data["page"] == 1
        assert data["page_size"] == 2

        # Page 2
        resp = await client.get(
            "/api/recycle-bin?page=2&page_size=2", headers=headers,
        )
        data = resp.json()
        assert len(data["items"]) >= 1
