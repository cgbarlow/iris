"""Tests for per-set element_tab_default (v6.16.0, ADR-208).

Round-trips ``element_tab_default`` through ``POST /api/sets``,
``GET /api/sets/{id}``, and ``PUT /api/sets/{id}``.

Default value: ``'relationships'`` (matches the m072 column default
and the ADR-208 decision).
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
async def test_new_set_defaults_to_relationships(
    client: httpx.AsyncClient,
) -> None:
    h = await _auth(client)
    r = await client.post("/api/sets", json={"name": "S1"}, headers=h)
    assert r.status_code == 201
    assert r.json()["element_tab_default"] == "relationships"


@pytest.mark.asyncio
async def test_update_persists_element_tab_default(
    client: httpx.AsyncClient,
) -> None:
    h = await _auth(client)
    s = (await client.post("/api/sets", json={"name": "S1"}, headers=h)).json()
    set_id = s["id"]
    r = await client.put(
        f"/api/sets/{set_id}",
        json={"name": "S1", "element_tab_default": "details"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["element_tab_default"] == "details"

    # Round-trip through GET
    g = await client.get(f"/api/sets/{set_id}", headers=h)
    assert g.json()["element_tab_default"] == "details"


@pytest.mark.asyncio
async def test_update_with_invalid_value_rejected(
    client: httpx.AsyncClient,
) -> None:
    h = await _auth(client)
    s = (await client.post("/api/sets", json={"name": "S1"}, headers=h)).json()
    r = await client.put(
        f"/api/sets/{s['id']}",
        json={"name": "S1", "element_tab_default": "invalid_tab"},
        headers=h,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_update_omitting_field_preserves_value(
    client: httpx.AsyncClient,
) -> None:
    """tri-state: omitting the field leaves the column alone."""
    h = await _auth(client)
    s = (await client.post("/api/sets", json={"name": "S1"}, headers=h)).json()
    # Set it to 'versions'
    await client.put(
        f"/api/sets/{s['id']}",
        json={"name": "S1", "element_tab_default": "versions"},
        headers=h,
    )
    # Subsequent PUT omits the field — should NOT reset to default
    r = await client.put(
        f"/api/sets/{s['id']}",
        json={"name": "S1 renamed"},
        headers=h,
    )
    assert r.status_code == 200
    assert r.json()["element_tab_default"] == "versions"
    assert r.json()["name"] == "S1 renamed"
