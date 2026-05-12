"""v5.17.0 (ADR-162, SPEC-162-A): backend endpoints
`/api/ai/response-prompts/types` and
`/api/ai/response-prompts/composed` accept a `?purpose=` query param
to expose creation_format prompts in addition to response_format,
giving MCP clients a way to fetch the same drafting cascade Iris AI
uses when generating diagrams.
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


class TestTypesEndpoint:
    async def test_default_returns_response_format_pairs(
        self, client: httpx.AsyncClient,
    ) -> None:
        # Default ?purpose= is response_format; the v5.12.0 seed has
        # (markdown, doview_analysis) at least.
        resp = await client.get("/api/ai/response-prompts/types")
        assert resp.status_code == 200
        pairs = resp.json()
        assert any(
            p["notation"] == "markdown" and p["diagram_type"] == "doview_analysis"
            for p in pairs
        )

    async def test_explicit_response_format_same_as_default(
        self, client: httpx.AsyncClient,
    ) -> None:
        default = await client.get("/api/ai/response-prompts/types")
        explicit = await client.get(
            "/api/ai/response-prompts/types?purpose=response_format",
        )
        assert default.json() == explicit.json()

    async def test_creation_format_returns_creation_pairs(
        self, client: httpx.AsyncClient,
    ) -> None:
        resp = await client.get(
            "/api/ai/response-prompts/types?purpose=creation_format",
        )
        assert resp.status_code == 200
        pairs = resp.json()
        # The v5.8.x seed has (doview, outcomes_map) creation_format rows.
        assert any(
            p["notation"] == "doview" and p["diagram_type"] == "outcomes_map"
            for p in pairs
        ), f"expected (doview, outcomes_map) in {pairs}"

    async def test_invalid_purpose_is_422(
        self, client: httpx.AsyncClient,
    ) -> None:
        resp = await client.get(
            "/api/ai/response-prompts/types?purpose=garbage",
        )
        assert resp.status_code == 422


class TestComposedEndpoint:
    async def test_default_returns_response_format_body(
        self, client: httpx.AsyncClient,
    ) -> None:
        resp = await client.get(
            "/api/ai/response-prompts/composed"
            "?notation=markdown&diagram_type=doview_analysis",
        )
        assert resp.status_code == 200
        # Response format body for doview_analysis includes the
        # required opening sentence.
        assert "I have prepared a summary response" in resp.json()["body"]

    async def test_creation_format_returns_creation_body(
        self, client: httpx.AsyncClient,
    ) -> None:
        resp = await client.get(
            "/api/ai/response-prompts/composed"
            "?notation=doview&diagram_type=outcomes_map"
            "&purpose=creation_format",
        )
        assert resp.status_code == 200
        body = resp.json()["body"]
        # The doview creation cascade includes the Stage 0 setup-questions
        # conversation (Q1..Q6 — "Describe in a couple of lines or less
        # what you want a DoView of.") from the seeded creation_format.
        assert "Stage 0" in body
        assert "Describe in a couple of lines" in body
        # And the outcomes_map layout rules (final_outcome type).
        assert "final_outcome" in body

    async def test_creation_format_HTTP_path_drops_ui_selection_preamble(
        self, client: httpx.AsyncClient,
    ) -> None:
        """ADR-162: the HTTP-exposed creation cascade must NOT include
        the 'User selection already confirmed in UI' suppression
        preamble (which is only correct when Iris AI is called server-
        side with attached document context). MCP clients need the raw
        conversational guidance."""
        resp = await client.get(
            "/api/ai/response-prompts/composed"
            "?notation=doview&diagram_type=outcomes_map"
            "&purpose=creation_format",
        )
        body = resp.json()["body"]
        assert "User selection (already confirmed in UI)" not in body
        assert "Do NOT ask the user to re-confirm the notation" not in body

    async def test_invalid_purpose_is_422(
        self, client: httpx.AsyncClient,
    ) -> None:
        resp = await client.get(
            "/api/ai/response-prompts/composed"
            "?notation=doview&purpose=garbage",
        )
        assert resp.status_code == 422
