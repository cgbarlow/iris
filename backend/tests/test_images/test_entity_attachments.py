"""Tests for entity image attachments (ADR-209, v6.17.0, issue #194).

Covers attach/detach/list across all five entity types, idempotency,
cross-entity reattach, the entity-type whitelist, and 404s.
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


# 1×1 PNG (8-byte signature + minimal IHDR/IDAT/IEND).
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


async def _make_set(client: httpx.AsyncClient, h: dict[str, str]) -> str:
    r = await client.post("/api/sets", json={"name": "S"}, headers=h)
    return r.json()["id"]


async def _upload_image(client: httpx.AsyncClient, h: dict[str, str]) -> str:
    r = await client.post(
        "/api/images",
        headers=h,
        files={"file": ("tiny.png", io.BytesIO(_PNG_1X1), "image/png")},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.mark.asyncio
async def test_upload_and_attach_to_set(client: httpx.AsyncClient) -> None:
    h = await _auth(client)
    set_id = await _make_set(client, h)
    r = await client.post(
        f"/api/set/{set_id}/images",
        headers=h,
        files={"file": ("tiny.png", io.BytesIO(_PNG_1X1), "image/png")},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["entity_type"] == "set"
    assert body["entity_id"] == set_id
    assert body["image_mime"] == "image/png"


@pytest.mark.asyncio
async def test_attach_existing_image(client: httpx.AsyncClient) -> None:
    h = await _auth(client)
    set_id = await _make_set(client, h)
    image_id = await _upload_image(client, h)
    r = await client.post(
        f"/api/set/{set_id}/images/attach",
        headers=h,
        json={"image_id": image_id},
    )
    assert r.status_code == 201, r.text
    assert r.json()["image_id"] == image_id


@pytest.mark.asyncio
async def test_list_returns_attachments(client: httpx.AsyncClient) -> None:
    h = await _auth(client)
    set_id = await _make_set(client, h)
    # Attach two images.
    for _ in range(2):
        await client.post(
            f"/api/set/{set_id}/images",
            headers=h,
            files={"file": ("tiny.png", io.BytesIO(_PNG_1X1), "image/png")},
        )
    r = await client.get(f"/api/set/{set_id}/images", headers=h)
    assert r.status_code == 200, r.text
    rows = r.json()
    assert len(rows) == 2
    # display_order is sequential
    orders = sorted(r["display_order"] for r in rows)
    assert orders == [0, 1]


@pytest.mark.asyncio
async def test_detach_removes_attachment(client: httpx.AsyncClient) -> None:
    h = await _auth(client)
    set_id = await _make_set(client, h)
    image_id = await _upload_image(client, h)
    a = await client.post(
        f"/api/set/{set_id}/images/attach",
        headers=h, json={"image_id": image_id},
    )
    attachment_id = a.json()["id"]
    r = await client.delete(
        f"/api/set/{set_id}/images/{attachment_id}", headers=h,
    )
    assert r.status_code == 204
    r2 = await client.get(f"/api/set/{set_id}/images", headers=h)
    assert r2.json() == []


@pytest.mark.asyncio
async def test_detach_does_not_delete_underlying_image(
    client: httpx.AsyncClient,
) -> None:
    h = await _auth(client)
    set_id = await _make_set(client, h)
    image_id = await _upload_image(client, h)
    a = await client.post(
        f"/api/set/{set_id}/images/attach",
        headers=h, json={"image_id": image_id},
    )
    await client.delete(
        f"/api/set/{set_id}/images/{a.json()['id']}", headers=h,
    )
    # The image itself still exists and serves bytes.
    g = await client.get(f"/api/images/{image_id}")
    assert g.status_code == 200
    assert g.headers["content-type"] == "image/png"


@pytest.mark.asyncio
async def test_cross_entity_reattach(client: httpx.AsyncClient) -> None:
    """Same image attached to two different entities."""
    h = await _auth(client)
    set_id = await _make_set(client, h)
    image_id = await _upload_image(client, h)
    # Attach to the set.
    a1 = await client.post(
        f"/api/set/{set_id}/images/attach",
        headers=h, json={"image_id": image_id},
    )
    assert a1.status_code == 201
    # Create a package in that set and attach the same image to it.
    p = await client.post(
        "/api/packages", json={"name": "P", "set_id": set_id}, headers=h,
    )
    pkg_id = p.json()["id"]
    a2 = await client.post(
        f"/api/package/{pkg_id}/images/attach",
        headers=h, json={"image_id": image_id},
    )
    assert a2.status_code == 201
    # Both entities list the image.
    r_set = await client.get(f"/api/set/{set_id}/images", headers=h)
    r_pkg = await client.get(f"/api/package/{pkg_id}/images", headers=h)
    assert r_set.json()[0]["image_id"] == image_id
    assert r_pkg.json()[0]["image_id"] == image_id


@pytest.mark.asyncio
async def test_duplicate_attach_is_idempotent(client: httpx.AsyncClient) -> None:
    """Attaching the same image twice to the same entity returns the
    existing attachment (UNIQUE constraint)."""
    h = await _auth(client)
    set_id = await _make_set(client, h)
    image_id = await _upload_image(client, h)
    a1 = await client.post(
        f"/api/set/{set_id}/images/attach",
        headers=h, json={"image_id": image_id},
    )
    a2 = await client.post(
        f"/api/set/{set_id}/images/attach",
        headers=h, json={"image_id": image_id},
    )
    assert a1.json()["id"] == a2.json()["id"]
    r = await client.get(f"/api/set/{set_id}/images", headers=h)
    assert len(r.json()) == 1


@pytest.mark.asyncio
async def test_unknown_entity_type_returns_422(
    client: httpx.AsyncClient,
) -> None:
    h = await _auth(client)
    r = await client.get("/api/widget/abc/images", headers=h)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_attach_to_missing_entity_returns_404(
    client: httpx.AsyncClient,
) -> None:
    h = await _auth(client)
    image_id = await _upload_image(client, h)
    r = await client.post(
        "/api/set/00000000-0000-0000-0000-000000000000/images/attach",
        headers=h, json={"image_id": image_id},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_attach_missing_image_returns_404(
    client: httpx.AsyncClient,
) -> None:
    h = await _auth(client)
    set_id = await _make_set(client, h)
    r = await client.post(
        f"/api/set/{set_id}/images/attach",
        headers=h, json={"image_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_detach_unknown_attachment_returns_404(
    client: httpx.AsyncClient,
) -> None:
    h = await _auth(client)
    set_id = await _make_set(client, h)
    r = await client.delete(
        f"/api/set/{set_id}/images/00000000-0000-0000-0000-000000000000",
        headers=h,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_is_anon_readable(client: httpx.AsyncClient) -> None:
    """MarkdownView's <img> tags resolve without sending auth, so the
    list endpoint must respond 200 to anon (matches /api/images/{id})."""
    h = await _auth(client)
    set_id = await _make_set(client, h)
    await client.post(
        f"/api/set/{set_id}/images",
        headers=h,
        files={"file": ("tiny.png", io.BytesIO(_PNG_1X1), "image/png")},
    )
    r = await client.get(f"/api/set/{set_id}/images")
    assert r.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("entity_type", ["collection", "set", "package", "diagram", "element"])
async def test_each_entity_type_supported(
    client: httpx.AsyncClient, entity_type: str,
) -> None:
    """Smoke: every supported entity type accepts attach + list."""
    h = await _auth(client)
    set_id = await _make_set(client, h)
    if entity_type == "set":
        entity_id = set_id
    elif entity_type == "collection":
        r = await client.post("/api/collections", json={"name": "C"}, headers=h)
        entity_id = r.json()["id"]
    elif entity_type == "package":
        r = await client.post(
            "/api/packages", json={"name": "P", "set_id": set_id}, headers=h,
        )
        entity_id = r.json()["id"]
    elif entity_type == "diagram":
        r = await client.post(
            "/api/diagrams",
            json={
                "name": "D", "set_id": set_id,
                "diagram_type": "text", "notation": "markdown",
            },
            headers=h,
        )
        entity_id = r.json()["id"]
    else:  # element
        r = await client.post(
            "/api/elements",
            json={"name": "E", "element_type": "application", "set_id": set_id},
            headers=h,
        )
        entity_id = r.json()["id"]

    image_id = await _upload_image(client, h)
    a = await client.post(
        f"/api/{entity_type}/{entity_id}/images/attach",
        headers=h, json={"image_id": image_id},
    )
    assert a.status_code == 201, f"{entity_type}: {a.text}"
    listing = await client.get(
        f"/api/{entity_type}/{entity_id}/images", headers=h,
    )
    assert len(listing.json()) == 1
