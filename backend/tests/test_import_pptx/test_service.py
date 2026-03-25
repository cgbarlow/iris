"""Tests for DoView PPTX import service."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import httpx
import pytest

from app.config import AppConfig, AuthConfig, DatabaseConfig
from app.database import DatabaseManager
from app.import_pptx.service import import_pptx_file
from app.main import create_app
from app.startup import initialize_databases

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from pathlib import Path


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
async def db_manager(app_config: AppConfig) -> AsyncIterator[DatabaseManager]:
    mgr = DatabaseManager(app_config)
    await initialize_databases(mgr)
    yield mgr
    await mgr.close()


async def _get_user_id(db) -> str:
    """Return any existing user ID from the seeded database."""
    cursor = await db.execute("SELECT id FROM users LIMIT 1")
    row = await cursor.fetchone()
    if row:
        return row[0]
    # Fallback: insert a minimal test user
    import uuid

    user_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO users (id, username, password_hash, role) "
        "VALUES (?, ?, ?, ?)",
        (user_id, "testuser", "placeholder_hash", "admin"),
    )
    await db.commit()
    return user_id


# ---------- Tests ----------


class TestImportPptxFile:
    """import_pptx_file() creates packages, elements, diagrams, relationships."""

    async def test_creates_root_package(
        self, db_manager: DatabaseManager, minimal_doview_pptx: str,
    ) -> None:
        db = db_manager.main_db
        user_id = await _get_user_id(db)
        summary = await import_pptx_file(db, minimal_doview_pptx, imported_by=user_id)
        assert summary.packages_created == 1

    async def test_creates_diagrams(
        self, db_manager: DatabaseManager, minimal_doview_pptx: str,
    ) -> None:
        db = db_manager.main_db
        user_id = await _get_user_id(db)
        summary = await import_pptx_file(db, minimal_doview_pptx, imported_by=user_id)
        # overview + final outcomes + outcomes map = 3 (info slide skipped)
        assert summary.diagrams_created == 3
        assert summary.slides_skipped == 1

    async def test_creates_elements(
        self, db_manager: DatabaseManager, minimal_doview_pptx: str,
    ) -> None:
        db = db_manager.main_db
        user_id = await _get_user_id(db)
        summary = await import_pptx_file(db, minimal_doview_pptx, imported_by=user_id)
        # 4 overview tiles + 2 final outcomes + 4 outcome boxes = 10
        assert summary.elements_created == 10

    async def test_creates_relationships(
        self, db_manager: DatabaseManager, minimal_doview_pptx: str,
    ) -> None:
        db = db_manager.main_db
        user_id = await _get_user_id(db)
        summary = await import_pptx_file(db, minimal_doview_pptx, imported_by=user_id)
        # 2 source × 2 target = 4 causal links (all-to-all between 2 columns)
        assert summary.relationships_created == 4

    async def test_diagrams_have_doview_notation(
        self, db_manager: DatabaseManager, minimal_doview_pptx: str,
    ) -> None:
        db = db_manager.main_db
        user_id = await _get_user_id(db)
        await import_pptx_file(db, minimal_doview_pptx, imported_by=user_id)
        cursor = await db.execute(
            "SELECT notation FROM diagrams WHERE is_deleted = 0 AND notation = 'doview'"
        )
        rows = await cursor.fetchall()
        assert len(rows) == 3

    async def test_outcomes_map_has_causal_edges(
        self, db_manager: DatabaseManager, minimal_doview_pptx: str,
    ) -> None:
        db = db_manager.main_db
        user_id = await _get_user_id(db)
        await import_pptx_file(db, minimal_doview_pptx, imported_by=user_id)
        cursor = await db.execute(
            "SELECT dv.data FROM diagram_versions dv "
            "JOIN diagrams d ON d.id = dv.diagram_id "
            "WHERE d.diagram_type = 'outcomes_map' AND d.notation = 'doview' "
            "AND d.is_deleted = 0"
        )
        rows = await cursor.fetchall()
        found_edges = False
        for row in rows:
            data = json.loads(row[0])
            if data.get("edges"):
                found_edges = True
                for edge in data["edges"]:
                    assert edge["type"] == "causal_link"
                    assert edge["sourceHandle"] == "center"
                    assert edge["targetHandle"] == "center"
        assert found_edges

    async def test_node_colors_preserved(
        self, db_manager: DatabaseManager, minimal_doview_pptx: str,
    ) -> None:
        db = db_manager.main_db
        user_id = await _get_user_id(db)
        await import_pptx_file(db, minimal_doview_pptx, imported_by=user_id)
        cursor = await db.execute(
            "SELECT dv.data FROM diagram_versions dv "
            "JOIN diagrams d ON d.id = dv.diagram_id "
            "WHERE d.is_deleted = 0 AND d.notation = 'doview'"
        )
        rows = await cursor.fetchall()
        for row in rows:
            data = json.loads(row[0])
            for node in data.get("nodes", []):
                visual = node.get("data", {}).get("visual", {})
                assert "bgColor" in visual
                assert "borderColor" in visual

    async def test_coordinate_conversion(
        self, db_manager: DatabaseManager, minimal_doview_pptx: str,
    ) -> None:
        """Positions should be in pixels, not EMU."""
        db = db_manager.main_db
        user_id = await _get_user_id(db)
        await import_pptx_file(db, minimal_doview_pptx, imported_by=user_id)
        cursor = await db.execute(
            "SELECT dv.data FROM diagram_versions dv "
            "JOIN diagrams d ON d.id = dv.diagram_id "
            "WHERE d.is_deleted = 0 AND d.notation = 'doview' LIMIT 1"
        )
        row = await cursor.fetchone()
        data = json.loads(row[0])
        for node in data.get("nodes", []):
            # EMU values are 100000+; pixel values should be < 2000
            assert node["position"]["x"] < 2000
            assert node["position"]["y"] < 2000


class TestImportPptxCompliance:
    """Compliance validation rejects non-DoView files."""

    async def test_non_doview_raises(
        self, db_manager: DatabaseManager, non_doview_pptx: str,
    ) -> None:
        db = db_manager.main_db
        user_id = await _get_user_id(db)
        with pytest.raises(ValueError, match="does not appear to be a DoView"):
            await import_pptx_file(db, non_doview_pptx, imported_by=user_id)
