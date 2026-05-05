"""Integration tests for the v5.4.0 image upload endpoints (ADR-145)."""

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


# 1×1 transparent PNG (smallest legal PNG).
PNG_1x1 = bytes([
    0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
    0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
    0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
    0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4,
    0x89, 0x00, 0x00, 0x00, 0x0D, 0x49, 0x44, 0x41,
    0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00,
    0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00,
    0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE,
    0x42, 0x60, 0x82,
])


@pytest.fixture
def app_config(tmp_path: "Path") -> AppConfig:
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
async def client(app_config: AppConfig) -> "AsyncIterator[httpx.AsyncClient]":
    application = create_app(app_config)
    db_manager = DatabaseManager(app_config)
    await initialize_databases(db_manager)
    application.state.db_manager = db_manager
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as c:
        yield c
    await db_manager.close()


async def _auth_headers(client: httpx.AsyncClient) -> dict[str, str]:
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
async def test_upload_png_success(client: httpx.AsyncClient) -> None:
    """A valid PNG upload returns 201 with an id; GET retrieves the bytes."""
    headers = await _auth_headers(client)
    files = {"file": ("dot.png", io.BytesIO(PNG_1x1), "image/png")}
    resp = await client.post("/api/images", files=files, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["mime"] == "image/png"
    assert data["size_bytes"] == len(PNG_1x1)

    # GET serves the bytes back with the right Content-Type.
    get_resp = await client.get(f"/api/images/{data['id']}")
    assert get_resp.status_code == 200
    assert get_resp.headers["content-type"].startswith("image/png")
    assert get_resp.content == PNG_1x1


@pytest.mark.asyncio
async def test_upload_rejects_non_image_mime(client: httpx.AsyncClient) -> None:
    """Uploading a text file with a fake png MIME is rejected by magic-byte check."""
    headers = await _auth_headers(client)
    files = {"file": ("evil.png", io.BytesIO(b"<html>nope</html>"), "image/png")}
    resp = await client.post("/api/images", files=files, headers=headers)
    assert resp.status_code in (400, 415)


@pytest.mark.asyncio
async def test_upload_rejects_oversized(client: httpx.AsyncClient) -> None:
    """Uploads above the 5 MB cap are rejected."""
    headers = await _auth_headers(client)
    big = b"\x89PNG\r\n\x1a\n" + b"\x00" * (5 * 1024 * 1024 + 1)
    files = {"file": ("big.png", io.BytesIO(big), "image/png")}
    resp = await client.post("/api/images", files=files, headers=headers)
    assert resp.status_code in (400, 413)


@pytest.mark.asyncio
async def test_get_unknown_id_returns_404(client: httpx.AsyncClient) -> None:
    resp = await client.get("/api/images/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_upload_requires_auth(client: httpx.AsyncClient) -> None:
    files = {"file": ("dot.png", io.BytesIO(PNG_1x1), "image/png")}
    resp = await client.post("/api/images", files=files)
    assert resp.status_code in (401, 403)
