"""Integration tests for collections CRUD API routes."""

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


class TestListCollections:
    async def test_empty_list(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/collections", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == {"items": []}


class TestCreateCollection:
    async def test_create_returns_201(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/collections",
            json={"name": "My Collection", "description": "Test collection"},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "My Collection"
        assert data["description"] == "Test collection"
        assert data["set_count"] == 0
        assert data["diagram_count"] == 0
        assert data["element_count"] == 0

    async def test_duplicate_name_returns_409(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        await client.post(
            "/api/collections",
            json={"name": "Unique Collection"},
            headers=headers,
        )
        resp = await client.post(
            "/api/collections",
            json={"name": "Unique Collection"},
            headers=headers,
        )
        assert resp.status_code == 409


class TestGetCollection:
    async def test_get_existing_collection(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        create_resp = await client.post(
            "/api/collections",
            json={"name": "Fetch Me", "description": "Fetchable"},
            headers=headers,
        )
        collection_id = create_resp.json()["id"]
        resp = await client.get(f"/api/collections/{collection_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Fetch Me"
        assert resp.json()["description"] == "Fetchable"

    async def test_get_nonexistent_returns_404(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/collections/nonexistent-id", headers=headers)
        assert resp.status_code == 404


class TestUpdateCollection:
    async def test_update_name_and_description(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        create_resp = await client.post(
            "/api/collections",
            json={"name": "Old Name"},
            headers=headers,
        )
        collection_id = create_resp.json()["id"]
        resp = await client.put(
            f"/api/collections/{collection_id}",
            json={"name": "New Name", "description": "Updated"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"
        assert resp.json()["description"] == "Updated"


class TestDeleteCollection:
    async def test_soft_delete(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        create_resp = await client.post(
            "/api/collections",
            json={"name": "Temp Collection"},
            headers=headers,
        )
        collection_id = create_resp.json()["id"]
        resp = await client.delete(f"/api/collections/{collection_id}", headers=headers)
        assert resp.status_code == 204

        # Verify it no longer appears in the list
        list_resp = await client.get("/api/collections", headers=headers)
        names = [c["name"] for c in list_resp.json()["items"]]
        assert "Temp Collection" not in names

        # Verify GET returns 404
        get_resp = await client.get(f"/api/collections/{collection_id}", headers=headers)
        assert get_resp.status_code == 404


class TestCollectionSetIntegration:
    async def test_create_set_with_collection_id(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        # Create a collection
        coll_resp = await client.post(
            "/api/collections",
            json={"name": "Integration Collection"},
            headers=headers,
        )
        assert coll_resp.status_code == 201
        collection_id = coll_resp.json()["id"]

        # Create a set with collection_id
        set_resp = await client.post(
            "/api/sets",
            json={"name": "Linked Set", "collection_id": collection_id},
            headers=headers,
        )
        assert set_resp.status_code == 201
        assert set_resp.json()["collection_id"] == collection_id

    async def test_get_sets_returns_collection_id_and_name(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        coll = (await client.post(
            "/api/collections",
            json={"name": "Named Collection"},
            headers=headers,
        )).json()
        set_resp = (await client.post(
            "/api/sets",
            json={"name": "Set In Named", "collection_id": coll["id"]},
            headers=headers,
        )).json()

        # GET single set should include collection_id and collection_name
        resp = await client.get(f"/api/sets/{set_resp['id']}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["collection_id"] == coll["id"]
        assert data["collection_name"] == "Named Collection"

    async def test_filter_sets_by_collection_id(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        coll = (await client.post(
            "/api/collections",
            json={"name": "Filter Collection"},
            headers=headers,
        )).json()
        await client.post(
            "/api/sets",
            json={"name": "InCollection", "collection_id": coll["id"]},
            headers=headers,
        )
        await client.post(
            "/api/sets",
            json={"name": "NotInCollection"},
            headers=headers,
        )

        # Filter by collection_id
        resp = await client.get(f"/api/sets?collection_id={coll['id']}", headers=headers)
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["name"] == "InCollection"

    async def test_collection_sets_endpoint(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        coll = (await client.post(
            "/api/collections",
            json={"name": "Sets Endpoint Collection"},
            headers=headers,
        )).json()
        await client.post(
            "/api/sets",
            json={"name": "Set Via Endpoint", "collection_id": coll["id"]},
            headers=headers,
        )

        # GET /api/collections/{id}/sets should return the set
        resp = await client.get(f"/api/collections/{coll['id']}/sets", headers=headers)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["name"] == "Set Via Endpoint"

    async def test_collection_counts(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        coll = (await client.post(
            "/api/collections",
            json={"name": "Counting Collection"},
            headers=headers,
        )).json()
        collection_id = coll["id"]

        # Create a set in the collection
        s = (await client.post(
            "/api/sets",
            json={"name": "Count Set", "collection_id": collection_id},
            headers=headers,
        )).json()

        # Create a diagram in the set
        await client.post(
            "/api/diagrams",
            json={"diagram_type": "simple-view", "name": "D1", "data": {}, "set_id": s["id"]},
            headers=headers,
        )

        # Create an element in the set
        await client.post(
            "/api/elements",
            json={"element_type": "component", "name": "E1", "data": {}, "set_id": s["id"]},
            headers=headers,
        )

        # Verify counts on the collection
        resp = await client.get(f"/api/collections/{collection_id}", headers=headers)
        data = resp.json()
        assert data["set_count"] == 1
        assert data["diagram_count"] == 1
        assert data["element_count"] == 1

    async def test_delete_collection_unlinks_sets(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        coll = (await client.post(
            "/api/collections",
            json={"name": "Unlink Collection"},
            headers=headers,
        )).json()
        collection_id = coll["id"]

        s = (await client.post(
            "/api/sets",
            json={"name": "Linked Then Unlinked", "collection_id": collection_id},
            headers=headers,
        )).json()

        # Verify set is linked
        get_resp = await client.get(f"/api/sets/{s['id']}", headers=headers)
        assert get_resp.json()["collection_id"] == collection_id

        # Delete the collection
        del_resp = await client.delete(f"/api/collections/{collection_id}", headers=headers)
        assert del_resp.status_code == 204

        # Verify set is unlinked (collection_id becomes null)
        get_resp = await client.get(f"/api/sets/{s['id']}", headers=headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["collection_id"] is None
