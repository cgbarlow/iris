"""Tests for /api/picker/browse (ADR-206, v6.15.0, issue #185).

Hierarchical browse endpoint that drives the Smart Markdown picker's
browse mode. Returns breadcrumb + items + (for scope=set) counts.
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
async def test_scope_root_returns_collections(
    client: httpx.AsyncClient,
) -> None:
    h = await _auth(client)
    await client.post("/api/collections", json={"name": "Coll A"}, headers=h)
    await client.post("/api/collections", json={"name": "Coll B"}, headers=h)
    r = await client.get("/api/picker/browse?scope=root", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["breadcrumb"] == [{"label": "Root"}]
    names = [i["name"] for i in body["items"]]
    assert "Coll A" in names
    assert "Coll B" in names
    for item in body["items"]:
        assert item["entity_type"] == "collection"


@pytest.mark.asyncio
async def test_scope_collection_returns_sets(
    client: httpx.AsyncClient,
) -> None:
    h = await _auth(client)
    coll = (await client.post(
        "/api/collections", json={"name": "Groceries"}, headers=h,
    )).json()["id"]
    await client.post(
        "/api/sets",
        json={"name": "Pantry", "collection_id": coll},
        headers=h,
    )
    # A set outside the collection — must not appear.
    await client.post("/api/sets", json={"name": "Other set"}, headers=h)
    r = await client.get(
        f"/api/picker/browse?scope=collection&collection_id={coll}", headers=h,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    breadcrumb_labels = [b["label"] for b in body["breadcrumb"]]
    assert breadcrumb_labels == ["Root", "Groceries"]
    names = [i["name"] for i in body["items"]]
    assert names == ["Pantry"]
    for item in body["items"]:
        assert item["entity_type"] == "set"


@pytest.mark.asyncio
async def test_scope_set_returns_counts_no_items(
    client: httpx.AsyncClient,
) -> None:
    h = await _auth(client)
    coll = (await client.post(
        "/api/collections", json={"name": "Groceries"}, headers=h,
    )).json()["id"]
    s = (await client.post(
        "/api/sets",
        json={"name": "Pantry", "collection_id": coll},
        headers=h,
    )).json()["id"]
    await client.post(
        "/api/elements",
        json={"name": "E1", "element_type": "application", "set_id": s},
        headers=h,
    )
    await client.post(
        "/api/elements",
        json={"name": "E2", "element_type": "application", "set_id": s},
        headers=h,
    )
    await client.post(
        "/api/packages", json={"name": "P1", "set_id": s}, headers=h,
    )

    r = await client.get(
        f"/api/picker/browse?scope=set&set_id={s}", headers=h,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    breadcrumb_labels = [b["label"] for b in body["breadcrumb"]]
    assert breadcrumb_labels == ["Root", "Groceries", "Pantry"]
    assert body["items"] == []
    assert body["counts"]["elements"] == 2
    assert body["counts"]["packages"] == 1
    # diagrams count exists even when zero
    assert body["counts"]["diagrams"] == 0


@pytest.mark.asyncio
async def test_scope_set_bucket_returns_entities(
    client: httpx.AsyncClient,
) -> None:
    h = await _auth(client)
    s = (await client.post(
        "/api/sets", json={"name": "Pantry"}, headers=h,
    )).json()["id"]
    await client.post(
        "/api/elements",
        json={"name": "Beef", "element_type": "application", "set_id": s},
        headers=h,
    )
    await client.post(
        "/api/elements",
        json={"name": "Apple", "element_type": "application", "set_id": s},
        headers=h,
    )

    r = await client.get(
        f"/api/picker/browse?scope=set_bucket&set_id={s}"
        "&entity_type=element",
        headers=h,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    breadcrumb_labels = [b["label"] for b in body["breadcrumb"]]
    assert breadcrumb_labels[-2:] == ["Pantry", "Elements"]
    names = [i["name"] for i in body["items"]]
    assert sorted(names) == ["Apple", "Beef"]
    for item in body["items"]:
        assert item["entity_type"] == "element"


@pytest.mark.asyncio
async def test_set_not_found_returns_404(
    client: httpx.AsyncClient,
) -> None:
    h = await _auth(client)
    r = await client.get(
        "/api/picker/browse?scope=set&set_id=no-such-set", headers=h,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_invalid_scope_returns_422(
    client: httpx.AsyncClient,
) -> None:
    h = await _auth(client)
    r = await client.get("/api/picker/browse?scope=junk", headers=h)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_soft_deleted_excluded(
    client: httpx.AsyncClient,
) -> None:
    h = await _auth(client)
    s = (await client.post(
        "/api/sets", json={"name": "S"}, headers=h,
    )).json()["id"]
    keep_resp = await client.post(
        "/api/elements",
        json={"name": "Keep", "element_type": "application", "set_id": s},
        headers=h,
    )
    drop_resp = await client.post(
        "/api/elements",
        json={"name": "Drop", "element_type": "application", "set_id": s},
        headers=h,
    )
    e_drop = drop_resp.json()["id"]
    drop_version = drop_resp.json().get("version", 1)
    # Elements require If-Match for delete (optimistic concurrency).
    del_r = await client.delete(
        f"/api/elements/{e_drop}",
        headers={**h, "If-Match": str(drop_version)},
    )
    assert del_r.status_code in (200, 204), del_r.text

    r = await client.get(
        f"/api/picker/browse?scope=set_bucket&set_id={s}&entity_type=element",
        headers=h,
    )
    assert r.status_code == 200
    names = [i["name"] for i in r.json()["items"]]
    assert "Keep" in names
    assert "Drop" not in names
    assert keep_resp.json()["id"]  # sanity
