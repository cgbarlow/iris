"""Scope-prompt index endpoint (ADR-152; ADR-154; ADR-156).

v5.11.0 / ADR-156: scope-level prompts no longer appear in the MCP
picker. The endpoint returns named prompts (ADR-154) only. Scope
content (`mcp_system_context`) is passed through as data on
`get_set` / `get_collection` MCP tool responses instead.

`system_prompt` continues to auto-apply in Iris AI (ADR-150) and is
stripped from MCP tool responses (ADR-151) — unchanged, and not the
concern of this endpoint.
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


class TestScopePromptIndex:
    async def test_empty_when_no_named_prompts(self, client: httpx.AsyncClient) -> None:
        await _auth_headers(client)
        resp = await client.get("/api/prompts/scope-index")
        assert resp.status_code == 200
        assert resp.json() == {"items": []}

    async def test_scope_mcp_system_context_does_not_appear_in_picker(
        self, client: httpx.AsyncClient,
    ) -> None:
        """ADR-156: scope-level `mcp_system_context` is data passthrough,
        NOT a picker entry. The picker shows only named prompts."""
        headers = await _auth_headers(client)
        s = (await client.post(
            "/api/sets", json={"name": "DoView"}, headers=headers,
        )).json()
        await client.put(
            f"/api/sets/{s['id']}",
            json={"name": "DoView", "mcp_system_context": "Use outcomes theory."},
            headers=headers,
        )

        resp = await client.get("/api/prompts/scope-index")
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    async def test_picker_shows_named_prompts_only(
        self, client: httpx.AsyncClient,
    ) -> None:
        headers = await _auth_headers(client)
        s = (await client.post(
            "/api/sets", json={"name": "DoView"}, headers=headers,
        )).json()
        await client.put(
            f"/api/sets/{s['id']}",
            json={"name": "DoView", "mcp_system_context": "Scope passthrough."},
            headers=headers,
        )
        await client.post(
            "/api/named-prompts",
            json={
                "scope_type": "set",
                "scope_id": s["id"],
                "name": "outcomes-theory",
                "description": "Outcomes theory framing.",
                "body": "Apply outcomes theory.",
            },
            headers=headers,
        )

        items = (await client.get("/api/prompts/scope-index")).json()["items"]
        assert len(items) == 1
        assert items[0]["entry_kind"] == "named_prompt"
        assert items[0]["name"] == f"set:{s['id']}:outcomes-theory"

    async def test_anonymous_can_read_index(self, client: httpx.AsyncClient) -> None:
        """Same posture as list_collections / list_sets — anonymous-readable."""
        headers = await _auth_headers(client)
        s = (await client.post(
            "/api/sets", json={"name": "Public Set"}, headers=headers,
        )).json()
        await client.post(
            "/api/named-prompts",
            json={
                "scope_type": "set",
                "scope_id": s["id"],
                "name": "anyone-can-see-this",
                "description": "Public",
                "body": "Body.",
            },
            headers=headers,
        )

        resp = await client.get("/api/prompts/scope-index")
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 1
