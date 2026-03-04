"""Integration tests for set thumbnail upload and retrieval."""

from __future__ import annotations

import struct
import zlib
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

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _minimal_png() -> bytes:
    """Create a minimal valid 1x1 white PNG."""
    # IHDR
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    ihdr_crc = zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF
    ihdr = struct.pack(">I", 13) + b"IHDR" + ihdr_data + struct.pack(">I", ihdr_crc)

    # IDAT
    raw_data = zlib.compress(b"\x00\xff\xff\xff")
    idat_crc = zlib.crc32(b"IDAT" + raw_data) & 0xFFFFFFFF
    idat = (
        struct.pack(">I", len(raw_data))
        + b"IDAT"
        + raw_data
        + struct.pack(">I", idat_crc)
    )

    # IEND
    iend_crc = zlib.crc32(b"IEND") & 0xFFFFFFFF
    iend = struct.pack(">I", 0) + b"IEND" + struct.pack(">I", iend_crc)

    return PNG_MAGIC + ihdr + idat + iend


# Minimal JPEG: SOI + APP0 + EOI
JPEG_MAGIC = b"\xff\xd8\xff\xe0"
MINIMAL_JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9"
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
    db_manager = DatabaseManager(app_config.database)
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


class TestUploadThumbnail:
    async def test_upload_png(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        s = (
            await client.post(
                "/api/sets", json={"name": "PNG Set"}, headers=headers
            )
        ).json()
        set_id = s["id"]

        png_bytes = _minimal_png()
        resp = await client.post(
            f"/api/sets/{set_id}/thumbnail",
            files={"file": ("thumb.png", png_bytes, "image/png")},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["thumbnail_source"] == "image"
        assert data["has_thumbnail_image"] is True

    async def test_upload_jpeg(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        s = (
            await client.post(
                "/api/sets", json={"name": "JPG Set"}, headers=headers
            )
        ).json()
        set_id = s["id"]

        resp = await client.post(
            f"/api/sets/{set_id}/thumbnail",
            files={"file": ("thumb.jpg", MINIMAL_JPEG, "image/jpeg")},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["thumbnail_source"] == "image"

    async def test_reject_oversized_image(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        s = (
            await client.post(
                "/api/sets", json={"name": "Big Set"}, headers=headers
            )
        ).json()
        set_id = s["id"]

        big_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * (2 * 1024 * 1024 + 1)
        resp = await client.post(
            f"/api/sets/{set_id}/thumbnail",
            files={"file": ("big.png", big_bytes, "image/png")},
            headers=headers,
        )
        assert resp.status_code == 400

    async def test_reject_invalid_content_type(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        s = (
            await client.post(
                "/api/sets", json={"name": "GIF Set"}, headers=headers
            )
        ).json()
        set_id = s["id"]

        resp = await client.post(
            f"/api/sets/{set_id}/thumbnail",
            files={"file": ("thumb.gif", b"GIF89a", "image/gif")},
            headers=headers,
        )
        assert resp.status_code == 400


class TestGetThumbnail:
    async def test_get_uploaded_thumbnail(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        s = (
            await client.post(
                "/api/sets", json={"name": "Get PNG Set"}, headers=headers
            )
        ).json()
        set_id = s["id"]

        png_bytes = _minimal_png()
        await client.post(
            f"/api/sets/{set_id}/thumbnail",
            files={"file": ("thumb.png", png_bytes, "image/png")},
            headers=headers,
        )

        resp = await client.get(f"/api/sets/{set_id}/thumbnail")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"
        assert resp.headers["cache-control"] == "public, max-age=300"
        assert resp.content[:8] == PNG_MAGIC

    async def test_get_thumbnail_404_when_none(
        self, client: httpx.AsyncClient
    ) -> None:
        headers = await _auth_headers(client)
        s = (
            await client.post(
                "/api/sets", json={"name": "No Thumb Set"}, headers=headers
            )
        ).json()
        set_id = s["id"]

        resp = await client.get(f"/api/sets/{set_id}/thumbnail")
        assert resp.status_code == 404


class TestDiagramThumbnailSource:
    async def test_set_diagram_thumbnail_source(
        self, client: httpx.AsyncClient
    ) -> None:
        headers = await _auth_headers(client)
        s = (
            await client.post(
                "/api/sets", json={"name": "Diagram Thumb Set"}, headers=headers
            )
        ).json()
        set_id = s["id"]

        # Create a diagram in this set
        m = (
            await client.post(
                "/api/diagrams",
                json={
                    "diagram_type": "simple-view",
                    "name": "Thumb Diagram",
                    "data": {},
                    "set_id": set_id,
                },
                headers=headers,
            )
        ).json()

        # Update set to use diagram thumbnail
        resp = await client.put(
            f"/api/sets/{set_id}",
            json={
                "name": "Diagram Thumb Set",
                "thumbnail_source": "diagram",
                "thumbnail_diagram_id": m["id"],
            },
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["thumbnail_source"] == "diagram"
        assert resp.json()["thumbnail_diagram_id"] == m["id"]

    async def test_diagram_not_in_set_returns_400(
        self, client: httpx.AsyncClient
    ) -> None:
        headers = await _auth_headers(client)
        s = (
            await client.post(
                "/api/sets", json={"name": "Wrong Diagram Set"}, headers=headers
            )
        ).json()
        set_id = s["id"]

        # Create a diagram in the default set (not this set)
        m = (
            await client.post(
                "/api/diagrams",
                json={
                    "diagram_type": "simple-view",
                    "name": "Other Diagram",
                    "data": {},
                },
                headers=headers,
            )
        ).json()

        # Try to use it as thumbnail — should fail
        resp = await client.put(
            f"/api/sets/{set_id}",
            json={
                "name": "Wrong Diagram Set",
                "thumbnail_source": "diagram",
                "thumbnail_diagram_id": m["id"],
            },
            headers=headers,
        )
        assert resp.status_code == 400
