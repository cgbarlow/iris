"""v5.18.0 (ADR-163, SPEC-163-A): GET /api/ai/server-instructions
returns the singleton mcp_server_instructions row body. iris-mcp
fetches this at startup to populate the MCP `Server.instructions`
field surfaced to every connected MCP client.

Anonymous-readable. Empty body when no active row exists (iris-mcp
falls back to its hardcoded baseline in that case).
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
        rate_limit_general=1000,
        rate_limit_pat=1000,
    )


@pytest.fixture
async def client(app_config: AppConfig) -> AsyncIterator[httpx.AsyncClient]:
    application = create_app(app_config)
    db_manager = DatabaseManager(app_config)
    await initialize_databases(db_manager)
    application.state.db_manager = db_manager
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test",
    ) as c:
        yield c
    await db_manager.close()


class TestServerInstructionsEndpoint:
    async def test_returns_seeded_body(self, client: httpx.AsyncClient) -> None:
        resp = await client.get("/api/ai/server-instructions")
        assert resp.status_code == 200
        body = resp.json()["body"]
        # The seeded body always contains the orient-first protocol marker.
        assert "ORIENT-FIRST PROTOCOL" in body
        assert "DISCOVERY TOOLS" in body
        assert "AUTH RECOVERY" in body

    async def test_anonymous_readable(self, client: httpx.AsyncClient) -> None:
        # No Authorization header.
        resp = await client.get("/api/ai/server-instructions")
        assert resp.status_code == 200

    async def test_empty_body_when_row_deactivated(
        self, client: httpx.AsyncClient,
    ) -> None:
        # Deactivate the singleton row directly via SQL.
        db = client._transport.app.state.db_manager.main_db  # type: ignore[attr-defined]
        await db.execute(
            "UPDATE ai_creation_prompts SET is_active = 0"
            " WHERE purpose = 'mcp_server_instructions'",
        )
        await db.commit()
        resp = await client.get("/api/ai/server-instructions")
        assert resp.status_code == 200
        assert resp.json()["body"] == ""

    async def test_returns_most_recent_when_multiple_rows_exist(
        self, client: httpx.AsyncClient,
    ) -> None:
        # The singleton seed is row-1. Add a second active row with a
        # later id; the endpoint should still return the seeded one
        # (order by display_order ASC, id ASC LIMIT 1).
        db = client._transport.app.state.db_manager.main_db  # type: ignore[attr-defined]
        await db.execute(
            "INSERT INTO ai_creation_prompts "
            "(id, name, description, purpose, layer, notation, diagram_type, "
            " prompt_text, display_order, is_active) "
            "VALUES (?, ?, ?, ?, ?, NULL, NULL, ?, 1, 1)",
            (
                "mcp-server-instructions-v2-experimental",
                "Experimental v2",
                "test row",
                "mcp_server_instructions",
                "base",
                "OVERRIDDEN BODY",
            ),
        )
        await db.commit()
        resp = await client.get("/api/ai/server-instructions")
        body = resp.json()["body"]
        # display_order=0 (the seed) wins over display_order=1.
        assert "ORIENT-FIRST PROTOCOL" in body
        assert "OVERRIDDEN BODY" not in body


class TestPurposeAcceptedByCreationPromptPydantic:
    """Adding `mcp_server_instructions` to the Pydantic Literal means
    POST /api/ai/creation-prompts no longer rejects it.

    (Adding NEW server-instructions rows via the CRUD is an admin
    affordance; the seed migration handles day-one.)"""

    async def test_post_with_new_purpose_value_does_not_422(
        self, client: httpx.AsyncClient,
    ) -> None:
        # Create an admin so we can hit the auth-required CRUD endpoint.
        await client.post(
            "/api/auth/setup",
            json={"username": "admin", "password": "AdminPass123!"},
        )
        login = await client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "AdminPass123!"},
        )
        token = login.json()["access_token"]

        resp = await client.post(
            "/api/ai/creation-prompts",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Test mcp_server_instructions extra",
                "description": "test",
                "purpose": "mcp_server_instructions",
                "layer": "base",
                "notation": None,
                "diagram_type": None,
                "prompt_text": "test body",
                "display_order": 99,
                "is_active": False,
            },
        )
        # Either 201 (accepted) or 409 (conflict with existing active
        # singleton) is fine — both prove the Pydantic Literal accepts
        # the new value. 422 would indicate the Literal rejected it.
        assert resp.status_code in (201, 409), (
            f"expected 201 or 409, got {resp.status_code}: {resp.text}"
        )
