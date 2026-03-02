"""Integration tests for sets CRUD API routes."""

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
    await client.post(
        "/api/auth/setup",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


class TestListSets:
    async def test_list_returns_default_set(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/sets", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) >= 1
        names = [s["name"] for s in data["items"]]
        assert "Default" in names

    async def test_default_set_has_well_known_id(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/sets", headers=headers)
        default = next(s for s in resp.json()["items"] if s["name"] == "Default")
        assert default["id"] == DEFAULT_SET_ID


class TestCreateSet:
    async def test_create_returns_201(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/sets",
            json={"name": "Sprint 1", "description": "First sprint"},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Sprint 1"
        assert data["description"] == "First sprint"
        assert data["model_count"] == 0
        assert data["entity_count"] == 0

    async def test_duplicate_name_returns_409(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        await client.post(
            "/api/sets",
            json={"name": "Unique Set"},
            headers=headers,
        )
        resp = await client.post(
            "/api/sets",
            json={"name": "Unique Set"},
            headers=headers,
        )
        assert resp.status_code == 409


class TestGetSet:
    async def test_get_existing_set(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get(f"/api/sets/{DEFAULT_SET_ID}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Default"

    async def test_get_nonexistent_returns_404(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/sets/nonexistent-id", headers=headers)
        assert resp.status_code == 404


class TestUpdateSet:
    async def test_update_name(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        create_resp = await client.post(
            "/api/sets",
            json={"name": "Old Name"},
            headers=headers,
        )
        set_id = create_resp.json()["id"]
        resp = await client.put(
            f"/api/sets/{set_id}",
            json={"name": "New Name", "description": "Updated"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"
        assert resp.json()["description"] == "Updated"


class TestDeleteSet:
    async def test_delete_empty_set(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        create_resp = await client.post(
            "/api/sets",
            json={"name": "Temp Set"},
            headers=headers,
        )
        set_id = create_resp.json()["id"]
        resp = await client.delete(f"/api/sets/{set_id}", headers=headers)
        assert resp.status_code == 204

    async def test_cannot_delete_default_set(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.delete(f"/api/sets/{DEFAULT_SET_ID}", headers=headers)
        assert resp.status_code == 403

    async def test_cannot_delete_nonempty_set(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        # Create a set
        create_resp = await client.post(
            "/api/sets",
            json={"name": "Has Models"},
            headers=headers,
        )
        set_id = create_resp.json()["id"]
        # Create a model in this set
        await client.post(
            "/api/models",
            json={"model_type": "simple-view", "name": "M1", "data": {}, "set_id": set_id},
            headers=headers,
        )
        # Try to delete
        resp = await client.delete(f"/api/sets/{set_id}", headers=headers)
        assert resp.status_code == 409


class TestSetTags:
    async def test_get_scoped_tags(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        # Create two sets
        s1 = (await client.post("/api/sets", json={"name": "Set A"}, headers=headers)).json()
        s2 = (await client.post("/api/sets", json={"name": "Set B"}, headers=headers)).json()

        # Create a model in each set and tag them
        m1 = (await client.post(
            "/api/models",
            json={"model_type": "simple-view", "name": "M1", "data": {}, "set_id": s1["id"]},
            headers=headers,
        )).json()
        m2 = (await client.post(
            "/api/models",
            json={"model_type": "simple-view", "name": "M2", "data": {}, "set_id": s2["id"]},
            headers=headers,
        )).json()

        await client.post(
            f"/api/models/{m1['id']}/tags",
            json={"tag": "v1.0"},
            headers=headers,
        )
        await client.post(
            f"/api/models/{m2['id']}/tags",
            json={"tag": "v2.0"},
            headers=headers,
        )

        # Tags for Set A should only contain v1.0
        resp = await client.get(f"/api/sets/{s1['id']}/tags", headers=headers)
        assert resp.status_code == 200
        assert "v1.0" in resp.json()
        assert "v2.0" not in resp.json()


class TestModelSetIntegration:
    async def test_model_created_with_set_id(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        create_resp = await client.post(
            "/api/sets",
            json={"name": "Custom Set"},
            headers=headers,
        )
        set_id = create_resp.json()["id"]
        model_resp = await client.post(
            "/api/models",
            json={"model_type": "simple-view", "name": "M1", "data": {}, "set_id": set_id},
            headers=headers,
        )
        assert model_resp.status_code == 201
        assert model_resp.json()["set_id"] == set_id

    async def test_model_defaults_to_default_set(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        model_resp = await client.post(
            "/api/models",
            json={"model_type": "simple-view", "name": "M2", "data": {}},
            headers=headers,
        )
        assert model_resp.json()["set_id"] == DEFAULT_SET_ID

    async def test_list_models_filtered_by_set(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        s = (await client.post("/api/sets", json={"name": "Filter Set"}, headers=headers)).json()
        await client.post(
            "/api/models",
            json={"model_type": "simple-view", "name": "InSet", "data": {}, "set_id": s["id"]},
            headers=headers,
        )
        await client.post(
            "/api/models",
            json={"model_type": "simple-view", "name": "NotInSet", "data": {}},
            headers=headers,
        )
        resp = await client.get(f"/api/models?set_id={s['id']}", headers=headers)
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["name"] == "InSet"

    async def test_set_counts_reflect_models(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        s = (await client.post("/api/sets", json={"name": "Count Set"}, headers=headers)).json()
        await client.post(
            "/api/models",
            json={"model_type": "simple-view", "name": "MC1", "data": {}, "set_id": s["id"]},
            headers=headers,
        )
        resp = await client.get(f"/api/sets/{s['id']}", headers=headers)
        assert resp.json()["model_count"] == 1


class TestEntitySetIntegration:
    async def test_entity_created_with_set_id(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        s = (await client.post("/api/sets", json={"name": "E Set"}, headers=headers)).json()
        resp = await client.post(
            "/api/entities",
            json={"entity_type": "component", "name": "E1", "data": {}, "set_id": s["id"]},
            headers=headers,
        )
        assert resp.status_code == 201
        assert resp.json()["set_id"] == s["id"]

    async def test_list_entities_filtered_by_set(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        s = (await client.post("/api/sets", json={"name": "EFilter"}, headers=headers)).json()
        await client.post(
            "/api/entities",
            json={"entity_type": "component", "name": "InSet", "data": {}, "set_id": s["id"]},
            headers=headers,
        )
        await client.post(
            "/api/entities",
            json={"entity_type": "component", "name": "NotInSet", "data": {}},
            headers=headers,
        )
        resp = await client.get(f"/api/entities?set_id={s['id']}", headers=headers)
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["name"] == "InSet"

    async def test_scoped_tag_listing(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        s1 = (await client.post("/api/sets", json={"name": "TagScope1"}, headers=headers)).json()
        s2 = (await client.post("/api/sets", json={"name": "TagScope2"}, headers=headers)).json()

        e1 = (await client.post(
            "/api/entities",
            json={"entity_type": "component", "name": "E1", "data": {}, "set_id": s1["id"]},
            headers=headers,
        )).json()
        e2 = (await client.post(
            "/api/entities",
            json={"entity_type": "component", "name": "E2", "data": {}, "set_id": s2["id"]},
            headers=headers,
        )).json()

        await client.post(f"/api/entities/{e1['id']}/tags", json={"tag": "alpha"}, headers=headers)
        await client.post(f"/api/entities/{e2['id']}/tags", json={"tag": "beta"}, headers=headers)

        resp = await client.get(f"/api/entities/tags/all?set_id={s1['id']}", headers=headers)
        tags = resp.json()
        assert "alpha" in tags
        assert "beta" not in tags
