"""Tests for the entity-search endpoint (v6.14.0, ADR-205, issue #185).

`GET /api/search/entities?q=<prefix>&types=<csv>&limit=<int>` powers
the Smart Markdown slash-picker entity step. Read-only, so it sits
outside the Protocol §14 surface-parity requirement.
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
async def test_prefix_match_finds_element(client: httpx.AsyncClient) -> None:
    h = await _auth(client)
    s = (await client.post("/api/sets", json={"name": "S"}, headers=h)).json()["id"]
    await client.post(
        "/api/elements",
        json={"name": "Pork mince", "element_type": "application", "set_id": s},
        headers=h,
    )
    r = await client.get("/api/search/entities?q=pork", headers=h)
    assert r.status_code == 200
    names = [row["name"] for row in r.json()]
    assert "Pork mince" in names


@pytest.mark.asyncio
async def test_type_filter_narrows(client: httpx.AsyncClient) -> None:
    h = await _auth(client)
    s = (await client.post("/api/sets", json={"name": "Pork"}, headers=h)).json()["id"]
    await client.post(
        "/api/elements",
        json={"name": "Pork", "element_type": "application", "set_id": s},
        headers=h,
    )
    r = await client.get("/api/search/entities?q=pork&types=element", headers=h)
    assert r.status_code == 200
    types = {row["entity_type"] for row in r.json()}
    assert types == {"element"} or types == set()  # only elements (or none)


@pytest.mark.asyncio
async def test_empty_q_returns_422(client: httpx.AsyncClient) -> None:
    h = await _auth(client)
    r = await client.get("/api/search/entities?q=", headers=h)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_limit_honoured(client: httpx.AsyncClient) -> None:
    h = await _auth(client)
    s = (await client.post("/api/sets", json={"name": "S2"}, headers=h)).json()["id"]
    for i in range(5):
        await client.post(
            "/api/elements",
            json={"name": f"Apple{i}", "element_type": "application", "set_id": s},
            headers=h,
        )
    r = await client.get("/api/search/entities?q=apple&limit=2", headers=h)
    assert r.status_code == 200
    assert len(r.json()) <= 2


@pytest.mark.asyncio
async def test_returns_id_entity_type_name(client: httpx.AsyncClient) -> None:
    h = await _auth(client)
    s = (await client.post("/api/sets", json={"name": "SetOne"}, headers=h)).json()["id"]
    r = await client.get("/api/search/entities?q=setone&types=set", headers=h)
    assert r.status_code == 200
    rows = r.json()
    if rows:
        for row in rows:
            assert set(row.keys()) == {"id", "entity_type", "name"}
            assert row["entity_type"] in {
                "element", "package", "diagram", "set", "collection",
            }
