"""CRUD tests for aggregation profiles (ADR-212, SPEC-212-a)."""

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
        debug=True, cors_origins=["http://localhost:5173"],
        database=DatabaseConfig(data_dir=str(tmp_path / "data")),
        auth=AuthConfig(
            jwt_secret="test-secret-key-that-is-at-least-32-bytes-long-for-hs256",
            argon2_time_cost=1, argon2_memory_cost=8192,
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
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await db_manager.close()


async def _auth(c: httpx.AsyncClient) -> dict:
    await c.post(
        "/api/auth/setup",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    resp = await c.post(
        "/api/auth/login",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _create_set(c, h) -> str:
    r = await c.post("/api/sets", json={"name": "S"}, headers=h)
    assert r.status_code == 201
    return r.json()["id"]


_VALID_PD = {
    "traversal": {
        "inner": {
            "collect_token_type": "element",
            "value_attribute_path": "attributes/Quantity/type",
            "skip_blank_values": True,
        },
    },
    "output": {
        "group_by": "element.name",
        "line_format": "- {element.name}: {sum_value}",
    },
}


@pytest.mark.asyncio
async def test_create_global_profile(client: httpx.AsyncClient) -> None:
    h = await _auth(client)
    r = await client.post(
        "/api/aggregation/profiles",
        json={
            "name": "Global test", "is_global": True,
            "profile_data": _VALID_PD,
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["is_global"] is True
    assert body["set_id"] is None
    assert body["profile_data"]["traversal"]["inner"]["collect_token_type"] == "element"


@pytest.mark.asyncio
async def test_create_set_scoped_profile(client: httpx.AsyncClient) -> None:
    h = await _auth(client)
    sid = await _create_set(client, h)
    r = await client.post(
        "/api/aggregation/profiles",
        json={
            "name": "Set test", "set_id": sid, "is_global": False,
            "profile_data": _VALID_PD,
        },
        headers=h,
    )
    assert r.status_code == 201
    assert r.json()["set_id"] == sid


@pytest.mark.asyncio
async def test_create_rejects_mixed_scope(client: httpx.AsyncClient) -> None:
    h = await _auth(client)
    sid = await _create_set(client, h)
    r = await client.post(
        "/api/aggregation/profiles",
        json={
            "name": "Bad", "set_id": sid, "is_global": True,
            "profile_data": _VALID_PD,
        },
        headers=h,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_rejects_invalid_profile_data(
    client: httpx.AsyncClient,
) -> None:
    h = await _auth(client)
    r = await client.post(
        "/api/aggregation/profiles",
        json={
            "name": "Bad data", "is_global": True,
            "profile_data": {"traversal": {}, "output": {}},  # missing inner
        },
        headers=h,
    )
    # Pydantic catches at the FastAPI layer.
    assert r.status_code in (422, 400)


@pytest.mark.asyncio
async def test_list_includes_seeded_globals(
    client: httpx.AsyncClient,
) -> None:
    """ADR-212 ships five seeded global profiles (m077 / m082)."""
    h = await _auth(client)
    r = await client.get(
        "/api/aggregation/profiles?include_global=true", headers=h,
    )
    assert r.status_code == 200
    names = {p["name"] for p in r.json()["items"]}
    assert {
        "Shopping list", "Sprint points rollup", "Time tracker rollup",
        "Expense report", "Reading log rollup",
    } <= names


@pytest.mark.asyncio
async def test_get_one(client: httpx.AsyncClient) -> None:
    h = await _auth(client)
    create = await client.post(
        "/api/aggregation/profiles",
        json={
            "name": "Fetchable", "is_global": True,
            "profile_data": _VALID_PD,
        },
        headers=h,
    )
    pid = create.json()["id"]
    r = await client.get(f"/api/aggregation/profiles/{pid}", headers=h)
    assert r.status_code == 200
    assert r.json()["name"] == "Fetchable"


@pytest.mark.asyncio
async def test_update_profile_data(client: httpx.AsyncClient) -> None:
    h = await _auth(client)
    create = await client.post(
        "/api/aggregation/profiles",
        json={
            "name": "Updatable", "is_global": True,
            "profile_data": _VALID_PD,
        },
        headers=h,
    )
    pid = create.json()["id"]
    new_pd = {
        "traversal": {
            "inner": {
                "collect_token_type": "element",
                "value_attribute_path": "attributes/Points/type",
                "skip_blank_values": True,
            },
        },
        "output": {
            "group_by": "element.package_name",
            "line_format": "- {element.name}: {sum_value} pts",
        },
    }
    r = await client.put(
        f"/api/aggregation/profiles/{pid}",
        json={"profile_data": new_pd, "description": "now for points"},
        headers=h,
    )
    assert r.status_code == 200
    assert (
        r.json()["profile_data"]["traversal"]["inner"]["value_attribute_path"]
        == "attributes/Points/type"
    )
    assert r.json()["description"] == "now for points"


@pytest.mark.asyncio
async def test_delete_soft_deletes(client: httpx.AsyncClient) -> None:
    h = await _auth(client)
    create = await client.post(
        "/api/aggregation/profiles",
        json={
            "name": "Deletable", "is_global": True,
            "profile_data": _VALID_PD,
        },
        headers=h,
    )
    pid = create.json()["id"]
    r = await client.delete(f"/api/aggregation/profiles/{pid}", headers=h)
    assert r.status_code == 204
    # Get returns 404 after delete.
    r = await client.get(f"/api/aggregation/profiles/{pid}", headers=h)
    assert r.status_code == 404
