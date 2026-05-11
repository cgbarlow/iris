"""ADR-152 / SPEC-152-A: scope-prompt index endpoint for MCP prompts.

Asserts `GET /api/prompts/scope-index` returns one row per Collection
and Set that has a non-null, non-empty `system_prompt`. Collections
come first, then Sets — keeps the ordering predictable for the MCP
prompt picker.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import httpx
import pytest

from app.config import AppConfig, AuthConfig, DatabaseConfig
from app.database import DatabaseManager
from app.main import create_app
from app.startup import initialize_databases

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


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


class TestScopePromptIndex:
    async def test_empty_when_no_scopes_have_prompts(self, client: httpx.AsyncClient) -> None:
        await _auth_headers(client)
        resp = await client.get("/api/prompts/scope-index")
        assert resp.status_code == 200
        assert resp.json() == {"items": []}

    async def test_lists_one_set_with_prompt(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        s = (await client.post(
            "/api/sets", json={"name": "DoView Book"}, headers=headers,
        )).json()
        await client.put(
            f"/api/sets/{s['id']}",
            json={"name": "DoView Book", "mcp_prompt": "Use outcomes theory framing."},
            headers=headers,
        )

        resp = await client.get("/api/prompts/scope-index")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        entry = items[0]
        assert entry["scope_type"] == "set"
        assert entry["scope_id"] == s["id"]
        assert entry["scope_name"] == "DoView Book"
        assert entry["body"] == "Use outcomes theory framing."
        assert entry["name"] == f"set:{s['id']}"

    async def test_lists_collection_before_sets(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        c = (await client.post(
            "/api/collections", json={"name": "NZISM"}, headers=headers,
        )).json()
        await client.put(
            f"/api/collections/{c['id']}",
            json={"name": "NZISM", "mcp_prompt": "Always cite the control number."},
            headers=headers,
        )
        s = (await client.post(
            "/api/sets",
            json={"name": "GCSB Set", "collection_id": c["id"]},
            headers=headers,
        )).json()
        await client.put(
            f"/api/sets/{s['id']}",
            json={
                "name": "GCSB Set",
                "collection_id": c["id"],
                "mcp_prompt": "Strict GCSB terminology.",
            },
            headers=headers,
        )

        resp = await client.get("/api/prompts/scope-index")
        items = resp.json()["items"]
        assert [(i["scope_type"], i["scope_name"]) for i in items] == [
            ("collection", "NZISM"),
            ("set", "GCSB Set"),
        ]
        assert items[0]["name"] == f"collection:{c['id']}"
        assert items[1]["name"] == f"set:{s['id']}"

    async def test_excludes_scopes_with_null_system_prompt(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        await client.post(
            "/api/sets", json={"name": "Unprompted Set"}, headers=headers,
        )

        resp = await client.get("/api/prompts/scope-index")
        assert resp.json()["items"] == []

    async def test_excludes_scopes_with_whitespace_only_system_prompt(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        s = (await client.post(
            "/api/sets", json={"name": "Whitespace Set"}, headers=headers,
        )).json()
        await client.put(
            f"/api/sets/{s['id']}",
            json={"name": "Whitespace Set", "mcp_prompt": "   "},
            headers=headers,
        )

        resp = await client.get("/api/prompts/scope-index")
        assert resp.json()["items"] == []

    async def test_anonymous_can_read_index(self, client: httpx.AsyncClient) -> None:
        """Same posture as list_collections / list_sets — anonymous-readable."""
        headers = await _auth_headers(client)
        s = (await client.post(
            "/api/sets", json={"name": "Public Set"}, headers=headers,
        )).json()
        await client.put(
            f"/api/sets/{s['id']}",
            json={"name": "Public Set", "mcp_prompt": "anyone can see this"},
            headers=headers,
        )

        # No auth header — should still succeed.
        resp = await client.get("/api/prompts/scope-index")
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 1
