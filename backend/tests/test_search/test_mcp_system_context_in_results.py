"""ADR-159 (v5.14.0): search results for Set / Collection hits include
their `mcp_system_context` field so an MCP client model sees the
scope's orient guidance immediately on a search match — no follow-up
`get_set` / `get_collection` call needed for the context to land.
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


async def _admin_headers(client: httpx.AsyncClient) -> dict[str, str]:
    await client.post(
        "/api/auth/setup",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "AdminPass123!"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


class TestSearchHitsCarryMcpSystemContext:
    async def test_set_hit_includes_mcp_system_context_when_populated(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        s = (await client.post(
            "/api/sets", json={"name": "Outcomes Theory Book"}, headers=headers,
        )).json()
        await client.put(
            f"/api/sets/{s['id']}",
            json={
                "name": "Outcomes Theory Book",
                "mcp_system_context": "Orient first — offer the four-option menu.",
            },
            headers=headers,
        )

        resp = await client.get("/api/search?q=outcomes")
        assert resp.status_code == 200
        results = resp.json()["results"]
        set_hit = next((r for r in results if r["result_type"] == "set"), None)
        assert set_hit is not None, "Set should appear in search results"
        assert set_hit["mcp_system_context"] == "Orient first — offer the four-option menu."

    async def test_set_hit_mcp_system_context_is_null_when_unpopulated(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        await client.post(
            "/api/sets", json={"name": "Unconfigured set"}, headers=headers,
        )

        resp = await client.get("/api/search?q=unconfigured")
        results = resp.json()["results"]
        set_hit = next((r for r in results if r["result_type"] == "set"), None)
        assert set_hit is not None
        assert set_hit["mcp_system_context"] is None

    async def test_collection_hit_includes_mcp_system_context(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _admin_headers(client)
        c = (await client.post(
            "/api/collections", json={"name": "DoView Strategy Models"}, headers=headers,
        )).json()
        await client.put(
            f"/api/collections/{c['id']}",
            json={
                "name": "DoView Strategy Models",
                "mcp_system_context": "Use this collection to bootstrap DoView modelling exercises.",
            },
            headers=headers,
        )

        resp = await client.get("/api/search?q=doview")
        results = resp.json()["results"]
        coll_hit = next((r for r in results if r["result_type"] == "collection"), None)
        assert coll_hit is not None
        assert coll_hit["mcp_system_context"] == "Use this collection to bootstrap DoView modelling exercises."

    async def test_non_scope_hits_do_not_have_mcp_system_context(
        self, client: httpx.AsyncClient,
    ) -> None:
        """Element / diagram / package hits don't carry mcp_system_context
        — the field is only meaningful on Set / Collection scopes."""
        headers = await _admin_headers(client)
        s = (await client.post(
            "/api/sets", json={"name": "carrier"}, headers=headers,
        )).json()
        await client.post(
            "/api/diagrams",
            json={
                "diagram_type": "text",
                "name": "Findable diagram",
                "notation": "markdown",
                "data": {"content": "# A findable diagram"},
                "set_id": s["id"],
            },
            headers=headers,
        )

        resp = await client.get("/api/search?q=findable")
        results = resp.json()["results"]
        diagram_hit = next((r for r in results if r["result_type"] == "diagram"), None)
        if diagram_hit is not None:
            # Field may be absent (Pydantic excludes unset) or present-and-None.
            assert diagram_hit.get("mcp_system_context") is None
