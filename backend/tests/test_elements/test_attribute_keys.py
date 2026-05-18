"""Tests for the element attribute-keys endpoint (v6.14.0, ADR-205).

`GET /api/elements/{id}/attribute-keys` returns the sorted list of
keys in the element's current ``data`` JSON. Powers the Smart Markdown
slash-picker field step for elements.
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
async def test_returns_sorted_keys(client: httpx.AsyncClient) -> None:
    h = await _auth(client)
    s = (await client.post("/api/sets", json={"name": "S"}, headers=h)).json()["id"]
    e = (
        await client.post(
            "/api/elements",
            json={
                "name": "E",
                "element_type": "application",
                "set_id": s,
                "data": {"Unit": "g", "Origin": "NZ", "Calories": "250"},
            },
            headers=h,
        )
    ).json()["id"]
    r = await client.get(f"/api/elements/{e}/attribute-keys", headers=h)
    assert r.status_code == 200
    assert r.json() == ["Calories", "Origin", "Unit"]  # alphabetical


@pytest.mark.asyncio
async def test_empty_for_element_without_data(client: httpx.AsyncClient) -> None:
    h = await _auth(client)
    s = (await client.post("/api/sets", json={"name": "S2"}, headers=h)).json()["id"]
    e = (
        await client.post(
            "/api/elements", json={"name": "E2", "element_type": "application", "set_id": s}, headers=h,
        )
    ).json()["id"]
    r = await client.get(f"/api/elements/{e}/attribute-keys", headers=h)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_404_for_missing_element(client: httpx.AsyncClient) -> None:
    h = await _auth(client)
    r = await client.get("/api/elements/no-such-id/attribute-keys", headers=h)
    assert r.status_code == 404
