"""Integration tests for batch operations API routes."""

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
    client: httpx.AsyncClient, headers: dict[str, str], *, name: str = "Test"
) -> dict:
    resp = await client.post(
        "/api/models",
        json={"model_type": "simple-view", "name": name, "data": {}},
        headers=headers,
    )
    return resp.json()


async def _create_entity(
    client: httpx.AsyncClient, headers: dict[str, str], *, name: str = "Test"
) -> dict:
    resp = await client.post(
        "/api/entities",
        json={"entity_type": "component", "name": name, "data": {}},
        headers=headers,
    )
    return resp.json()


class TestBatchDeleteModels:
    async def test_delete_multiple_models(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        m1 = await _create_model(client, headers, name="Del1")
        m2 = await _create_model(client, headers, name="Del2")
        resp = await client.post(
            "/api/batch/models/delete",
            json={"ids": [m1["id"], m2["id"]]},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["succeeded"] == 2
        assert data["failed"] == 0

    async def test_partial_failure(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        m1 = await _create_model(client, headers, name="Real")
        resp = await client.post(
            "/api/batch/models/delete",
            json={"ids": [m1["id"], "nonexistent"]},
            headers=headers,
        )
        data = resp.json()
        assert data["succeeded"] == 1
        assert data["failed"] == 1


class TestBatchCloneModels:
    async def test_clone_models(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        m1 = await _create_model(client, headers, name="Original")
        resp = await client.post(
            "/api/batch/models/clone",
            json={"ids": [m1["id"]]},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["succeeded"] == 1

        # Verify clone exists
        list_resp = await client.get("/api/models", headers=headers)
        names = [m["name"] for m in list_resp.json()["items"]]
        assert "Original (Copy)" in names


class TestBatchSetModels:
    async def test_move_models_to_set(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        s = (await client.post("/api/sets", json={"name": "Target"}, headers=headers)).json()
        m1 = await _create_model(client, headers, name="ToMove")
        resp = await client.post(
            "/api/batch/models/set",
            json={"ids": [m1["id"]], "set_id": s["id"]},
            headers=headers,
        )
        assert resp.json()["succeeded"] == 1

        # Verify model is now in target set
        model_resp = await client.get(f"/api/models/{m1['id']}", headers=headers)
        assert model_resp.json()["set_id"] == s["id"]

    async def test_invalid_set_returns_all_failed(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        m1 = await _create_model(client, headers, name="M")
        resp = await client.post(
            "/api/batch/models/set",
            json={"ids": [m1["id"]], "set_id": "nonexistent"},
            headers=headers,
        )
        data = resp.json()
        assert data["failed"] == 1
        assert data["succeeded"] == 0


class TestBatchTagsModels:
    async def test_add_tags(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        m1 = await _create_model(client, headers, name="TagMe")
        resp = await client.post(
            "/api/batch/models/tags",
            json={"ids": [m1["id"]], "add_tags": ["v1.0", "release"], "remove_tags": []},
            headers=headers,
        )
        assert resp.json()["succeeded"] == 1

        # Verify tags
        model_resp = await client.get(f"/api/models/{m1['id']}", headers=headers)
        tags = model_resp.json()["tags"]
        assert "v1.0" in tags
        assert "release" in tags

    async def test_remove_tags(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        m1 = await _create_model(client, headers, name="UntagMe")
        # Add tags first
        await client.post(
            f"/api/models/{m1['id']}/tags",
            json={"tag": "old"},
            headers=headers,
        )
        resp = await client.post(
            "/api/batch/models/tags",
            json={"ids": [m1["id"]], "add_tags": [], "remove_tags": ["old"]},
            headers=headers,
        )
        assert resp.json()["succeeded"] == 1
        model_resp = await client.get(f"/api/models/{m1['id']}", headers=headers)
        assert "old" not in model_resp.json()["tags"]


class TestBatchDeleteEntities:
    async def test_delete_entities(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        e1 = await _create_entity(client, headers, name="EDel1")
        e2 = await _create_entity(client, headers, name="EDel2")
        resp = await client.post(
            "/api/batch/entities/delete",
            json={"ids": [e1["id"], e2["id"]]},
            headers=headers,
        )
        assert resp.json()["succeeded"] == 2


class TestBatchCloneEntities:
    async def test_clone_entities(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        e1 = await _create_entity(client, headers, name="EOriginal")
        resp = await client.post(
            "/api/batch/entities/clone",
            json={"ids": [e1["id"]]},
            headers=headers,
        )
        assert resp.json()["succeeded"] == 1

        list_resp = await client.get("/api/entities", headers=headers)
        names = [e["name"] for e in list_resp.json()["items"]]
        assert "EOriginal (Copy)" in names


class TestBatchSetEntities:
    async def test_move_entities_to_set(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        s = (await client.post("/api/sets", json={"name": "ETarget"}, headers=headers)).json()
        e1 = await _create_entity(client, headers, name="EToMove")
        resp = await client.post(
            "/api/batch/entities/set",
            json={"ids": [e1["id"]], "set_id": s["id"]},
            headers=headers,
        )
        assert resp.json()["succeeded"] == 1

        entity_resp = await client.get(f"/api/entities/{e1['id']}", headers=headers)
        assert entity_resp.json()["set_id"] == s["id"]


class TestBatchTagsEntities:
    async def test_add_and_remove_tags(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        e1 = await _create_entity(client, headers, name="ETagMe")
        # Add a tag first
        await client.post(
            f"/api/entities/{e1['id']}/tags",
            json={"tag": "remove-me"},
            headers=headers,
        )
        resp = await client.post(
            "/api/batch/entities/tags",
            json={"ids": [e1["id"]], "add_tags": ["new-tag"], "remove_tags": ["remove-me"]},
            headers=headers,
        )
        assert resp.json()["succeeded"] == 1
        entity_resp = await client.get(f"/api/entities/{e1['id']}", headers=headers)
        tags = entity_resp.json()["tags"]
        assert "new-tag" in tags
        assert "remove-me" not in tags


class TestBatchValidation:
    async def test_empty_ids_returns_422(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/batch/models/delete",
            json={"ids": []},
            headers=headers,
        )
        assert resp.status_code == 422

    async def test_requires_auth(self, client: httpx.AsyncClient) -> None:
        resp = await client.post(
            "/api/batch/models/delete",
            json={"ids": ["test"]},
        )
        assert resp.status_code == 401
