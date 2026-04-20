"""Tests for AI file upload extract endpoint (ADR-115)."""

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
    db_manager = DatabaseManager(app_config.database)
    await initialize_databases(db_manager)
    application.state.db_manager = db_manager
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await db_manager.close()


async def _auth_headers(client: httpx.AsyncClient) -> dict[str, str]:
    """Create admin user and return auth headers."""
    await client.post("/api/auth/setup", json={"username": "admin", "password": "AdminPass123!"})
    resp = await client.post("/api/auth/login", json={"username": "admin", "password": "AdminPass123!"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


class TestFileExtractEndpoint:
    @pytest.mark.anyio
    async def test_extract_returns_text(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        content = b"Hello, this is test content."
        resp = await client.post(
            "/api/ai/files/extract",
            files={"file": ("readme.txt", content, "text/plain")},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["filename"] == "readme.txt"
        assert data["extracted_text"] == "Hello, this is test content."
        assert data["truncated"] is False
        assert data["error"] is None
        assert data["size_bytes"] == len(content)

    @pytest.mark.anyio
    async def test_extract_size_limit(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        # Create a file larger than 5 MB
        content = b"A" * (5 * 1024 * 1024 + 1)
        resp = await client.post(
            "/api/ai/files/extract",
            files={"file": ("big.txt", content, "text/plain")},
            headers=headers,
        )
        assert resp.status_code == 413

    @pytest.mark.anyio
    async def test_extract_requires_auth(self, client: httpx.AsyncClient) -> None:
        content = b"Hello"
        resp = await client.post(
            "/api/ai/files/extract",
            files={"file": ("test.txt", content, "text/plain")},
        )
        assert resp.status_code == 401

    @pytest.mark.anyio
    async def test_extract_handles_binary_error(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        content = bytes(range(256)) * 10
        resp = await client.post(
            "/api/ai/files/extract",
            files={"file": ("data.bin", content, "application/octet-stream")},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["error"] is not None
        assert data["extracted_text"] == ""

    @pytest.mark.anyio
    async def test_extract_csv_file(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        content = b"Name,Age\nAlice,30\nBob,25\n"
        resp = await client.post(
            "/api/ai/files/extract",
            files={"file": ("people.csv", content, "text/csv")},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "Alice" in data["extracted_text"]
        assert data["error"] is None
