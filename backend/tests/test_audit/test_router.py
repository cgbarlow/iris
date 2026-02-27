"""Tests for audit log read API per ADR-009 / SPEC-009-A."""

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
async def client_and_db(
    app_config: AppConfig,
) -> AsyncIterator[tuple[httpx.AsyncClient, DatabaseManager]]:
    application = create_app(app_config)
    db_manager = DatabaseManager(app_config.database)
    await initialize_databases(db_manager)
    application.state.db_manager = db_manager
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test"
    ) as c:
        yield c, db_manager
    await db_manager.close()


async def _setup_and_login(
    client: httpx.AsyncClient,
) -> dict[str, str]:
    """Create admin via setup, login, return tokens."""
    await client.post(
        "/api/auth/setup",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    return resp.json()


async def _create_viewer(
    client: httpx.AsyncClient,
    admin_token: str,
) -> dict[str, str]:
    """Create a viewer user and return their tokens."""
    await client.post(
        "/api/users",
        json={"username": "viewer", "password": "ViewerPass123!", "role": "viewer"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "viewer", "password": "ViewerPass123!"},
    )
    return resp.json()


class TestAuditListEndpoint:
    """Tests for GET /api/audit."""

    async def test_returns_paginated_entries(
        self, client_and_db: tuple[httpx.AsyncClient, DatabaseManager]
    ) -> None:
        client, _ = client_and_db
        tokens = await _setup_and_login(client)
        resp = await client.get(
            "/api/audit",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert data["total"] > 0
        assert len(data["items"]) > 0

    async def test_action_filter(
        self, client_and_db: tuple[httpx.AsyncClient, DatabaseManager]
    ) -> None:
        client, _ = client_and_db
        tokens = await _setup_and_login(client)
        resp = await client.get(
            "/api/audit?action=setup",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert "setup" in item["action"].lower()

    async def test_username_filter(
        self, client_and_db: tuple[httpx.AsyncClient, DatabaseManager]
    ) -> None:
        client, _ = client_and_db
        tokens = await _setup_and_login(client)
        resp = await client.get(
            "/api/audit?username=admin",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["username"] == "admin"

    async def test_pagination(
        self, client_and_db: tuple[httpx.AsyncClient, DatabaseManager]
    ) -> None:
        client, _ = client_and_db
        tokens = await _setup_and_login(client)
        resp = await client.get(
            "/api/audit?page=1&page_size=1",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["page_size"] == 1
        assert len(data["items"]) <= 1

    async def test_non_admin_gets_403(
        self, client_and_db: tuple[httpx.AsyncClient, DatabaseManager]
    ) -> None:
        client, _ = client_and_db
        admin_tokens = await _setup_and_login(client)
        viewer_tokens = await _create_viewer(client, admin_tokens["access_token"])
        resp = await client.get(
            "/api/audit",
            headers={"Authorization": f"Bearer {viewer_tokens['access_token']}"},
        )
        assert resp.status_code == 403


class TestAuditVerifyEndpoint:
    """Tests for GET /api/audit/verify."""

    async def test_returns_chain_status(
        self, client_and_db: tuple[httpx.AsyncClient, DatabaseManager]
    ) -> None:
        client, _ = client_and_db
        tokens = await _setup_and_login(client)
        resp = await client.get(
            "/api/audit/verify",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert data["entries_checked"] > 0
        assert "verified_at" in data

    async def test_non_admin_gets_403(
        self, client_and_db: tuple[httpx.AsyncClient, DatabaseManager]
    ) -> None:
        client, _ = client_and_db
        admin_tokens = await _setup_and_login(client)
        viewer_tokens = await _create_viewer(client, admin_tokens["access_token"])
        resp = await client.get(
            "/api/audit/verify",
            headers={"Authorization": f"Bearer {viewer_tokens['access_token']}"},
        )
        assert resp.status_code == 403
