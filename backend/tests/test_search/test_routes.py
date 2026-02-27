"""Integration tests for search routes."""

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


class TestSearchEndpoint:
    """Verify the search API."""

    async def test_search_requires_auth(
        self, client: httpx.AsyncClient,
    ) -> None:
        resp = await client.get("/api/search?q=test")
        assert resp.status_code == 401

    async def test_search_requires_query(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        resp = await client.get("/api/search", headers=headers)
        assert resp.status_code == 422

    async def test_search_empty_results(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        resp = await client.get(
            "/api/search?q=nonexistent", headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["query"] == "nonexistent"
        assert data["results"] == []
        assert data["total"] == 0

    async def test_search_finds_entities(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        # Create an entity
        await client.post(
            "/api/entities",
            json={
                "entity_type": "application",
                "name": "Payment Gateway",
                "description": "Handles payment processing",
            },
            headers=headers,
        )

        # Search for it
        resp = await client.get(
            "/api/search?q=payment", headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        result = data["results"][0]
        assert result["result_type"] == "entity"
        assert result["name"] == "Payment Gateway"
        assert result["deep_link"].startswith("/entities/")

    async def test_search_finds_models(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        # Create a model
        await client.post(
            "/api/models",
            json={
                "model_type": "simple",
                "name": "Network Architecture",
                "description": "Core network topology",
            },
            headers=headers,
        )

        # Search for it
        resp = await client.get(
            "/api/search?q=network", headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        result = data["results"][0]
        assert result["result_type"] == "model"
        assert result["name"] == "Network Architecture"
        assert result["deep_link"].startswith("/models/")

    async def test_search_finds_both_types(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        # Create entity and model with overlapping terms
        await client.post(
            "/api/entities",
            json={
                "entity_type": "application",
                "name": "Security Scanner",
                "description": "Scans for vulnerabilities",
            },
            headers=headers,
        )
        await client.post(
            "/api/models",
            json={
                "model_type": "simple",
                "name": "Security Model",
                "description": "Security architecture overview",
            },
            headers=headers,
        )

        resp = await client.get(
            "/api/search?q=security", headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        types = {r["result_type"] for r in data["results"]}
        assert types == {"entity", "model"}

    async def test_search_respects_limit(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        # Create multiple entities
        for i in range(5):
            await client.post(
                "/api/entities",
                json={
                    "entity_type": "application",
                    "name": f"Widget Service {i}",
                },
                headers=headers,
            )

        resp = await client.get(
            "/api/search?q=widget&limit=2", headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["total"] <= 2

    async def test_search_excludes_deleted_entities(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        # Create then delete an entity
        create_resp = await client.post(
            "/api/entities",
            json={
                "entity_type": "application",
                "name": "Ephemeral Thing",
            },
            headers=headers,
        )
        entity_id = create_resp.json()["id"]
        await client.delete(
            f"/api/entities/{entity_id}",
            headers={**headers, "If-Match": "1"},
        )

        resp = await client.get(
            "/api/search?q=ephemeral", headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    async def test_search_description_match(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        await client.post(
            "/api/entities",
            json={
                "entity_type": "application",
                "name": "Generic Service",
                "description": "Handles cryptographic operations",
            },
            headers=headers,
        )

        resp = await client.get(
            "/api/search?q=cryptographic", headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1
        assert resp.json()["results"][0]["name"] == "Generic Service"
