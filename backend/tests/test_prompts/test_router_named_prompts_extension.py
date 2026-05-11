"""ADR-154 / SPEC-154-A: scope-index extension for named prompts.

`GET /api/prompts/scope-index` now returns BOTH system-prompt entries
(unchanged shape from ADR-152) AND named-prompt entries with the new
`entry_kind` discriminator and optional `prompt_name`. Ordering:
system prompts first, then named prompts.
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
        "/api/auth/setup", json={"username": "admin", "password": "AdminPass123!"},
    )
    resp = await client.post(
        "/api/auth/login", json={"username": "admin", "password": "AdminPass123!"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


class TestScopeIndexExtension:
    async def test_includes_named_prompt_entries(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        s = (await client.post("/api/sets", json={"name": "DoView"}, headers=headers)).json()

        # No system_prompt set — only the named prompt should appear.
        await client.post(
            "/api/named-prompts",
            json={
                "scope_type": "set",
                "scope_id": s["id"],
                "name": "outcomes-theory",
                "description": "Outcomes theory framing.",
                "body": "Apply outcomes theory rules.",
            },
            headers=headers,
        )

        resp = await client.get("/api/prompts/scope-index")
        assert resp.status_code == 200
        items = resp.json()["items"]
        named = [i for i in items if i["entry_kind"] == "named_prompt"]
        assert len(named) == 1
        entry = named[0]
        assert entry["name"] == f"set:{s['id']}:outcomes-theory"
        assert entry["scope_type"] == "set"
        assert entry["scope_id"] == s["id"]
        assert entry["scope_name"] == "DoView"
        assert entry["prompt_name"] == "outcomes-theory"
        assert entry["body"] == "Apply outcomes theory rules."

    async def test_entry_kind_is_named_prompt_only(self, client: httpx.AsyncClient) -> None:
        """ADR-156: every entry in the scope-index is now a named prompt.
        Scope-level mcp_system_context never appears here — it flows
        through MCP tool responses (get_set / get_collection) as data."""
        headers = await _auth_headers(client)
        s = (await client.post("/api/sets", json={"name": "Mixed"}, headers=headers)).json()
        # Even with scope content populated, no scope entry shows up.
        await client.put(
            f"/api/sets/{s['id']}",
            json={
                "name": "Mixed",
                "system_prompt": "Iris-AI directive.",
                "mcp_system_context": "Scope passthrough.",
            },
            headers=headers,
        )
        await client.post(
            "/api/named-prompts",
            json={
                "scope_type": "set",
                "scope_id": s["id"],
                "name": "extra",
                "description": "An extra directive.",
                "body": "Do the extra thing.",
            },
            headers=headers,
        )

        items = (await client.get("/api/prompts/scope-index")).json()["items"]
        assert len(items) == 1
        assert items[0]["entry_kind"] == "named_prompt"
        assert items[0]["prompt_name"] == "extra"

    async def test_empty_when_no_named_prompts_exist(self, client: httpx.AsyncClient) -> None:
        await _auth_headers(client)
        resp = await client.get("/api/prompts/scope-index")
        assert resp.json() == {"items": []}

    async def test_adr_156_scope_content_is_data_passthrough_not_picker(
        self, client: httpx.AsyncClient,
    ) -> None:
        """ADR-156: `mcp_system_context` content is passed through as
        data on `get_set` / `get_collection` MCP tool responses, NOT
        surfaced in the scope-prompt index. The index is named-prompts
        only."""
        headers = await _auth_headers(client)
        s = (await client.post(
            "/api/sets", json={"name": "Passthrough set"}, headers=headers,
        )).json()
        await client.put(
            f"/api/sets/{s['id']}",
            json={
                "name": "Passthrough set",
                "mcp_system_context": "Initial context for MCP browsers.",
            },
            headers=headers,
        )

        # Not in the scope-prompt index.
        items = (await client.get("/api/prompts/scope-index")).json()["items"]
        assert items == []

        # IS on the Set response (which the MCP get_set tool returns).
        set_resp = (await client.get(f"/api/sets/{s['id']}")).json()
        assert set_resp["mcp_system_context"] == "Initial context for MCP browsers."

    async def test_adr_156_system_prompt_stripped_from_set_response_via_mcp(
        self, client: httpx.AsyncClient,
    ) -> None:
        """ADR-151 (still in force): system_prompt is server-side
        composition only and is stripped from MCP tool responses. This
        endpoint is the FastAPI route directly (no MCP boundary), so
        system_prompt IS visible here. The MCP-boundary strip happens
        in `iris_mcp/links.py:_strip_sensitive_keys`."""
        headers = await _auth_headers(client)
        s = (await client.post(
            "/api/sets", json={"name": "Iris-AI set"}, headers=headers,
        )).json()
        await client.put(
            f"/api/sets/{s['id']}",
            json={"name": "Iris-AI set", "system_prompt": "Iris-AI directive."},
            headers=headers,
        )

        set_resp = (await client.get(f"/api/sets/{s['id']}")).json()
        # Backend FastAPI route includes system_prompt — the strip
        # happens at the MCP layer (links.py) not here.
        assert set_resp["system_prompt"] == "Iris-AI directive."
