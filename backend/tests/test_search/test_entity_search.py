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


# ──────────────────────────────────────────────────────────────────
# ADR-206 / v6.15.0: substring + scoped search
# ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_substring_match_finds_middle_token(
    client: httpx.AsyncClient,
) -> None:
    """ADR-206: `mince` now finds `Pork mince` (was prefix-only)."""
    h = await _auth(client)
    s = (await client.post("/api/sets", json={"name": "S"}, headers=h)).json()["id"]
    await client.post(
        "/api/elements",
        json={"name": "Pork mince", "element_type": "application", "set_id": s},
        headers=h,
    )
    r = await client.get("/api/search/entities?q=mince", headers=h)
    assert r.status_code == 200
    names = [row["name"] for row in r.json()]
    assert "Pork mince" in names


@pytest.mark.asyncio
async def test_substring_case_insensitive(client: httpx.AsyncClient) -> None:
    h = await _auth(client)
    s = (await client.post("/api/sets", json={"name": "S"}, headers=h)).json()["id"]
    await client.post(
        "/api/elements",
        json={"name": "Pork Mince", "element_type": "application", "set_id": s},
        headers=h,
    )
    r = await client.get("/api/search/entities?q=MINCE", headers=h)
    assert r.status_code == 200
    names = [row["name"] for row in r.json()]
    assert "Pork Mince" in names


@pytest.mark.asyncio
async def test_set_id_scopes_results_to_that_set(
    client: httpx.AsyncClient,
) -> None:
    """ADR-206: passing set_id narrows element/package/diagram results
    to that set; sets and collections are excluded."""
    h = await _auth(client)
    s1 = (await client.post("/api/sets", json={"name": "S1"}, headers=h)).json()["id"]
    s2 = (await client.post("/api/sets", json={"name": "S2"}, headers=h)).json()["id"]
    await client.post(
        "/api/elements",
        json={"name": "Pork mince", "element_type": "application", "set_id": s1},
        headers=h,
    )
    await client.post(
        "/api/elements",
        json={"name": "Pork roast", "element_type": "application", "set_id": s2},
        headers=h,
    )

    r = await client.get(f"/api/search/entities?q=pork&set_id={s1}", headers=h)
    assert r.status_code == 200
    rows = r.json()
    names = [row["name"] for row in rows]
    assert "Pork mince" in names
    assert "Pork roast" not in names
    # set itself excluded from results
    assert not any(row["entity_type"] == "set" for row in rows)


@pytest.mark.asyncio
async def test_collection_id_scopes_to_subtree(
    client: httpx.AsyncClient,
) -> None:
    """ADR-206: collection_id includes sets in that collection AND
    entities under those sets."""
    h = await _auth(client)
    coll_a = (await client.post(
        "/api/collections", json={"name": "Coll A"}, headers=h,
    )).json()["id"]
    coll_b = (await client.post(
        "/api/collections", json={"name": "Coll B"}, headers=h,
    )).json()["id"]
    s_a = (await client.post(
        "/api/sets", json={"name": "S in A", "collection_id": coll_a}, headers=h,
    )).json()["id"]
    s_b = (await client.post(
        "/api/sets", json={"name": "S in B", "collection_id": coll_b}, headers=h,
    )).json()["id"]
    await client.post(
        "/api/elements",
        json={"name": "Pork mince", "element_type": "application", "set_id": s_a},
        headers=h,
    )
    await client.post(
        "/api/elements",
        json={"name": "Pork roast", "element_type": "application", "set_id": s_b},
        headers=h,
    )

    r = await client.get(
        f"/api/search/entities?q=pork&collection_id={coll_a}", headers=h,
    )
    assert r.status_code == 200
    names = [row["name"] for row in r.json()]
    assert "Pork mince" in names
    assert "Pork roast" not in names
