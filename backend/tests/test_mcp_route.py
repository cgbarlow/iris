"""Smoke test for the /mcp Streamable HTTP route (ADR-133 / SPEC-133-A).

Verifies the route is mounted on the FastAPI app and excluded from the
public OpenAPI schema. Skipped if iris-mcp isn't installed alongside
the backend.

A full POST /mcp/ initialize roundtrip works end-to-end against a real
uvicorn process — see `scripts/mcp_smoke.py`. The roundtrip can't be
exercised under pytest-asyncio because the StreamableHTTP session
manager's anyio task group requires a long-lived owner outside the
per-test event loop.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

iris_mcp = pytest.importorskip("iris_mcp", reason="iris-mcp not installed")


@pytest.fixture
def app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    # ADR-134: embedded /mcp mount is opt-in. Tests assert it works
    # when explicitly enabled; production defaults to off.
    monkeypatch.setenv("IRIS_EMBEDDED_MCP", "1")

    from app.config import AppConfig, AuthConfig, DatabaseConfig
    from app.main import create_app

    cfg = AppConfig(
        debug=True,
        cors_origins=["http://test"],
        database=DatabaseConfig(data_dir=str(tmp_path / "data")),
        auth=AuthConfig(
            jwt_secret="test-secret-key-that-is-at-least-32-bytes-long-for-hs256",
            argon2_time_cost=1,
            argon2_memory_cost=8192,
            argon2_parallelism=1,
        ),
    )
    return create_app(cfg)


@pytest.fixture
async def client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[httpx.AsyncClient]:
    monkeypatch.setenv("IRIS_EMBEDDED_MCP", "1")

    from app.config import AppConfig, AuthConfig, DatabaseConfig
    from app.database import DatabaseManager
    from app.main import create_app
    from app.startup import initialize_databases

    cfg = AppConfig(
        debug=True,
        cors_origins=["http://test"],
        database=DatabaseConfig(data_dir=str(tmp_path / "data")),
        auth=AuthConfig(
            jwt_secret="test-secret-key-that-is-at-least-32-bytes-long-for-hs256",
            argon2_time_cost=1,
            argon2_memory_cost=8192,
            argon2_parallelism=1,
        ),
    )
    app_ = create_app(cfg)
    dbm = DatabaseManager(cfg)
    await initialize_databases(dbm)
    app_.state.db_manager = dbm
    transport = httpx.ASGITransport(app=app_)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test", timeout=5,
    ) as c:
        yield c
    await dbm.close()


class TestMcpRoute:
    def test_mount_present(self, app: FastAPI) -> None:
        """The /mcp Mount appears in the FastAPI route table."""
        mcp_mounts = [
            r for r in app.routes
            if type(r).__name__ == "Mount" and getattr(r, "path", None) == "/mcp"
        ]
        assert len(mcp_mounts) == 1, (
            f"expected exactly one /mcp Mount, got {len(mcp_mounts)}"
        )

    def test_session_manager_built(self, app: FastAPI) -> None:
        """attach_mcp stashed the session_manager.run() context for lifespan."""
        assert getattr(app.state, "mcp_session_run", None) is not None

    @pytest.mark.asyncio
    async def test_mount_excluded_from_openapi(
        self, client: httpx.AsyncClient,
    ) -> None:
        """The MCP route is intentionally not in the public OpenAPI schema."""
        resp = await client.get("/api/openapi.json")
        assert resp.status_code == 200
        paths = resp.json().get("paths", {})
        assert not any(p.startswith("/mcp") for p in paths), (
            "MCP route leaked into OpenAPI schema"
        )
