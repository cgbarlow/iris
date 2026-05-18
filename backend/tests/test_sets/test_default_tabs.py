"""Tests for per-set tab defaults (v6.14.0, ADR-204).

Round-trips ``package_tab_default`` and ``view_tab_default`` through
the ``POST /api/sets``, ``GET /api/sets/{id}``, and
``PUT /api/sets/{id}`` endpoints.

Defaults:
- ``package_tab_default = 'relationships'``
- ``view_tab_default = 'canvas'``

Both fields are tri-state on update: omitting / sending None leaves
the column unchanged, mirroring the ADR-202 hierarchy_sort behaviour
and the ``_put_merge_partial`` MCP contract.
"""

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
        transport=transport, base_url="http://test",
    ) as c:
        yield c
    await db_manager.close()


async def _auth(client: httpx.AsyncClient) -> dict[str, str]:
    await client.post(
        "/api/auth/setup",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.mark.asyncio
async def test_new_set_defaults_to_relationships_and_canvas(
    client: httpx.AsyncClient,
) -> None:
    h = await _auth(client)
    r = await client.post("/api/sets", json={"name": "S1"}, headers=h)
    assert r.status_code == 201
    body = r.json()
    assert body["package_tab_default"] == "relationships"
    assert body["view_tab_default"] == "canvas"


@pytest.mark.asyncio
async def test_get_returns_current_tab_defaults(
    client: httpx.AsyncClient,
) -> None:
    h = await _auth(client)
    r = await client.post("/api/sets", json={"name": "S2"}, headers=h)
    set_id = r.json()["id"]
    g = await client.get(f"/api/sets/{set_id}", headers=h)
    assert g.status_code == 200
    assert g.json()["package_tab_default"] == "relationships"
    assert g.json()["view_tab_default"] == "canvas"


@pytest.mark.asyncio
async def test_put_persists_package_tab_default(
    client: httpx.AsyncClient,
) -> None:
    h = await _auth(client)
    r = await client.post("/api/sets", json={"name": "S3"}, headers=h)
    set_id = r.json()["id"]
    u = await client.put(
        f"/api/sets/{set_id}",
        json={"name": "S3", "package_tab_default": "details"},
        headers=h,
    )
    assert u.status_code == 200
    assert u.json()["package_tab_default"] == "details"
    assert u.json()["view_tab_default"] == "canvas"  # unchanged


@pytest.mark.asyncio
async def test_put_persists_view_tab_default(
    client: httpx.AsyncClient,
) -> None:
    h = await _auth(client)
    r = await client.post("/api/sets", json={"name": "S4"}, headers=h)
    set_id = r.json()["id"]
    u = await client.put(
        f"/api/sets/{set_id}",
        json={"name": "S4", "view_tab_default": "details"},
        headers=h,
    )
    assert u.status_code == 200
    assert u.json()["view_tab_default"] == "details"
    assert u.json()["package_tab_default"] == "relationships"


@pytest.mark.asyncio
async def test_partial_put_leaves_other_field_alone(
    client: httpx.AsyncClient,
) -> None:
    h = await _auth(client)
    r = await client.post("/api/sets", json={"name": "S5"}, headers=h)
    set_id = r.json()["id"]
    # First change both.
    await client.put(
        f"/api/sets/{set_id}",
        json={
            "name": "S5",
            "package_tab_default": "details",
            "view_tab_default": "relationships",
        },
        headers=h,
    )
    # Then update only one — the other must survive.
    u = await client.put(
        f"/api/sets/{set_id}",
        json={"name": "S5", "package_tab_default": "relationships"},
        headers=h,
    )
    assert u.status_code == 200
    assert u.json()["package_tab_default"] == "relationships"
    assert u.json()["view_tab_default"] == "relationships"  # preserved


@pytest.mark.asyncio
async def test_invalid_package_tab_default_returns_422(
    client: httpx.AsyncClient,
) -> None:
    h = await _auth(client)
    r = await client.post("/api/sets", json={"name": "S6"}, headers=h)
    set_id = r.json()["id"]
    u = await client.put(
        f"/api/sets/{set_id}",
        json={"name": "S6", "package_tab_default": "bogus"},
        headers=h,
    )
    assert u.status_code == 422


@pytest.mark.asyncio
async def test_invalid_view_tab_default_returns_422(
    client: httpx.AsyncClient,
) -> None:
    h = await _auth(client)
    r = await client.post("/api/sets", json={"name": "S7"}, headers=h)
    set_id = r.json()["id"]
    u = await client.put(
        f"/api/sets/{set_id}",
        json={"name": "S7", "view_tab_default": "history"},
        headers=h,
    )
    assert u.status_code == 422
