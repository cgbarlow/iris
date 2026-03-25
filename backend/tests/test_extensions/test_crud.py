"""Integration tests for extensions registry API routes."""

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
    await client.post(
        "/api/auth/setup",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


class TestListExtensions:
    async def test_empty_list(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/extensions", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == {"items": []}


class TestInstallExtension:
    async def test_install_returns_201(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/extensions/scenia/install",
            json={
                "name": "Scenia",
                "description": "Roadmapping extension",
                "version": "1.0.0",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == "scenia"
        assert data["name"] == "Scenia"
        assert data["description"] == "Roadmapping extension"
        assert data["version"] == "1.0.0"
        assert data["is_enabled"] is True

    async def test_duplicate_install_returns_409(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        await client.post(
            "/api/extensions/scenia/install",
            json={"name": "Scenia", "version": "1.0.0"},
            headers=headers,
        )
        resp = await client.post(
            "/api/extensions/scenia/install",
            json={"name": "Scenia", "version": "1.0.0"},
            headers=headers,
        )
        assert resp.status_code == 409

    async def test_install_appears_in_list(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        await client.post(
            "/api/extensions/scenia/install",
            json={"name": "Scenia", "version": "1.0.0"},
            headers=headers,
        )
        resp = await client.get("/api/extensions", headers=headers)
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["name"] == "Scenia"


class TestGetExtension:
    async def test_get_installed_extension(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        await client.post(
            "/api/extensions/scenia/install",
            json={"name": "Scenia", "version": "1.0.0"},
            headers=headers,
        )
        resp = await client.get("/api/extensions/scenia", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Scenia"

    async def test_get_nonexistent_returns_404(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/extensions/nonexistent", headers=headers)
        assert resp.status_code == 404


class TestUninstallExtension:
    async def test_uninstall_returns_204(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        await client.post(
            "/api/extensions/scenia/install",
            json={"name": "Scenia", "version": "1.0.0"},
            headers=headers,
        )
        resp = await client.post("/api/extensions/scenia/uninstall", headers=headers)
        assert resp.status_code == 204

        # Verify it's gone
        get_resp = await client.get("/api/extensions/scenia", headers=headers)
        assert get_resp.status_code == 404

    async def test_uninstall_nonexistent_returns_404(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.post("/api/extensions/nonexistent/uninstall", headers=headers)
        assert resp.status_code == 404


class TestEnableDisableExtension:
    async def test_disable_extension(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        await client.post(
            "/api/extensions/scenia/install",
            json={"name": "Scenia", "version": "1.0.0"},
            headers=headers,
        )
        resp = await client.post("/api/extensions/scenia/disable", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["is_enabled"] is False

    async def test_enable_extension(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        await client.post(
            "/api/extensions/scenia/install",
            json={"name": "Scenia", "version": "1.0.0"},
            headers=headers,
        )
        # Disable first
        await client.post("/api/extensions/scenia/disable", headers=headers)
        # Then re-enable
        resp = await client.post("/api/extensions/scenia/enable", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["is_enabled"] is True

    async def test_disable_nonexistent_returns_404(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.post("/api/extensions/nonexistent/disable", headers=headers)
        assert resp.status_code == 404

    async def test_enable_nonexistent_returns_404(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.post("/api/extensions/nonexistent/enable", headers=headers)
        assert resp.status_code == 404


class TestExtensionConfig:
    async def test_install_with_config(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/extensions/scenia/install",
            json={
                "name": "Scenia",
                "version": "1.0.0",
                "config": {"theme": "dark", "auto_save": True},
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["config"]["theme"] == "dark"
        assert data["config"]["auto_save"] is True
