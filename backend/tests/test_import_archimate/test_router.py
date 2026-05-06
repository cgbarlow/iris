"""Tests for POST /api/import/archimate."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import httpx
import pytest

from app.config import AppConfig, AuthConfig, DatabaseConfig
from app.database import DatabaseManager
from app.main import create_app
from app.startup import initialize_databases

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

REF = Path(__file__).resolve().parents[3] / "docs" / "reference" / "ArchiMate"
SAMPLE = str(REF / "sample-with-view.xml")
MSD = str(REF / "msd-map.xml")


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
async def client(app_config: AppConfig) -> "AsyncIterator[httpx.AsyncClient]":
    application = create_app(app_config)
    db_manager = DatabaseManager(app_config)
    await initialize_databases(db_manager)
    application.state.db_manager = db_manager
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
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


async def test_uploads_oex_file_and_returns_summary(
    client: httpx.AsyncClient,
) -> None:
    headers = await _auth(client)
    with open(SAMPLE, "rb") as fh:
        resp = await client.post(
            "/api/import/archimate",
            headers=headers,
            files={"file": ("sample.xml", fh.read(), "application/xml")},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["elements_created"] == 3
    assert body["relationships_created"] == 2
    assert body["diagrams_created"] == 1
    assert isinstance(body["warnings"], list)


async def test_uploads_msd_real_world_file(client: httpx.AsyncClient) -> None:
    headers = await _auth(client)
    with open(MSD, "rb") as fh:
        resp = await client.post(
            "/api/import/archimate",
            headers=headers,
            files={"file": ("msd.xml", fh.read(), "application/xml")},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["elements_created"] == 127
    assert body["relationships_created"] == 977
    assert body["diagrams_created"] == 1


async def test_rejects_non_oex_xml(client: httpx.AsyncClient) -> None:
    headers = await _auth(client)
    resp = await client.post(
        "/api/import/archimate",
        headers=headers,
        files={
            "file": (
                "bogus.xml",
                b'<?xml version="1.0"?><root xmlns="urn:other"/>',
                "application/xml",
            )
        },
    )
    assert resp.status_code == 400
    assert "ArchiMate" in resp.json()["detail"]


async def test_rejects_disallowed_extension(client: httpx.AsyncClient) -> None:
    headers = await _auth(client)
    resp = await client.post(
        "/api/import/archimate",
        headers=headers,
        files={"file": ("model.txt", b"<model/>", "text/plain")},
    )
    assert resp.status_code == 400


async def test_rejects_bogus_set_id(client: httpx.AsyncClient) -> None:
    headers = await _auth(client)
    with open(SAMPLE, "rb") as fh:
        resp = await client.post(
            "/api/import/archimate",
            headers=headers,
            data={"set_id": "nonexistent-set-id"},
            files={"file": ("sample.xml", fh.read(), "application/xml")},
        )
    assert resp.status_code == 400
    assert "set_id" in resp.json()["detail"].lower()


async def test_requires_auth(client: httpx.AsyncClient) -> None:
    with open(SAMPLE, "rb") as fh:
        resp = await client.post(
            "/api/import/archimate",
            files={"file": ("sample.xml", fh.read(), "application/xml")},
        )
    assert resp.status_code in (401, 403)
