"""Regression test for set/collection gallery thumbnail surfacing
attached images (v6.17.4 → v6.17.6, issue #205 item 5).

v6.17.4 widened `_SET_COLUMNS`/`_COLLECTION_COLUMNS` so the
`has_thumbnail_image` field returned by `GET /api/sets/{id}` and
`GET /api/sets` is TRUE when an `entity_images` attachment exists.
The user reported the gallery tile still didn't surface — this test
exercises the round-trip end-to-end so a future regression is caught
before it ships.
"""

from __future__ import annotations

import io
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


_PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\rIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01]\xcc\x86\xcf"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


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
async def test_set_has_thumbnail_image_true_after_image_attached(
    client: httpx.AsyncClient,
) -> None:
    h = await _auth(client)
    s = (await client.post("/api/sets", json={"name": "Pantry"}, headers=h)).json()
    set_id = s["id"]
    assert s["has_thumbnail_image"] is False

    r = await client.post(
        f"/api/set/{set_id}/images",
        headers=h,
        files={"file": ("tiny.png", io.BytesIO(_PNG_1X1), "image/png")},
    )
    assert r.status_code == 201, r.text

    after = await client.get(f"/api/sets/{set_id}", headers=h)
    assert after.status_code == 200
    assert after.json()["has_thumbnail_image"] is True


@pytest.mark.asyncio
async def test_set_list_has_thumbnail_image_true_after_image_attached(
    client: httpx.AsyncClient,
) -> None:
    """Gallery uses /api/sets (the list endpoint) — both code paths
    (`get_set` and `list_sets`) share `_SET_COLUMNS`, but a regression
    in either would break the gallery."""
    h = await _auth(client)
    s = (await client.post("/api/sets", json={"name": "Pantry"}, headers=h)).json()
    set_id = s["id"]
    await client.post(
        f"/api/set/{set_id}/images",
        headers=h,
        files={"file": ("tiny.png", io.BytesIO(_PNG_1X1), "image/png")},
    )
    listing = await client.get("/api/sets", headers=h)
    rows = listing.json()["items"]
    target = next((r for r in rows if r["id"] == set_id), None)
    assert target is not None
    assert target["has_thumbnail_image"] is True


@pytest.mark.asyncio
async def test_set_thumbnail_endpoint_returns_attached_image_bytes(
    client: httpx.AsyncClient,
) -> None:
    """The /api/sets/{id}/thumbnail endpoint returns the attached
    image bytes when no explicit thumbnail_image / thumbnail_diagram
    is set (the fallback path added in v6.17.4)."""
    h = await _auth(client)
    s = (await client.post("/api/sets", json={"name": "Pantry"}, headers=h)).json()
    set_id = s["id"]
    await client.post(
        f"/api/set/{set_id}/images",
        headers=h,
        files={"file": ("tiny.png", io.BytesIO(_PNG_1X1), "image/png")},
    )
    thumb = await client.get(f"/api/sets/{set_id}/thumbnail")
    assert thumb.status_code == 200
    assert thumb.headers["content-type"] == "image/png"
    assert thumb.content == _PNG_1X1


@pytest.mark.asyncio
async def test_collection_has_thumbnail_image_true_after_image_attached(
    client: httpx.AsyncClient,
) -> None:
    h = await _auth(client)
    c_resp = await client.post(
        "/api/collections", json={"name": "Groceries"}, headers=h,
    )
    coll_id = c_resp.json()["id"]
    await client.post(
        f"/api/collection/{coll_id}/images",
        headers=h,
        files={"file": ("tiny.png", io.BytesIO(_PNG_1X1), "image/png")},
    )
    after = await client.get(f"/api/collections/{coll_id}", headers=h)
    assert after.status_code == 200
    assert after.json()["has_thumbnail_image"] is True
