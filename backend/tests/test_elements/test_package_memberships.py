"""Tests for GET /api/elements/{id}/package-memberships (ADR-208, v6.16.0)."""

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
async def test_element_without_package_returns_empty_list(
    client: httpx.AsyncClient,
) -> None:
    h = await _auth(client)
    s = (await client.post("/api/sets", json={"name": "S"}, headers=h)).json()["id"]
    e = await client.post(
        "/api/elements",
        json={"name": "Lonely", "element_type": "application", "set_id": s},
        headers=h,
    )
    eid = e.json()["id"]
    r = await client.get(f"/api/elements/{eid}/package-memberships", headers=h)
    assert r.status_code == 200, r.text
    assert r.json() == []


@pytest.mark.asyncio
async def test_element_in_package_returns_membership(
    client: httpx.AsyncClient,
) -> None:
    h = await _auth(client)
    s = (await client.post("/api/sets", json={"name": "S"}, headers=h)).json()["id"]
    p = await client.post(
        "/api/packages",
        json={"name": "Pkg One", "set_id": s},
        headers=h,
    )
    pid = p.json()["id"]
    e = await client.post(
        "/api/elements",
        json={
            "name": "Member",
            "element_type": "application",
            "set_id": s,
            "package_id": pid,
        },
        headers=h,
    )
    eid = e.json()["id"]
    r = await client.get(f"/api/elements/{eid}/package-memberships", headers=h)
    assert r.status_code == 200, r.text
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["id"] == pid
    assert rows[0]["name"] == "Pkg One"


@pytest.mark.asyncio
async def test_missing_element_returns_404(client: httpx.AsyncClient) -> None:
    h = await _auth(client)
    r = await client.get(
        "/api/elements/00000000-0000-0000-0000-000000000000/package-memberships",
        headers=h,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_anonymous_read_allowed(client: httpx.AsyncClient) -> None:
    """Matches sibling /api/elements/{id}/... GETs which are anon-readable."""
    h = await _auth(client)
    s = (await client.post("/api/sets", json={"name": "S"}, headers=h)).json()["id"]
    e = await client.post(
        "/api/elements",
        json={"name": "X", "element_type": "application", "set_id": s},
        headers=h,
    )
    eid = e.json()["id"]
    r = await client.get(f"/api/elements/{eid}/package-memberships")
    assert r.status_code == 200
