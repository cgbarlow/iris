"""Tests for diagram frame as canvas node after import (ADR-088).

Verifies that imported diagrams include a diagram_frame node in the
nodes array (not a separate diagramFrame field), with type, name,
width, and height derived from EA's cx/cy columns.
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


async def _create_mock_qea_with_frame(path: str) -> None:
    """Create a minimal .qea SQLite file with diagram cx/cy dimensions.

    Diagram: Name='Main', Diagram_Type='Logical', cx=799, cy=1067
    """
    async with aiosqlite.connect(path) as db:
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
            "  PDATA1 TEXT"
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

        # Insert a Class element so the diagram is not empty
        await db.execute(
            "INSERT INTO t_object (Object_ID, Object_Type, Name, Package_ID, Note, ea_guid) "
            "VALUES (200, 'Class', 'SampleClass', 1, NULL, '{CLASS-200}')"
        )

        # Insert a diagram with cx/cy
        await db.execute(
            "INSERT INTO t_diagram (Diagram_ID, Name, Diagram_Type, Package_ID, ea_guid, cx, cy) "
            "VALUES (1, 'Main', 'Logical', 1, '{DIAG-1}', 799, 1067)"
        )

        # Place the class on the diagram
        await db.execute(
            "INSERT INTO t_diagramobjects (Diagram_ID, Object_ID, RectTop, RectBottom, RectLeft, RectRight) "
            "VALUES (1, 200, -100, -200, 50, 200)"
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


class TestDiagramFrame:
    """Verify imported diagrams include diagram_frame as a node in the nodes array."""

    async def test_frame_is_a_node_in_nodes_array(
        self, client: httpx.AsyncClient, tmp_path: Path,
    ) -> None:
        """After import, diagram canvas data must contain a diagram_frame node."""
        headers = await _auth_headers(client)
        db_manager = client._transport.app.state.db_manager  # type: ignore[union-attr]
        db = db_manager.main_db

        qea_path = str(tmp_path / "test_frame.qea")
        await _create_mock_qea_with_frame(qea_path)

        cursor = await db.execute("SELECT id FROM users WHERE username = 'admin'")
        row = await cursor.fetchone()
        user_id = row[0]
        await import_sparx_file(db, qea_path, imported_by=user_id)

        cursor = await db.execute(
            "SELECT data FROM diagram_versions WHERE data IS NOT NULL AND data != '{}'"
        )
        rows = await cursor.fetchall()
        assert len(rows) >= 1, "No diagram data found after import"

        data = json.loads(rows[0][0])
        nodes = data.get("nodes", [])
        frame_nodes = [n for n in nodes if n.get("type") == "diagram_frame"]
        assert len(frame_nodes) == 1, f"Expected 1 diagram_frame node, found {len(frame_nodes)}"

    async def test_frame_node_has_dimensions(
        self, client: httpx.AsyncClient, tmp_path: Path,
    ) -> None:
        """diagram_frame node should include frameWidth and frameHeight in data."""
        headers = await _auth_headers(client)
        db_manager = client._transport.app.state.db_manager  # type: ignore[union-attr]
        db = db_manager.main_db

        qea_path = str(tmp_path / "test_frame.qea")
        await _create_mock_qea_with_frame(qea_path)

        cursor = await db.execute("SELECT id FROM users WHERE username = 'admin'")
        row = await cursor.fetchone()
        user_id = row[0]
        await import_sparx_file(db, qea_path, imported_by=user_id)

        cursor = await db.execute(
            "SELECT data FROM diagram_versions WHERE data IS NOT NULL AND data != '{}'"
        )
        rows = await cursor.fetchall()
        data = json.loads(rows[0][0])
        nodes = data.get("nodes", [])
        frame_node = next(n for n in nodes if n.get("type") == "diagram_frame")
        assert frame_node["data"]["frameWidth"] == 799
        assert frame_node["data"]["frameHeight"] == 1067

    async def test_frame_node_has_name_and_type(
        self, client: httpx.AsyncClient, tmp_path: Path,
    ) -> None:
        """diagram_frame node data should have frameType and label."""
        headers = await _auth_headers(client)
        db_manager = client._transport.app.state.db_manager  # type: ignore[union-attr]
        db = db_manager.main_db

        qea_path = str(tmp_path / "test_frame.qea")
        await _create_mock_qea_with_frame(qea_path)

        cursor = await db.execute("SELECT id FROM users WHERE username = 'admin'")
        row = await cursor.fetchone()
        user_id = row[0]
        await import_sparx_file(db, qea_path, imported_by=user_id)

        cursor = await db.execute(
            "SELECT data FROM diagram_versions WHERE data IS NOT NULL AND data != '{}'"
        )
        rows = await cursor.fetchall()
        data = json.loads(rows[0][0])
        nodes = data.get("nodes", [])
        frame_node = next(n for n in nodes if n.get("type") == "diagram_frame")
        assert frame_node["data"]["frameType"] == "class"
        assert frame_node["data"]["label"] == "Main"

    async def test_no_separate_diagram_frame_field(
        self, client: httpx.AsyncClient, tmp_path: Path,
    ) -> None:
        """diagramFrame should NOT exist as a separate field in canvas data."""
        headers = await _auth_headers(client)
        db_manager = client._transport.app.state.db_manager  # type: ignore[union-attr]
        db = db_manager.main_db

        qea_path = str(tmp_path / "test_frame.qea")
        await _create_mock_qea_with_frame(qea_path)

        cursor = await db.execute("SELECT id FROM users WHERE username = 'admin'")
        row = await cursor.fetchone()
        user_id = row[0]
        await import_sparx_file(db, qea_path, imported_by=user_id)

        cursor = await db.execute(
            "SELECT data FROM diagram_versions WHERE data IS NOT NULL AND data != '{}'"
        )
        rows = await cursor.fetchall()
        data = json.loads(rows[0][0])
        assert "diagramFrame" not in data, "diagramFrame should be a node, not a separate field"
