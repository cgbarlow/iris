"""Tests for /api/elements/{id}/data-tree (ADR-206, v6.15.0, issue #185).

Returns a single-level tree descriptor for the Smart Markdown picker's
drill UI. Optional ?path= walks deeper.
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


async def _make_element(
    client: httpx.AsyncClient, h: dict[str, str], data: dict | None,
) -> str:
    s = (await client.post(
        "/api/sets", json={"name": "S"}, headers=h,
    )).json()["id"]
    body: dict = {"name": "E", "element_type": "application", "set_id": s}
    if data is not None:
        body["data"] = data
    r = await client.post("/api/elements", json=body, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.mark.asyncio
async def test_root_dict_returns_keys(client: httpx.AsyncClient) -> None:
    h = await _auth(client)
    eid = await _make_element(
        client, h, {"Unit": "g", "tags": ["x", "y"], "attributes": []},
    )
    r = await client.get(f"/api/elements/{eid}/data-tree", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["kind"] == "dict"
    assert sorted(body["keys"]) == ["Unit", "attributes", "tags"]


@pytest.mark.asyncio
async def test_path_into_list_of_named(client: httpx.AsyncClient) -> None:
    h = await _auth(client)
    eid = await _make_element(client, h, {
        "attributes": [
            {"name": "Unit", "type": "g"},
            {"name": "Products", "type": "WW Pork"},
        ],
    })
    r = await client.get(
        f"/api/elements/{eid}/data-tree?path=attributes", headers=h,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["kind"] == "list_of_named"
    assert body["names"] == ["Unit", "Products"]


@pytest.mark.asyncio
async def test_path_into_list_unnamed(client: httpx.AsyncClient) -> None:
    h = await _auth(client)
    eid = await _make_element(client, h, {"tags": ["a", "b", "c"]})
    r = await client.get(
        f"/api/elements/{eid}/data-tree?path=tags", headers=h,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["kind"] == "list"
    assert body["length"] == 3


@pytest.mark.asyncio
async def test_path_into_named_item_then_dict(
    client: httpx.AsyncClient,
) -> None:
    h = await _auth(client)
    eid = await _make_element(client, h, {
        "attributes": [{"name": "Unit", "type": "g", "scope": "Public"}],
    })
    r = await client.get(
        f"/api/elements/{eid}/data-tree?path=attributes/Unit", headers=h,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["kind"] == "dict"
    assert sorted(body["keys"]) == ["name", "scope", "type"]


@pytest.mark.asyncio
async def test_path_to_primitive(client: httpx.AsyncClient) -> None:
    h = await _auth(client)
    eid = await _make_element(client, h, {
        "attributes": [{"name": "Unit", "type": "g"}],
    })
    r = await client.get(
        f"/api/elements/{eid}/data-tree?path=attributes/Unit/type",
        headers=h,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["kind"] == "primitive"
    assert body["value"] == "g"


@pytest.mark.asyncio
async def test_missing_path_returns_404(client: httpx.AsyncClient) -> None:
    h = await _auth(client)
    eid = await _make_element(client, h, {"Unit": "g"})
    r = await client.get(
        f"/api/elements/{eid}/data-tree?path=nope", headers=h,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_empty_data_returns_empty_kind(
    client: httpx.AsyncClient,
) -> None:
    h = await _auth(client)
    eid = await _make_element(client, h, None)
    r = await client.get(f"/api/elements/{eid}/data-tree", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["kind"] in ("empty", "dict")
    if body["kind"] == "dict":
        assert body["keys"] == []


@pytest.mark.asyncio
async def test_element_not_found(client: httpx.AsyncClient) -> None:
    h = await _auth(client)
    r = await client.get(
        "/api/elements/00000000-0000-0000-0000-000000000000/data-tree",
        headers=h,
    )
    assert r.status_code == 404
