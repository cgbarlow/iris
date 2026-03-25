"""Integration tests for Scenia bulk data read/write."""

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
    await client.post(
        "/api/extensions/scenia/install",
        json={"name": "Scenia", "version": "1.0.0"},
        headers=headers,
    )


async def _create_set(client: httpx.AsyncClient, headers: dict[str, str], name: str = "Roadmap Set") -> str:
    resp = await client.post("/api/sets", json={"name": name}, headers=headers)
    return resp.json()["id"]


class TestBulkDataRead:
    async def test_empty_bulk_data(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        await _install_scenia(client, headers)
        set_id = await _create_set(client, headers)

        resp = await client.get(f"/api/scenia/data?set_id={set_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["strategies"] == []
        assert data["programmes"] == []
        assert data["initiatives"] == []
        assert data["assets"] == []
        assert data["applications"] == []
        assert data["app_segments"] == []
        assert data["milestones"] == []
        assert data["resources"] == []
        assert data["dependencies"] == []
        assert data["asset_categories"] == []
        assert data["app_statuses"] == []
        assert data["timeline_settings"] is None
        assert data["versions"] == []

    async def test_bulk_data_includes_created_entities(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        await _install_scenia(client, headers)
        set_id = await _create_set(client, headers)

        # Create some entities
        await client.post("/api/scenia/strategies", json={"name": "S1", "data": {}, "set_id": set_id}, headers=headers)
        await client.post("/api/scenia/initiatives", json={"name": "I1", "data": {}, "set_id": set_id}, headers=headers)
        await client.post(
            "/api/scenia/asset-categories",
            json={"name": "Cat1", "set_id": set_id},
            headers=headers,
        )

        resp = await client.get(f"/api/scenia/data?set_id={set_id}", headers=headers)
        data = resp.json()
        assert len(data["strategies"]) == 1
        assert len(data["initiatives"]) == 1
        assert len(data["asset_categories"]) == 1


class TestBulkDataWrite:
    async def test_save_bulk_data(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        await _install_scenia(client, headers)
        set_id = await _create_set(client, headers)

        payload = {
            "strategies": [
                {"name": "Digital First", "data": {"vision": "Transform"}, "set_id": set_id},
            ],
            "programmes": [
                {"name": "Cloud Programme", "data": {"budget": 1000000}, "set_id": set_id},
            ],
            "initiatives": [
                {"name": "Migrate DB", "data": {"progress": 25}, "set_id": set_id},
                {"name": "Modernize UI", "data": {"progress": 0}, "set_id": set_id},
            ],
            "assets": [
                {"name": "CRM System", "data": {"owner": "Sales"}, "set_id": set_id},
            ],
            "asset_categories": [
                {"name": "Core Systems", "color": "#3B82F6", "set_id": set_id},
            ],
            "app_statuses": [
                {"name": "Active", "color": "#22C55E", "set_id": set_id},
            ],
            "timeline_settings": {
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
                "view_mode": "quarterly",
            },
        }

        resp = await client.put(
            f"/api/scenia/data?set_id={set_id}",
            json=payload,
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["strategies"]) == 1
        assert len(data["programmes"]) == 1
        assert len(data["initiatives"]) == 2
        assert len(data["assets"]) == 1
        assert len(data["asset_categories"]) == 1
        assert len(data["app_statuses"]) == 1
        assert data["timeline_settings"]["view_mode"] == "quarterly"

    async def test_save_replaces_existing_data(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        await _install_scenia(client, headers)
        set_id = await _create_set(client, headers)

        # First save
        await client.put(
            f"/api/scenia/data?set_id={set_id}",
            json={
                "strategies": [
                    {"name": "Old Strategy", "data": {}, "set_id": set_id},
                    {"name": "Other Strategy", "data": {}, "set_id": set_id},
                ],
            },
            headers=headers,
        )

        # Second save replaces
        resp = await client.put(
            f"/api/scenia/data?set_id={set_id}",
            json={
                "strategies": [
                    {"name": "New Strategy", "data": {}, "set_id": set_id},
                ],
            },
            headers=headers,
        )
        data = resp.json()
        assert len(data["strategies"]) == 1
        assert data["strategies"][0]["name"] == "New Strategy"


class TestCrossLink:
    async def test_cross_link_for_scenia_element(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        await _install_scenia(client, headers)
        set_id = await _create_set(client, headers)

        create_resp = await client.post(
            "/api/scenia/strategies",
            json={"name": "Linked Strategy", "data": {}, "set_id": set_id},
            headers=headers,
        )
        element_id = create_resp.json()["id"]

        resp = await client.get(f"/api/scenia/link/{element_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["element_type"] == "scenia_strategy"

    async def test_cross_link_404_for_non_scenia_element(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        await _install_scenia(client, headers)

        # Create a regular element
        create_resp = await client.post(
            "/api/elements",
            json={"element_type": "component", "name": "Regular", "data": {}},
            headers=headers,
        )
        element_id = create_resp.json()["id"]

        resp = await client.get(f"/api/scenia/link/{element_id}", headers=headers)
        assert resp.status_code == 404
