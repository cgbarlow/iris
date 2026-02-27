"""Tests for sliding window rate limiting middleware."""

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
        rate_limit_login=3,
        rate_limit_refresh=5,
        rate_limit_general=10,
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


class TestRateLimitLogin:
    """Verify login endpoint rate limiting."""

    async def test_allows_requests_under_limit(
        self, client: httpx.AsyncClient
    ) -> None:
        for _ in range(3):
            resp = await client.post(
                "/api/auth/login",
                json={"username": "x", "password": "y"},
            )
            assert resp.status_code != 429

    async def test_blocks_after_limit_exceeded(
        self, client: httpx.AsyncClient
    ) -> None:
        for _ in range(3):
            await client.post(
                "/api/auth/login",
                json={"username": "x", "password": "y"},
            )
        resp = await client.post(
            "/api/auth/login",
            json={"username": "x", "password": "y"},
        )
        assert resp.status_code == 429

    async def test_returns_retry_after_header(
        self, client: httpx.AsyncClient
    ) -> None:
        for _ in range(3):
            await client.post(
                "/api/auth/login",
                json={"username": "x", "password": "y"},
            )
        resp = await client.post(
            "/api/auth/login",
            json={"username": "x", "password": "y"},
        )
        assert "retry-after" in resp.headers


class TestRateLimitRefresh:
    """Verify refresh endpoint rate limiting."""

    async def test_blocks_after_limit_exceeded(
        self, client: httpx.AsyncClient
    ) -> None:
        for _ in range(5):
            await client.post(
                "/api/auth/refresh",
                json={"refresh_token": "fake"},
            )
        resp = await client.post(
            "/api/auth/refresh",
            json={"refresh_token": "fake"},
        )
        assert resp.status_code == 429


class TestRateLimitGeneral:
    """Verify general endpoint rate limiting."""

    async def test_health_endpoint_rate_limited(
        self, client: httpx.AsyncClient
    ) -> None:
        for _ in range(10):
            await client.get("/health")
        resp = await client.get("/health")
        assert resp.status_code == 429


class TestRateLimitIsolation:
    """Verify rate limits are per-endpoint-category."""

    async def test_login_limit_does_not_affect_health(
        self, client: httpx.AsyncClient
    ) -> None:
        # Exhaust login limit
        for _ in range(3):
            await client.post(
                "/api/auth/login",
                json={"username": "x", "password": "y"},
            )
        # Health should still work
        resp = await client.get("/health")
        assert resp.status_code == 200
