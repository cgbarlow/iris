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

    async def test_entry_kind_discriminator_on_every_entry(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        s = (await client.post("/api/sets", json={"name": "Mixed"}, headers=headers)).json()
        await client.put(
            f"/api/sets/{s['id']}",
            json={"name": "Mixed", "mcp_prompt": "House rules."},
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
        assert len(items) == 2
        kinds = {i["entry_kind"] for i in items}
        assert kinds == {"system_prompt", "named_prompt"}
        # prompt_name set only on named entries
        for entry in items:
            if entry["entry_kind"] == "named_prompt":
                assert entry["prompt_name"] is not None
            else:
                assert entry["prompt_name"] is None

    async def test_system_prompts_appear_before_named_prompts(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        s = (await client.post("/api/sets", json={"name": "Z-set"}, headers=headers)).json()
        # Order matters: named added first, system added second; result
        # must still place system_prompt first in the index.
        await client.post(
            "/api/named-prompts",
            json={
                "scope_type": "set", "scope_id": s["id"], "name": "alpha",
                "description": "A", "body": "B",
            },
            headers=headers,
        )
        await client.put(
            f"/api/sets/{s['id']}",
            json={"name": "Z-set", "mcp_prompt": "house rules"},
            headers=headers,
        )

        items = (await client.get("/api/prompts/scope-index")).json()["items"]
        kinds_in_order = [i["entry_kind"] for i in items]
        assert kinds_in_order == ["system_prompt", "named_prompt"]

    async def test_empty_when_neither_prompts_exist(self, client: httpx.AsyncClient) -> None:
        await _auth_headers(client)
        resp = await client.get("/api/prompts/scope-index")
        assert resp.json() == {"items": []}

    async def test_adr_155_strict_split_system_prompt_alone_does_not_appear(
        self, client: httpx.AsyncClient,
    ) -> None:
        """ADR-155: a Set with ONLY `system_prompt` (no mcp_prompt) must
        NOT appear in the MCP scope-index. system_prompt is Iris-AI-only
        post-v5.10.0. The MCP picker entry only appears when mcp_prompt
        is populated.
        """
        headers = await _auth_headers(client)
        s = (await client.post(
            "/api/sets", json={"name": "Iris-only set"}, headers=headers,
        )).json()
        # Populate system_prompt (auto-apply in Iris AI) but NOT mcp_prompt.
        await client.put(
            f"/api/sets/{s['id']}",
            json={"name": "Iris-only set", "system_prompt": "Iris-only directive."},
            headers=headers,
        )

        items = (await client.get("/api/prompts/scope-index")).json()["items"]
        # Iris-only system_prompt does NOT surface in the MCP picker.
        assert items == []

    async def test_adr_155_strict_split_mcp_prompt_alone_appears(
        self, client: httpx.AsyncClient,
    ) -> None:
        """ADR-155: a Set with ONLY `mcp_prompt` (no system_prompt) MUST
        appear in the MCP scope-index. mcp_prompt is the MCP-only
        channel post-v5.10.0.
        """
        headers = await _auth_headers(client)
        s = (await client.post(
            "/api/sets", json={"name": "MCP-only set"}, headers=headers,
        )).json()
        await client.put(
            f"/api/sets/{s['id']}",
            json={"name": "MCP-only set", "mcp_prompt": "MCP-only directive."},
            headers=headers,
        )

        items = (await client.get("/api/prompts/scope-index")).json()["items"]
        assert len(items) == 1
        assert items[0]["body"] == "MCP-only directive."
        assert items[0]["name"] == f"set:{s['id']}"

    async def test_adr_155_strict_split_both_populated(
        self, client: httpx.AsyncClient,
    ) -> None:
        """ADR-155: when both columns are populated, MCP picker shows
        mcp_prompt content (system_prompt continues to auto-apply in
        Iris AI but is not visible here)."""
        headers = await _auth_headers(client)
        s = (await client.post(
            "/api/sets", json={"name": "Both set"}, headers=headers,
        )).json()
        await client.put(
            f"/api/sets/{s['id']}",
            json={
                "name": "Both set",
                "system_prompt": "Iris-AI directive.",
                "mcp_prompt": "MCP directive.",
            },
            headers=headers,
        )

        items = (await client.get("/api/prompts/scope-index")).json()["items"]
        assert len(items) == 1
        # MCP picker body is mcp_prompt, NOT system_prompt.
        assert items[0]["body"] == "MCP directive."
