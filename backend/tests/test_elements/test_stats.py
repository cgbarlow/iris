"""Tests for element stats and diagrams endpoints."""

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


async def _create_element(
    client: httpx.AsyncClient, token: str, name: str, element_type: str = "component"
) -> dict:
    """Create an element and return response."""
    resp = await client.post(
        "/api/elements",
        json={"name": name, "element_type": element_type, "data": {}},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()


class TestElementDiagramsEndpoint:
    """Tests for GET /api/elements/{id}/diagrams."""

    async def test_returns_empty_when_no_diagrams(
        self, client_and_db: tuple[httpx.AsyncClient, DatabaseManager]
    ) -> None:
        client, _ = client_and_db
        token = await _setup_and_get_token(client)
        element = await _create_element(client, token, "TestElement")

        resp = await client.get(
            f"/api/elements/{element['id']}/diagrams",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_returns_diagrams_referencing_element(
        self, client_and_db: tuple[httpx.AsyncClient, DatabaseManager]
    ) -> None:
        client, _ = client_and_db
        token = await _setup_and_get_token(client)
        element = await _create_element(client, token, "TestElement")

        # Create a diagram that references the element in its data
        diagram_resp = await client.post(
            "/api/diagrams",
            json={
                "name": "Test Diagram",
                "diagram_type": "component_diagram",
                "data": {"nodes": [{"id": element["id"], "type": "component"}]},
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert diagram_resp.status_code == 201

        resp = await client.get(
            f"/api/elements/{element['id']}/diagrams",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        diagrams = resp.json()
        assert len(diagrams) == 1
        assert diagrams[0]["name"] == "Test Diagram"
        assert diagrams[0]["diagram_type"] == "component_diagram"

    async def test_returns_404_for_nonexistent_element(
        self, client_and_db: tuple[httpx.AsyncClient, DatabaseManager]
    ) -> None:
        client, _ = client_and_db
        token = await _setup_and_get_token(client)

        resp = await client.get(
            "/api/elements/nonexistent-id/diagrams",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404


class TestElementStatsEndpoint:
    """Tests for GET /api/elements/{id}/stats."""

    async def test_returns_zero_counts_for_new_element(
        self, client_and_db: tuple[httpx.AsyncClient, DatabaseManager]
    ) -> None:
        client, _ = client_and_db
        token = await _setup_and_get_token(client)
        element = await _create_element(client, token, "TestElement")

        resp = await client.get(
            f"/api/elements/{element['id']}/stats",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        stats = resp.json()
        assert stats["relationship_count"] == 0
        assert stats["diagram_usage_count"] == 0

    async def test_counts_relationships(
        self, client_and_db: tuple[httpx.AsyncClient, DatabaseManager]
    ) -> None:
        client, _ = client_and_db
        token = await _setup_and_get_token(client)
        element1 = await _create_element(client, token, "Source")
        element2 = await _create_element(client, token, "Target")

        # Create relationship
        await client.post(
            "/api/relationships",
            json={
                "source_element_id": element1["id"],
                "target_element_id": element2["id"],
                "relationship_type": "uses",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        resp = await client.get(
            f"/api/elements/{element1['id']}/stats",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        stats = resp.json()
        assert stats["relationship_count"] == 1

    async def test_counts_diagram_usage(
        self, client_and_db: tuple[httpx.AsyncClient, DatabaseManager]
    ) -> None:
        client, _ = client_and_db
        token = await _setup_and_get_token(client)
        element = await _create_element(client, token, "TestElement")

        # Create diagram referencing element
        await client.post(
            "/api/diagrams",
            json={
                "name": "Diagram A",
                "diagram_type": "component_diagram",
                "data": {"nodes": [{"id": element["id"]}]},
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        resp = await client.get(
            f"/api/elements/{element['id']}/stats",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        stats = resp.json()
        assert stats["diagram_usage_count"] == 1

    async def test_returns_404_for_nonexistent_element(
        self, client_and_db: tuple[httpx.AsyncClient, DatabaseManager]
    ) -> None:
        client, _ = client_and_db
        token = await _setup_and_get_token(client)

        resp = await client.get(
            "/api/elements/nonexistent-id/stats",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404
