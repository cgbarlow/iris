"""Tests for Note/Boundary import label derivation (ADR-069)."""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

import httpx
import pytest

from app.import_sparx.service import derive_note_label, import_sparx_file
from app.main import create_app
from app.startup import initialize_databases

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from pathlib import Path

from app.config import AppConfig, AuthConfig, DatabaseConfig
from app.database import DatabaseManager

SAMPLE_QEA = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..", "..", "..", "docs", "reference", "SparxEA", "AIXM_5.1.1_EA16.qea",
    )
)


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
    tokens = resp.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


# ---------- derive_note_label Unit Tests ----------


class TestDeriveNoteLabel:
    """Test the derive_note_label utility function."""

    def test_strips_html_tags(self) -> None:
        html = "<p>This is a <b>note</b> about something</p>"
        result = derive_note_label(html, "fallback")
        assert result == "This is a note about something"

    def test_takes_first_line(self) -> None:
        html = "<p>First line</p><p>Second line</p>"
        result = derive_note_label(html, "fallback")
        assert result == "First line"

    def test_truncates_to_60_chars(self) -> None:
        html = "A" * 100
        result = derive_note_label(html, "fallback")
        assert len(result) == 63  # 60 + "..."
        assert result.endswith("...")

    def test_returns_fallback_for_none(self) -> None:
        result = derive_note_label(None, "fallback")
        assert result == "fallback"

    def test_returns_fallback_for_empty_string(self) -> None:
        result = derive_note_label("", "fallback")
        assert result == "fallback"

    def test_returns_fallback_for_whitespace_only_html(self) -> None:
        result = derive_note_label("<p>   </p>", "fallback")
        assert result == "fallback"

    def test_handles_nested_html(self) -> None:
        html = "<div><span class='x'>Nested <em>content</em></span></div>"
        result = derive_note_label(html, "fallback")
        assert result == "Nested content"

    def test_handles_br_as_line_break(self) -> None:
        html = "First line<br/>Second line"
        result = derive_note_label(html, "fallback")
        assert result == "First line"


# ---------- Import Integration Tests ----------


class TestNoteImportLabels:
    """Verify Note elements get content-derived names after import."""

    async def test_note_element_gets_content_derived_name(
        self, client: httpx.AsyncClient, app_config: AppConfig
    ) -> None:
        headers = await _auth_headers(client)
        db_manager = client._transport.app.state.db_manager  # type: ignore[union-attr]
        db = db_manager.main_db
        cursor = await db.execute("SELECT id FROM users WHERE username = 'admin'")
        row = await cursor.fetchone()
        user_id = row[0]
        await import_sparx_file(db, SAMPLE_QEA, imported_by=user_id)

        # Check note elements don't have generic "Element N" names
        cursor = await db.execute(
            "SELECT ev.name FROM elements e "
            "JOIN element_versions ev ON e.id = ev.element_id AND e.current_version = ev.version "
            "WHERE e.element_type = 'note'"
        )
        rows = await cursor.fetchall()
        assert len(rows) >= 5
        for row in rows:
            name = row[0]
            # Should not be generic "Element <number>" pattern
            assert not name.startswith("Element "), f"Note has generic name: {name}"

    async def test_canvas_nodes_have_description(
        self, client: httpx.AsyncClient, app_config: AppConfig
    ) -> None:
        headers = await _auth_headers(client)
        db_manager = client._transport.app.state.db_manager  # type: ignore[union-attr]
        db = db_manager.main_db
        cursor = await db.execute("SELECT id FROM users WHERE username = 'admin'")
        row = await cursor.fetchone()
        user_id = row[0]
        await import_sparx_file(db, SAMPLE_QEA, imported_by=user_id)

        # Check diagram_versions with canvas data have nodes with descriptions
        cursor = await db.execute(
            "SELECT data FROM diagram_versions WHERE data IS NOT NULL AND data != '{}'"
        )
        rows = await cursor.fetchall()
        found_description = False
        for row in rows:
            data = json.loads(row[0])
            nodes = data.get("nodes", [])
            for node in nodes:
                node_data = node.get("data", {})
                if node_data.get("description"):
                    found_description = True
                    break
            if found_description:
                break
        assert found_description, "No canvas nodes have description populated"

    async def test_boundary_element_gets_meaningful_name(
        self, client: httpx.AsyncClient, app_config: AppConfig
    ) -> None:
        headers = await _auth_headers(client)
        db_manager = client._transport.app.state.db_manager  # type: ignore[union-attr]
        db = db_manager.main_db
        cursor = await db.execute("SELECT id FROM users WHERE username = 'admin'")
        row = await cursor.fetchone()
        user_id = row[0]
        await import_sparx_file(db, SAMPLE_QEA, imported_by=user_id)

        # Check boundary elements exist and have meaningful names
        cursor = await db.execute(
            "SELECT ev.name FROM elements e "
            "JOIN element_versions ev ON e.id = ev.element_id AND e.current_version = ev.version "
            "WHERE e.element_type = 'boundary'"
        )
        rows = await cursor.fetchall()
        assert len(rows) >= 1
        for row in rows:
            name = row[0]
            assert not name.startswith("Element "), f"Boundary has generic name: {name}"
