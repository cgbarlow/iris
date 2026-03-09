"""Tests for note element dimension fidelity during import (ADR-086).

Verifies that imported notes preserve exact EA rectangle dimensions
(no 1.4x scaling) so the canvas matches the EA diagram pixel-for-pixel.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

import aiosqlite
import httpx
import pytest

from app.config import AppConfig, AuthConfig, DatabaseConfig
from app.database import DatabaseManager
from app.import_sparx.service import import_sparx_file
from app.main import create_app
from app.startup import initialize_databases

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from pathlib import Path


# ---------- Helpers ----------


async def _create_mock_qea(path: str) -> None:
    """Create a minimal .qea SQLite file with a note element on a diagram.

    The note has known EA coordinates:
      RectLeft=9, RectRight=124, RectTop=-332, RectBottom=-468

    Raw EA dimensions: width=115, height=136
    """
    async with aiosqlite.connect(path) as db:
        # Create EA schema tables
        await db.execute(
            "CREATE TABLE t_package ("
            "  Package_ID INTEGER PRIMARY KEY,"
            "  Name TEXT,"
            "  Parent_ID INTEGER DEFAULT 0,"
            "  ea_guid TEXT,"
            "  Notes TEXT"
            ")"
        )
        await db.execute(
            "CREATE TABLE t_object ("
            "  Object_ID INTEGER PRIMARY KEY,"
            "  Object_Type TEXT,"
            "  Name TEXT,"
            "  Package_ID INTEGER DEFAULT 0,"
            "  Note TEXT,"
            "  ea_guid TEXT,"
            "  Status TEXT,"
            "  Stereotype TEXT,"
            "  Version TEXT,"
            "  Scope TEXT,"
            "  Abstract TEXT,"
            "  Persistence TEXT,"
            "  Author TEXT,"
            "  Complexity TEXT,"
            "  Phase TEXT,"
            "  CreatedDate TEXT,"
            "  ModifiedDate TEXT,"
            "  GenType TEXT,"
            "  Backcolor INTEGER DEFAULT -1,"
            "  Fontcolor INTEGER DEFAULT -1,"
            "  Bordercolor INTEGER DEFAULT -1,"
            "  BorderWidth INTEGER DEFAULT -1,"
            "  Alias TEXT,"
            "  PDATA1 TEXT,"
            "  StyleEx TEXT"
            ")"
        )
        await db.execute(
            "CREATE TABLE t_connector ("
            "  Connector_ID INTEGER PRIMARY KEY,"
            "  Connector_Type TEXT,"
            "  Name TEXT,"
            "  Start_Object_ID INTEGER,"
            "  End_Object_ID INTEGER,"
            "  ea_guid TEXT,"
            "  Notes TEXT,"
            "  Direction TEXT,"
            "  SourceCard TEXT,"
            "  DestCard TEXT,"
            "  SourceRole TEXT,"
            "  DestRole TEXT,"
            "  SourceAccess TEXT,"
            "  DestAccess TEXT,"
            "  Stereotype TEXT,"
            "  RouteStyle INTEGER DEFAULT 0,"
            "  SourceIsNavigable TEXT,"
            "  DestIsNavigable TEXT,"
            "  SourceIsAggregate INTEGER DEFAULT 0,"
            "  DestIsAggregate INTEGER DEFAULT 0,"
            "  LineColor INTEGER DEFAULT -1,"
            "  IsBold INTEGER DEFAULT 0,"
            "  LineStyle INTEGER DEFAULT 0,"
            "  Start_Edge INTEGER,"
            "  End_Edge INTEGER,"
            "  PtStartX INTEGER,"
            "  PtStartY INTEGER,"
            "  PtEndX INTEGER,"
            "  PtEndY INTEGER"
            ")"
        )
        await db.execute(
            "CREATE TABLE t_diagramlinks ("
            "  DiagramID INTEGER,"
            "  ConnectorID INTEGER,"
            "  Geometry TEXT,"
            "  Style TEXT,"
            "  Hidden INTEGER DEFAULT 0,"
            "  Path TEXT"
            ")"
        )
        await db.execute(
            "CREATE TABLE t_diagram ("
            "  Diagram_ID INTEGER PRIMARY KEY,"
            "  Name TEXT,"
            "  Diagram_Type TEXT,"
            "  Package_ID INTEGER DEFAULT 0,"
            "  ea_guid TEXT,"
            "  Notes TEXT,"
            "  cx INTEGER DEFAULT 0,"
            "  cy INTEGER DEFAULT 0"
            ")"
        )
        await db.execute(
            "CREATE TABLE t_diagramobjects ("
            "  Diagram_ID INTEGER,"
            "  Object_ID INTEGER,"
            "  RectTop INTEGER,"
            "  RectBottom INTEGER,"
            "  RectLeft INTEGER,"
            "  RectRight INTEGER,"
            "  ObjectStyle TEXT"
            ")"
        )
        await db.execute(
            "CREATE TABLE t_attribute ("
            "  Object_ID INTEGER,"
            "  Name TEXT,"
            "  Type TEXT,"
            "  Notes TEXT,"
            '  "Default" TEXT,'
            "  LowerBound TEXT,"
            "  UpperBound TEXT,"
            "  Stereotype TEXT,"
            "  Scope TEXT,"
            "  Pos INTEGER DEFAULT 0"
            ")"
        )
        await db.execute(
            "CREATE TABLE t_objectproperties ("
            "  Object_ID INTEGER,"
            "  Property TEXT,"
            "  Value TEXT"
            ")"
        )

        # Insert a root package
        await db.execute(
            "INSERT INTO t_package (Package_ID, Name, Parent_ID, ea_guid) "
            "VALUES (1, 'Root', 0, '{PKG-ROOT}')"
        )

        # Insert a Note element
        await db.execute(
            "INSERT INTO t_object (Object_ID, Object_Type, Name, Package_ID, Note, ea_guid) "
            "VALUES (100, 'Note', NULL, 1, '<p>Test note content</p>', '{NOTE-100}')"
        )

        # Insert a diagram
        await db.execute(
            "INSERT INTO t_diagram (Diagram_ID, Name, Diagram_Type, Package_ID, ea_guid) "
            "VALUES (1, 'Test Diagram', 'Logical', 1, '{DIAG-1}')"
        )

        # Place the note on the diagram with known coordinates
        # RectLeft=9, RectRight=124, RectTop=-332, RectBottom=-468
        # Expected: width=115, height=136 (exact EA dimensions, NO 1.4x scaling)
        await db.execute(
            "INSERT INTO t_diagramobjects (Diagram_ID, Object_ID, RectTop, RectBottom, RectLeft, RectRight) "
            "VALUES (1, 100, -332, -468, 9, 124)"
        )

        await db.commit()


# ---------- Fixtures ----------


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
    """Setup admin user and return auth headers."""
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


# ---------- Tests ----------


class TestNoteDimensions:
    """Verify imported notes have exact EA dimensions (no 1.4x scaling)."""

    async def test_note_width_matches_ea_rectangle(
        self, client: httpx.AsyncClient, tmp_path: Path,
    ) -> None:
        """Note visual width should be 115 (raw EA width), not 161 (1.4x scaled)."""
        headers = await _auth_headers(client)
        db_manager = client._transport.app.state.db_manager  # type: ignore[union-attr]
        db = db_manager.main_db

        # Create mock .qea
        qea_path = str(tmp_path / "test_notes.qea")
        await _create_mock_qea(qea_path)

        cursor = await db.execute("SELECT id FROM users WHERE username = 'admin'")
        row = await cursor.fetchone()
        user_id = row[0]
        await import_sparx_file(db, qea_path, imported_by=user_id)

        # Find the imported diagram's canvas data
        cursor = await db.execute(
            "SELECT data FROM diagram_versions WHERE data IS NOT NULL AND data != '{}'"
        )
        rows = await cursor.fetchall()
        assert len(rows) >= 1, "No diagram data found after import"

        # Find the note node
        found_note = False
        for r in rows:
            data = json.loads(r[0])
            for node in data.get("nodes", []):
                node_data = node.get("data", {})
                if node_data.get("entityType") == "note":
                    found_note = True
                    visual = node_data.get("visual", {})
                    assert visual.get("width") == 115, (
                        f"Note width should be 115 (raw EA), got {visual.get('width')}"
                    )
                    break
            if found_note:
                break

        assert found_note, "No note node found in canvas data"

    async def test_note_height_matches_ea_rectangle(
        self, client: httpx.AsyncClient, tmp_path: Path,
    ) -> None:
        """Note visual height should be 136 (raw EA height), not 190 (1.4x scaled)."""
        headers = await _auth_headers(client)
        db_manager = client._transport.app.state.db_manager  # type: ignore[union-attr]
        db = db_manager.main_db

        qea_path = str(tmp_path / "test_notes.qea")
        await _create_mock_qea(qea_path)

        cursor = await db.execute("SELECT id FROM users WHERE username = 'admin'")
        row = await cursor.fetchone()
        user_id = row[0]
        await import_sparx_file(db, qea_path, imported_by=user_id)

        cursor = await db.execute(
            "SELECT data FROM diagram_versions WHERE data IS NOT NULL AND data != '{}'"
        )
        rows = await cursor.fetchall()
        assert len(rows) >= 1

        found_note = False
        for r in rows:
            data = json.loads(r[0])
            for node in data.get("nodes", []):
                node_data = node.get("data", {})
                if node_data.get("entityType") == "note":
                    found_note = True
                    visual = node_data.get("visual", {})
                    assert visual.get("height") == 136, (
                        f"Note height should be 136 (raw EA), got {visual.get('height')}"
                    )
                    break
            if found_note:
                break

        assert found_note, "No note node found in canvas data"

    async def test_note_dimensions_not_scaled(
        self, client: httpx.AsyncClient, tmp_path: Path,
    ) -> None:
        """Confirm note dimensions are NOT the old 1.4x scaled values (161x190)."""
        headers = await _auth_headers(client)
        db_manager = client._transport.app.state.db_manager  # type: ignore[union-attr]
        db = db_manager.main_db

        qea_path = str(tmp_path / "test_notes.qea")
        await _create_mock_qea(qea_path)

        cursor = await db.execute("SELECT id FROM users WHERE username = 'admin'")
        row = await cursor.fetchone()
        user_id = row[0]
        await import_sparx_file(db, qea_path, imported_by=user_id)

        cursor = await db.execute(
            "SELECT data FROM diagram_versions WHERE data IS NOT NULL AND data != '{}'"
        )
        rows = await cursor.fetchall()

        for r in rows:
            data = json.loads(r[0])
            for node in data.get("nodes", []):
                node_data = node.get("data", {})
                if node_data.get("entityType") == "note":
                    visual = node_data.get("visual", {})
                    # These would be the old 1.4x scaled values -- must NOT match
                    assert visual.get("width") != 161, "Note width is still 1.4x scaled (161)"
                    assert visual.get("height") != 190, "Note height is still 1.4x scaled (190)"
