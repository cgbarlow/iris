"""Tests for entity stats and models endpoints."""

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
async def client_and_db(
    app_config: AppConfig,
) -> AsyncIterator[tuple[httpx.AsyncClient, DatabaseManager]]:
    application = create_app(app_config)
    db_manager = DatabaseManager(app_config.database)
    await initialize_databases(db_manager)
    application.state.db_manager = db_manager
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as c:
        yield c, db_manager
    await db_manager.close()


async def _setup_and_get_token(client: httpx.AsyncClient) -> str:
    """Create admin, login, return access token."""
    await client.post(
        "/api/auth/setup",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    return resp.json()["access_token"]


async def _create_entity(
    client: httpx.AsyncClient, token: str, name: str, entity_type: str = "component"
) -> dict:
    """Create an entity and return response."""
    resp = await client.post(
        "/api/entities",
        json={"name": name, "entity_type": entity_type, "data": {}},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


class TestEntityModelsEndpoint:
    """Tests for GET /api/entities/{id}/models."""

    async def test_returns_empty_when_no_models(
        self, client_and_db: tuple[httpx.AsyncClient, DatabaseManager]
    ) -> None:
        client, _ = client_and_db
        token = await _setup_and_get_token(client)
        entity = await _create_entity(client, token, "TestEntity")

        resp = await client.get(
            f"/api/entities/{entity['id']}/models",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_returns_models_referencing_entity(
        self, client_and_db: tuple[httpx.AsyncClient, DatabaseManager]
    ) -> None:
        client, _ = client_and_db
        token = await _setup_and_get_token(client)
        entity = await _create_entity(client, token, "TestEntity")

        # Create a model that references the entity in its data
        model_resp = await client.post(
            "/api/models",
            json={
                "name": "Test Model",
                "model_type": "component_diagram",
                "data": {"nodes": [{"id": entity["id"], "type": "component"}]},
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert model_resp.status_code == 201

        resp = await client.get(
            f"/api/entities/{entity['id']}/models",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        models = resp.json()
        assert len(models) == 1
        assert models[0]["name"] == "Test Model"
        assert models[0]["model_type"] == "component_diagram"

    async def test_returns_404_for_nonexistent_entity(
        self, client_and_db: tuple[httpx.AsyncClient, DatabaseManager]
    ) -> None:
        client, _ = client_and_db
        token = await _setup_and_get_token(client)

        resp = await client.get(
            "/api/entities/nonexistent-id/models",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404


class TestEntityStatsEndpoint:
    """Tests for GET /api/entities/{id}/stats."""

    async def test_returns_zero_counts_for_new_entity(
        self, client_and_db: tuple[httpx.AsyncClient, DatabaseManager]
    ) -> None:
        client, _ = client_and_db
        token = await _setup_and_get_token(client)
        entity = await _create_entity(client, token, "TestEntity")

        resp = await client.get(
            f"/api/entities/{entity['id']}/stats",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        stats = resp.json()
        assert stats["relationship_count"] == 0
        assert stats["model_usage_count"] == 0

    async def test_counts_relationships(
        self, client_and_db: tuple[httpx.AsyncClient, DatabaseManager]
    ) -> None:
        client, _ = client_and_db
        token = await _setup_and_get_token(client)
        entity1 = await _create_entity(client, token, "Source")
        entity2 = await _create_entity(client, token, "Target")

        # Create relationship
        await client.post(
            "/api/relationships",
            json={
                "source_entity_id": entity1["id"],
                "target_entity_id": entity2["id"],
                "relationship_type": "uses",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        resp = await client.get(
            f"/api/entities/{entity1['id']}/stats",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        stats = resp.json()
        assert stats["relationship_count"] == 1

    async def test_counts_model_usage(
        self, client_and_db: tuple[httpx.AsyncClient, DatabaseManager]
    ) -> None:
        client, _ = client_and_db
        token = await _setup_and_get_token(client)
        entity = await _create_entity(client, token, "TestEntity")

        # Create model referencing entity
        await client.post(
            "/api/models",
            json={
                "name": "Model A",
                "model_type": "component_diagram",
                "data": {"nodes": [{"id": entity["id"]}]},
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        resp = await client.get(
            f"/api/entities/{entity['id']}/stats",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        stats = resp.json()
        assert stats["model_usage_count"] == 1

    async def test_returns_404_for_nonexistent_entity(
        self, client_and_db: tuple[httpx.AsyncClient, DatabaseManager]
    ) -> None:
        client, _ = client_and_db
        token = await _setup_and_get_token(client)

        resp = await client.get(
            "/api/entities/nonexistent-id/stats",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404
