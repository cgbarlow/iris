"""Tests for the Text diagram subclass + Markdown notation (issue #26, ADR-137)."""

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
    db_manager = DatabaseManager(app_config.database)
    await initialize_databases(db_manager)
    application.state.db_manager = db_manager
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await db_manager.close()


async def _auth_headers(client: httpx.AsyncClient) -> dict[str, str]:
    await client.post("/api/auth/setup", json={"username": "admin", "password": "AdminPass123!"})
    resp = await client.post("/api/auth/login", json={"username": "admin", "password": "AdminPass123!"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


class TestMarkdownNotationRegistry:
    @pytest.mark.anyio
    async def test_markdown_notation_exists(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/registry/notations", headers=headers)
        assert resp.status_code == 200
        ids = [n["id"] for n in resp.json()]
        assert "markdown" in ids

    @pytest.mark.anyio
    async def test_text_diagram_type_exists(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/registry/diagram-types", headers=headers)
        ids = [t["id"] for t in resp.json()]
        assert "text" in ids

    @pytest.mark.anyio
    async def test_text_default_notation_is_markdown(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.get("/api/registry/diagram-types", headers=headers)
        types = resp.json()
        text = next(t for t in types if t["id"] == "text")
        defaults = [n for n in text["notations"] if n["is_default"]]
        assert len(defaults) == 1
        assert defaults[0]["notation_id"] == "markdown"


class TestTextDiagramCreation:
    @pytest.mark.anyio
    async def test_create_text_diagram(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        resp = await client.post(
            "/api/diagrams",
            json={
                "diagram_type": "text",
                "name": "Architecture Notes",
                "notation": "markdown",
                "data": {"content": "# Architecture Notes\n\nSee [the diagram](iris://diagram/abc123)."},
            },
            headers=headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["diagram_type"] == "text"
        assert body["notation"] == "markdown"
        assert body["data"]["content"].startswith("# Architecture Notes")

    @pytest.mark.anyio
    async def test_text_diagram_round_trips_content(self, client: httpx.AsyncClient) -> None:
        headers = await _auth_headers(client)
        markdown = "# H1\n\n## H2\n\nBody with [iris ref](iris://element/elem-42).\n"
        resp = await client.post(
            "/api/diagrams",
            json={
                "diagram_type": "text",
                "name": "Doc",
                "notation": "markdown",
                "data": {"content": markdown},
            },
            headers=headers,
        )
        diagram_id = resp.json()["id"]
        # Fetch back and verify content is preserved verbatim.
        get = await client.get(f"/api/diagrams/{diagram_id}", headers=headers)
        assert get.status_code == 200
        assert get.json()["data"]["content"] == markdown
