"""Tests for optional-authentication dependency and anonymous read access (ADR-123 / SPEC-123-A).

Anonymous GET on public read endpoints returns 200.
Anonymous writes and admin GETs return 401.
Invalid tokens still return 401 (anonymous ≠ invalid credentials).
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


class TestAnonymousReads:
    """Anonymous GET on public read endpoints returns 200."""

    async def test_collections_list_allows_anonymous(
        self, client: httpx.AsyncClient,
    ) -> None:
        resp = await client.get("/api/collections")
        assert resp.status_code == 200

    async def test_sets_list_allows_anonymous(
        self, client: httpx.AsyncClient,
    ) -> None:
        resp = await client.get("/api/sets")
        assert resp.status_code == 200

    async def test_packages_list_allows_anonymous(
        self, client: httpx.AsyncClient,
    ) -> None:
        resp = await client.get("/api/packages")
        assert resp.status_code == 200

    async def test_diagrams_list_allows_anonymous(
        self, client: httpx.AsyncClient,
    ) -> None:
        resp = await client.get("/api/diagrams")
        assert resp.status_code == 200

    async def test_elements_list_allows_anonymous(
        self, client: httpx.AsyncClient,
    ) -> None:
        resp = await client.get("/api/elements")
        assert resp.status_code == 200

    async def test_search_allows_anonymous(
        self, client: httpx.AsyncClient,
    ) -> None:
        resp = await client.get("/api/search?q=anything")
        assert resp.status_code == 200

    async def test_graph_allows_anonymous(
        self, client: httpx.AsyncClient,
    ) -> None:
        resp = await client.get("/api/graph")
        assert resp.status_code == 200


class TestAnonymousWritesBlocked:
    """Anonymous POST/PUT/PATCH/DELETE returns 401."""

    async def test_create_collection_requires_auth(
        self, client: httpx.AsyncClient,
    ) -> None:
        resp = await client.post(
            "/api/collections", json={"name": "x", "description": "x"},
        )
        assert resp.status_code == 401

    async def test_create_set_requires_auth(
        self, client: httpx.AsyncClient,
    ) -> None:
        resp = await client.post("/api/sets", json={"name": "x"})
        assert resp.status_code == 401

    async def test_create_package_requires_auth(
        self, client: httpx.AsyncClient,
    ) -> None:
        resp = await client.post("/api/packages", json={"name": "x"})
        assert resp.status_code == 401


class TestAnonymousAdminBlocked:
    """Anonymous requests to admin routers return 401."""

    async def test_users_list_requires_auth(
        self, client: httpx.AsyncClient,
    ) -> None:
        resp = await client.get("/api/users")
        assert resp.status_code == 401

    async def test_audit_requires_auth(
        self, client: httpx.AsyncClient,
    ) -> None:
        resp = await client.get("/api/audit")
        assert resp.status_code == 401


class TestInvalidTokenRejected:
    """Invalid tokens return 401 — anonymous is the absence of a header, not a bad one."""

    async def test_invalid_bearer_token_returns_401(
        self, client: httpx.AsyncClient,
    ) -> None:
        resp = await client.get(
            "/api/collections",
            headers={"Authorization": "Bearer not-a-real-token"},
        )
        assert resp.status_code == 401

    async def test_malformed_authorization_header_returns_401(
        self, client: httpx.AsyncClient,
    ) -> None:
        resp = await client.get(
            "/api/collections",
            headers={"Authorization": "NotBearer xxx"},
        )
        assert resp.status_code == 401


class TestAuthenticatedStillWorks:
    """Authenticated flows unchanged by optional-auth introduction."""

    async def test_authenticated_get_still_200(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/collections", headers=headers)
        assert resp.status_code == 200

    async def test_authenticated_post_still_201(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/collections",
            json={"name": "Collection", "description": ""},
            headers=headers,
        )
        assert resp.status_code == 201
