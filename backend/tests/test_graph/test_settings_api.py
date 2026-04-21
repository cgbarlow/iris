"""Integration tests for graph settings API (ADR-117)."""

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


async def _viewer_headers(client: httpx.AsyncClient, admin_headers: dict[str, str]) -> dict[str, str]:
    await client.post(
        "/api/users",
        json={"username": "viewer1", "password": "ViewerPass123!", "role": "viewer"},
        headers=admin_headers,
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "viewer1", "password": "ViewerPass123!"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


class TestGetGraphSettings:
    async def test_allows_anonymous(self, client: httpx.AsyncClient) -> None:
        """Graph settings GET is public-readable (ADR-123). Anonymous returns 200."""
        resp = await client.get("/api/graph/settings")
        assert resp.status_code == 200

    async def test_rejects_invalid_token(self, client: httpx.AsyncClient) -> None:
        """A *present-but-invalid* token still returns 401 (SPEC-123-A)."""
        resp = await client.get(
            "/api/graph/settings",
            headers={"Authorization": "Bearer not-a-real-token"},
        )
        assert resp.status_code == 401

    async def test_returns_seeded_defaults(self, client: httpx.AsyncClient) -> None:
        headers = await _admin_headers(client)
        resp = await client.get("/api/graph/settings", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["scope_type"] == "global"
        assert data["scope_id"] == "__global__"
        s = data["settings"]
        assert s["label_density"] == 10
        assert s["node_spacing"] == 1.0
        assert s["size_contrast"] == 1.0
        assert s["link_length"] == 1.0
        assert s["nodes"]["collection"] is True
        assert s["nodes"]["element"] is True
        assert s["edges"]["hierarchy"] is True

    async def test_cascade_collection(self, client: httpx.AsyncClient) -> None:
        headers = await _admin_headers(client)
        col = await client.post("/api/collections", json={"name": "TestCol"}, headers=headers)
        col_id = col.json()["id"]
        # Set collection-level override
        await client.put(
            "/api/graph/settings",
            json={
                "scope_type": "collection",
                "scope_id": col_id,
                "settings": {"label_density": 5, "node_spacing": 2.0},
            },
            headers=headers,
        )
        resp = await client.get(f"/api/graph/settings?collection_id={col_id}", headers=headers)
        s = resp.json()["settings"]
        assert s["label_density"] == 5
        assert s["node_spacing"] == 2.0
        # Non-overridden fields fall back to global
        assert s["size_contrast"] == 1.0
        assert s["link_length"] == 1.0

    async def test_cascade_set(self, client: httpx.AsyncClient) -> None:
        headers = await _admin_headers(client)
        col = await client.post("/api/collections", json={"name": "TestCol2"}, headers=headers)
        col_id = col.json()["id"]
        s_resp = await client.post("/api/sets", json={"name": "TestSet", "collection_id": col_id}, headers=headers)
        set_id = s_resp.json()["id"]
        # Collection override
        await client.put(
            "/api/graph/settings",
            json={"scope_type": "collection", "scope_id": col_id, "settings": {"label_density": 5}},
            headers=headers,
        )
        # Set override
        await client.put(
            "/api/graph/settings",
            json={"scope_type": "set", "scope_id": set_id, "settings": {"label_density": 3, "link_length": 2.5}},
            headers=headers,
        )
        resp = await client.get(f"/api/graph/settings?set_id={set_id}&collection_id={col_id}", headers=headers)
        s = resp.json()["settings"]
        assert s["label_density"] == 3  # set overrides collection
        assert s["link_length"] == 2.5  # set-level
        assert s["node_spacing"] == 1.0  # global default (no override)


class TestPutGraphSettings:
    async def test_requires_admin(self, client: httpx.AsyncClient) -> None:
        admin_headers = await _admin_headers(client)
        viewer_headers = await _viewer_headers(client, admin_headers)
        resp = await client.put(
            "/api/graph/settings",
            json={"scope_type": "global", "scope_id": "__global__", "settings": {"label_density": 5}},
            headers=viewer_headers,
        )
        assert resp.status_code == 403

    async def test_admin_can_update_global(self, client: httpx.AsyncClient) -> None:
        headers = await _admin_headers(client)
        resp = await client.put(
            "/api/graph/settings",
            json={"scope_type": "global", "scope_id": "__global__", "settings": {"node_spacing": 2.0}},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["settings"]["node_spacing"] == 2.0
        # Verify persisted
        get_resp = await client.get("/api/graph/settings", headers=headers)
        assert get_resp.json()["settings"]["node_spacing"] == 2.0

    async def test_admin_can_set_scoped(self, client: httpx.AsyncClient) -> None:
        headers = await _admin_headers(client)
        col = await client.post("/api/collections", json={"name": "ScopedCol"}, headers=headers)
        col_id = col.json()["id"]
        resp = await client.put(
            "/api/graph/settings",
            json={"scope_type": "collection", "scope_id": col_id, "settings": {"size_contrast": 2.5}},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["scope_type"] == "collection"
        assert resp.json()["settings"]["size_contrast"] == 2.5

    async def test_default_values_match_hardcoded(self, client: httpx.AsyncClient) -> None:
        """Seeded defaults must match the canonical GRAPH_SETTINGS_DEFAULTS."""
        headers = await _admin_headers(client)
        resp = await client.get("/api/graph/settings", headers=headers)
        s = resp.json()["settings"]
        assert s["label_density"] == 10
        assert s["node_spacing"] == 1.0
        assert s["size_contrast"] == 1.0
        assert s["link_length"] == 1.0
        assert s["nodes"] == {
            "collection": True, "set": True, "package": True, "diagram": True, "element": True,
        }
        assert s["edges"]["collection_membership"] is True
        assert s["edges"]["set_membership"] is True
        assert s["edges"]["direct_diagram_links"] is True
        assert s["edges"]["hierarchy"] is True
        assert s["edges"]["element_relationship"] is True
