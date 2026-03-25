"""Tests for DoView PPTX import router."""

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
        transport=transport, base_url="http://test"
    ) as c:
        yield c
    await db_manager.close()


async def _auth_headers(client: httpx.AsyncClient) -> dict[str, str]:
    """Setup admin user and return auth headers."""
    await client.post(
        "/api/auth/setup",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    tokens = resp.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


class TestImportPptxRouter:
    """POST /api/import/pptx endpoint tests."""

    async def test_rejects_non_pptx_extension(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/import/pptx",
            headers=headers,
            files={"file": ("test.txt", b"hello", "text/plain")},
        )
        assert resp.status_code == 400
        assert "pptx" in resp.json()["detail"].lower()

    async def test_rejects_non_doview_pptx(
        self, client: httpx.AsyncClient, non_doview_pptx: str,
    ) -> None:
        headers = await _auth_headers(client)
        with open(non_doview_pptx, "rb") as f:
            resp = await client.post(
                "/api/import/pptx",
                headers=headers,
                files={"file": ("test.pptx", f, "application/vnd.openxmlformats-officedocument.presentationml.presentation")},
            )
        assert resp.status_code == 400
        assert "DoView" in resp.json()["detail"]

    async def test_successful_import(
        self, client: httpx.AsyncClient, minimal_doview_pptx: str,
    ) -> None:
        headers = await _auth_headers(client)
        with open(minimal_doview_pptx, "rb") as f:
            resp = await client.post(
                "/api/import/pptx",
                headers=headers,
                files={"file": ("doview.pptx", f, "application/vnd.openxmlformats-officedocument.presentationml.presentation")},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["packages_created"] == 1
        assert data["diagrams_created"] == 3
        assert data["elements_created"] == 10
        assert data["relationships_created"] == 4
        assert data["slides_skipped"] == 1

    async def test_requires_auth(self, client: httpx.AsyncClient) -> None:
        resp = await client.post(
            "/api/import/pptx",
            files={"file": ("test.pptx", b"hello", "application/octet-stream")},
        )
        assert resp.status_code in (401, 403)
