"""ADR-129: public OpenAPI docs must be accessible in every environment."""

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


def _config(tmp_path: Path, debug: bool) -> AppConfig:
    return AppConfig(
        debug=debug,
        cors_origins=["http://localhost:5173"],
        database=DatabaseConfig(data_dir=str(tmp_path / "data")),
        auth=AuthConfig(
            jwt_secret="test-secret-key-that-is-at-least-32-bytes-long-for-hs256",
            argon2_time_cost=1,
            argon2_memory_cost=8192,
            argon2_parallelism=1,
        ),
    )


@pytest.fixture(params=[True, False], ids=["debug", "prod"])
async def client(
    request: pytest.FixtureRequest, tmp_path: Path,
) -> AsyncIterator[httpx.AsyncClient]:
    cfg = _config(tmp_path, debug=request.param)
    application = create_app(cfg)
    db_manager = DatabaseManager(cfg)
    await initialize_databases(db_manager)
    application.state.db_manager = db_manager
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test",
    ) as c:
        yield c
    await db_manager.close()


class TestPublicOpenAPI:
    async def test_docs_served_at_api_docs(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/api/docs")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    async def test_openapi_json_accessible(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/api/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        assert schema["info"]["title"] == "Iris API"
        # Sanity: the schema includes endpoints we depend on downstream.
        assert "/api/search" in schema["paths"]
        assert "/api/export/diagrams/{diagram_id}" in schema["paths"]
        assert "/api/users/me/tokens" in schema["paths"]

    async def test_redoc_served(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/api/redoc")
        assert resp.status_code == 200

    async def test_legacy_root_docs_not_served(self, client: httpx.AsyncClient) -> None:
        # ADR-129 moved docs to /api/docs; the old root path should 404.
        resp = await client.get("/docs")
        assert resp.status_code == 404
