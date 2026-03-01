"""Integration tests for model tag CRUD operations (WP-9: Tag Management System)."""
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
    name: str = "Tag Test Model",
) -> str:
    """Create a test model and return its ID."""
    resp = await client.post(
        "/api/models",
        json={
            "model_type": "simple-view",
            "name": name,
            "description": "Model for tag testing",
            "data": {"placements": []},
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.mark.asyncio
class TestModelTagCRUD:
    """Test model tag add/remove via API."""

    async def test_add_tag_to_model(self, client: httpx.AsyncClient):
        """Adding a tag returns 201 with tag details."""
        headers = await _auth_headers(client)
        model_id = await _create_model(client, headers)
        resp = await client.post(
            f"/api/models/{model_id}/tags",
            json={"tag": "architecture"},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["model_id"] == model_id
        assert data["tag"] == "architecture"

    async def test_duplicate_tag_returns_409(self, client: httpx.AsyncClient):
        """Adding the same tag twice returns 409."""
        headers = await _auth_headers(client)
        model_id = await _create_model(client, headers)
        await client.post(
            f"/api/models/{model_id}/tags",
            json={"tag": "dup-tag"},
            headers=headers,
        )
        resp = await client.post(
            f"/api/models/{model_id}/tags",
            json={"tag": "dup-tag"},
            headers=headers,
        )
        assert resp.status_code == 409

    async def test_remove_tag_from_model(self, client: httpx.AsyncClient):
        """Removing a tag returns 200."""
        headers = await _auth_headers(client)
        model_id = await _create_model(client, headers)
        await client.post(
            f"/api/models/{model_id}/tags",
            json={"tag": "removable"},
            headers=headers,
        )
        resp = await client.delete(
            f"/api/models/{model_id}/tags/removable",
            headers=headers,
        )
        assert resp.status_code == 200

    async def test_model_response_includes_tags(self, client: httpx.AsyncClient):
        """GET model response includes tags array."""
        headers = await _auth_headers(client)
        model_id = await _create_model(client, headers)
        await client.post(
            f"/api/models/{model_id}/tags",
            json={"tag": "included"},
            headers=headers,
        )
        resp = await client.get(f"/api/models/{model_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "tags" in data
        assert "included" in data["tags"]

    async def test_empty_tag_returns_400(self, client: httpx.AsyncClient):
        """Empty tag returns 400."""
        headers = await _auth_headers(client)
        model_id = await _create_model(client, headers)
        resp = await client.post(
            f"/api/models/{model_id}/tags",
            json={"tag": ""},
            headers=headers,
        )
        assert resp.status_code == 400

    async def test_long_tag_returns_400(self, client: httpx.AsyncClient):
        """Tag over 50 characters returns 400."""
        headers = await _auth_headers(client)
        model_id = await _create_model(client, headers)
        resp = await client.post(
            f"/api/models/{model_id}/tags",
            json={"tag": "x" * 51},
            headers=headers,
        )
        assert resp.status_code == 400

    async def test_list_models_includes_tags(self, client: httpx.AsyncClient):
        """GET models list includes tags for each model."""
        headers = await _auth_headers(client)
        model_id = await _create_model(client, headers, name="Tagged List Model")
        await client.post(
            f"/api/models/{model_id}/tags",
            json={"tag": "listed"},
            headers=headers,
        )
        resp = await client.get("/api/models", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        tagged = [i for i in data["items"] if i["id"] == model_id]
        assert len(tagged) > 0
        assert "listed" in tagged[0].get("tags", [])

    async def test_all_tags_includes_model_tags(self, client: httpx.AsyncClient):
        """GET /api/tags/all includes model tags."""
        headers = await _auth_headers(client)
        model_id = await _create_model(client, headers, name="Global Tag Model")
        await client.post(
            f"/api/models/{model_id}/tags",
            json={"tag": "global-model-tag"},
            headers=headers,
        )
        resp = await client.get("/api/entities/tags/all", headers=headers)
        assert resp.status_code == 200
        tags = resp.json()
        assert "global-model-tag" in tags
