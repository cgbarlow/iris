"""Tests for the FastAPI application factory."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest

from app.config import AppConfig, AuthConfig, DatabaseConfig
from app.main import create_app

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def app_config(tmp_path: Path) -> AppConfig:
    """Create an app config with temp database paths."""
    return AppConfig(
        debug=True,
        cors_origins=["http://localhost:5173"],
        database=DatabaseConfig(data_dir=str(tmp_path / "data")),
        auth=AuthConfig(
            jwt_secret="test-key-at-least-32-bytes-long-for-testing",
        ),
    )


@pytest.fixture
def app(app_config: AppConfig) -> object:
    """Create a FastAPI app for testing."""
    return create_app(app_config)


class TestAppFactory:
    """Verify FastAPI application factory configuration."""

    def test_creates_app(self, app_config: AppConfig) -> None:
        application = create_app(app_config)
        assert application.title == "Iris"

    def test_docs_enabled_in_debug(self, app_config: AppConfig) -> None:
        application = create_app(app_config)
        assert application.docs_url == "/docs"

    def test_docs_disabled_in_production(self, tmp_path: Path) -> None:
        config = AppConfig(
            debug=False,
            database=DatabaseConfig(data_dir=str(tmp_path / "data")),
            auth=AuthConfig(
                jwt_secret="test-key-at-least-32-bytes-long-for-testing",
            ),
        )
        application = create_app(config)
        assert application.docs_url is None


class TestHealthEndpoint:
    """Verify health check endpoint."""

    async def test_health_check(self, app_config: AppConfig) -> None:
        application = create_app(app_config)
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestSecurityHeaders:
    """Verify security headers are set on all responses."""

    async def test_x_content_type_options(
        self, app_config: AppConfig
    ) -> None:
        application = create_app(app_config)
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.get("/health")
        assert response.headers["x-content-type-options"] == "nosniff"

    async def test_x_frame_options(self, app_config: AppConfig) -> None:
        application = create_app(app_config)
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.get("/health")
        assert response.headers["x-frame-options"] == "DENY"

    async def test_referrer_policy(self, app_config: AppConfig) -> None:
        application = create_app(app_config)
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.get("/health")
        assert (
            response.headers["referrer-policy"]
            == "strict-origin-when-cross-origin"
        )

    async def test_strict_transport_security(
        self, app_config: AppConfig
    ) -> None:
        application = create_app(app_config)
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.get("/health")
        assert "max-age=31536000" in response.headers.get(
            "strict-transport-security", ""
        )
