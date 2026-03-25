"""Integration tests for Scenia entity CRUD API routes."""

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
    await client.post(
        "/api/auth/setup",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _install_scenia(client: httpx.AsyncClient, headers: dict[str, str]) -> None:
    """Install the scenia extension so routes are accessible."""
    await client.post(
        "/api/extensions/scenia/install",
        json={"name": "Scenia", "version": "1.0.0"},
        headers=headers,
    )


async def _create_set(client: httpx.AsyncClient, headers: dict[str, str], name: str = "Test Set") -> str:
    """Create a set and return its ID."""
    resp = await client.post("/api/sets", json={"name": name}, headers=headers)
    return resp.json()["id"]


class TestSceniaGating:
    async def test_returns_404_when_not_installed(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/scenia/strategies", headers=headers)
        assert resp.status_code == 404
        assert "not available" in resp.json()["detail"]

    async def test_accessible_when_installed(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        await _install_scenia(client, headers)
        resp = await client.get("/api/scenia/strategies", headers=headers)
        assert resp.status_code == 200


class TestStrategyCrud:
    async def test_create_strategy(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        await _install_scenia(client, headers)
        set_id = await _create_set(client, headers)

        resp = await client.post(
            "/api/scenia/strategies",
            json={"name": "Digital Transformation", "description": "Our vision", "data": {"vision": "Be digital-first"}, "set_id": set_id},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Digital Transformation"
        assert data["element_type"] == "scenia_strategy"
        assert data["data"]["vision"] == "Be digital-first"

    async def test_list_strategies_by_set(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        await _install_scenia(client, headers)
        set1 = await _create_set(client, headers, "Set 1")
        set2 = await _create_set(client, headers, "Set 2")

        await client.post("/api/scenia/strategies", json={"name": "S1", "set_id": set1, "data": {}}, headers=headers)
        await client.post("/api/scenia/strategies", json={"name": "S2", "set_id": set2, "data": {}}, headers=headers)

        resp = await client.get(f"/api/scenia/strategies?set_id={set1}", headers=headers)
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["name"] == "S1"

    async def test_update_strategy(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        await _install_scenia(client, headers)
        set_id = await _create_set(client, headers)

        create_resp = await client.post(
            "/api/scenia/strategies",
            json={"name": "Old Name", "data": {}, "set_id": set_id},
            headers=headers,
        )
        entity_id = create_resp.json()["id"]

        resp = await client.put(
            f"/api/scenia/strategies/{entity_id}",
            json={"name": "New Name", "data": {"updated": True}},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"

    async def test_delete_strategy(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        await _install_scenia(client, headers)
        set_id = await _create_set(client, headers)

        create_resp = await client.post(
            "/api/scenia/strategies",
            json={"name": "Temp", "data": {}, "set_id": set_id},
            headers=headers,
        )
        entity_id = create_resp.json()["id"]

        resp = await client.delete(f"/api/scenia/strategies/{entity_id}", headers=headers)
        assert resp.status_code == 204

        get_resp = await client.get(f"/api/scenia/strategies/{entity_id}", headers=headers)
        assert get_resp.status_code == 404


class TestInitiativeCrud:
    async def test_create_initiative_with_data(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        await _install_scenia(client, headers)
        set_id = await _create_set(client, headers)

        resp = await client.post(
            "/api/scenia/initiatives",
            json={
                "name": "Cloud Migration",
                "data": {
                    "startDate": "2026-04-01",
                    "endDate": "2026-12-31",
                    "budget": 500000,
                    "progress": 0,
                    "status": "planned",
                },
                "set_id": set_id,
            },
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["budget"] == 500000


class TestAssetCategories:
    async def test_create_and_list_categories(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        await _install_scenia(client, headers)
        set_id = await _create_set(client, headers)

        await client.post(
            "/api/scenia/asset-categories",
            json={"name": "Infrastructure", "color": "#3B82F6", "display_order": 0, "set_id": set_id},
            headers=headers,
        )
        await client.post(
            "/api/scenia/asset-categories",
            json={"name": "Applications", "color": "#10B981", "display_order": 1, "set_id": set_id},
            headers=headers,
        )

        resp = await client.get(f"/api/scenia/asset-categories?set_id={set_id}", headers=headers)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 2
        assert items[0]["name"] == "Infrastructure"

    async def test_delete_category(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        await _install_scenia(client, headers)
        set_id = await _create_set(client, headers)

        create_resp = await client.post(
            "/api/scenia/asset-categories",
            json={"name": "Temp Cat", "set_id": set_id},
            headers=headers,
        )
        cat_id = create_resp.json()["id"]

        resp = await client.delete(f"/api/scenia/asset-categories/{cat_id}", headers=headers)
        assert resp.status_code == 204


class TestAppStatuses:
    async def test_create_and_list_statuses(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        await _install_scenia(client, headers)
        set_id = await _create_set(client, headers)

        await client.post(
            "/api/scenia/app-statuses",
            json={"name": "Active", "color": "#22C55E", "display_order": 0, "set_id": set_id},
            headers=headers,
        )

        resp = await client.get(f"/api/scenia/app-statuses?set_id={set_id}", headers=headers)
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["name"] == "Active"


class TestTimelineSettings:
    async def test_upsert_and_get_timeline_settings(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        await _install_scenia(client, headers)
        set_id = await _create_set(client, headers)

        resp = await client.put(
            f"/api/scenia/timeline-settings?set_id={set_id}",
            json={"start_date": "2026-01-01", "end_date": "2026-12-31", "view_mode": "monthly", "zoom_level": 1.5},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["view_mode"] == "monthly"
        assert data["zoom_level"] == 1.5

        # Update
        resp2 = await client.put(
            f"/api/scenia/timeline-settings?set_id={set_id}",
            json={"start_date": "2026-01-01", "end_date": "2027-06-30", "view_mode": "quarterly"},
            headers=headers,
        )
        assert resp2.json()["view_mode"] == "quarterly"


class TestVersions:
    async def test_create_and_list_versions(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        await _install_scenia(client, headers)
        set_id = await _create_set(client, headers)

        await client.post(
            "/api/scenia/versions",
            json={"name": "v1.0", "data": {"snapshot": True}, "set_id": set_id},
            headers=headers,
        )
        await client.post(
            "/api/scenia/versions",
            json={"name": "v2.0", "data": {}, "set_id": set_id},
            headers=headers,
        )

        resp = await client.get(f"/api/scenia/versions?set_id={set_id}", headers=headers)
        items = resp.json()["items"]
        assert len(items) == 2
        # Ordered descending by version number
        assert items[0]["version_number"] == 2
        assert items[1]["version_number"] == 1


class TestDependencies:
    async def test_create_and_list_dependencies(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        await _install_scenia(client, headers)
        set_id = await _create_set(client, headers)

        # Create two initiatives
        i1 = (await client.post(
            "/api/scenia/initiatives",
            json={"name": "Initiative A", "data": {}, "set_id": set_id},
            headers=headers,
        )).json()
        i2 = (await client.post(
            "/api/scenia/initiatives",
            json={"name": "Initiative B", "data": {}, "set_id": set_id},
            headers=headers,
        )).json()

        # Create dependency
        resp = await client.post(
            "/api/scenia/dependencies",
            json={"source_id": i1["id"], "target_id": i2["id"], "dependency_type": "blocks", "set_id": set_id},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["dependency_type"] == "blocks"

        # List
        list_resp = await client.get(f"/api/scenia/dependencies?set_id={set_id}", headers=headers)
        assert len(list_resp.json()["items"]) == 1

    async def test_delete_dependency(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        await _install_scenia(client, headers)
        set_id = await _create_set(client, headers)

        i1 = (await client.post(
            "/api/scenia/initiatives",
            json={"name": "A", "data": {}, "set_id": set_id},
            headers=headers,
        )).json()
        i2 = (await client.post(
            "/api/scenia/initiatives",
            json={"name": "B", "data": {}, "set_id": set_id},
            headers=headers,
        )).json()

        dep = (await client.post(
            "/api/scenia/dependencies",
            json={"source_id": i1["id"], "target_id": i2["id"], "dependency_type": "requires", "set_id": set_id},
            headers=headers,
        )).json()

        resp = await client.delete(f"/api/scenia/dependencies/{dep['id']}", headers=headers)
        assert resp.status_code == 204
