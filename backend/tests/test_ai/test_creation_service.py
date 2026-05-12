"""Tests for AI diagram creation service (ADR-094-B)."""

from __future__ import annotations

import json

import aiosqlite
import pytest
import pytest_asyncio

from app.ai.creation import build_creation_system_prompt, create_diagrams_from_ai
from app.migrations.m026_ai_providers import up as m026_up
from app.migrations.m028_ai_creation_prompts import up as m028_up
from app.migrations.m051_response_format_prompts import up as m051_up


async def _minimal_schema(conn: aiosqlite.Connection) -> None:
    """Set up minimal tables needed for creation service tests.

    Mirrors the real schema: diagrams has no 'name' column (stored in
    diagram_versions), and diagram_versions uses a composite PK.
    """
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS sets (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            created_by TEXT NOT NULL DEFAULT 'system',
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            is_deleted INTEGER NOT NULL DEFAULT 0
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS diagrams (
            id TEXT PRIMARY KEY,
            set_id TEXT NOT NULL,
            diagram_type TEXT NOT NULL DEFAULT 'free_form',
            notation TEXT,
            parent_package_id TEXT,
            current_version INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            created_by TEXT NOT NULL DEFAULT 'system',
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            is_deleted INTEGER NOT NULL DEFAULT 0
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS diagram_versions (
            diagram_id TEXT NOT NULL,
            version INTEGER NOT NULL,
            name TEXT NOT NULL DEFAULT '',
            data TEXT NOT NULL DEFAULT '{}',
            change_type TEXT NOT NULL DEFAULT 'create',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            created_by TEXT NOT NULL DEFAULT 'system',
            PRIMARY KEY (diagram_id, version)
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS elements (
            id TEXT PRIMARY KEY,
            element_type TEXT NOT NULL,
            set_id TEXT,
            current_version INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            created_by TEXT NOT NULL DEFAULT 'system',
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            is_deleted INTEGER NOT NULL DEFAULT 0,
            notation TEXT
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS element_versions (
            element_id TEXT NOT NULL,
            version INTEGER NOT NULL,
            name TEXT NOT NULL DEFAULT '',
            description TEXT,
            data TEXT NOT NULL DEFAULT '{}',
            change_type TEXT NOT NULL DEFAULT 'create',
            change_summary TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            created_by TEXT NOT NULL DEFAULT 'system',
            metadata TEXT,
            PRIMARY KEY (element_id, version)
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS relationships (
            id TEXT PRIMARY KEY,
            source_element_id TEXT NOT NULL,
            target_element_id TEXT NOT NULL,
            relationship_type TEXT NOT NULL,
            current_version INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            created_by TEXT NOT NULL DEFAULT 'system',
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            is_deleted INTEGER NOT NULL DEFAULT 0
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS relationship_versions (
            relationship_id TEXT NOT NULL,
            version INTEGER NOT NULL,
            label TEXT NOT NULL DEFAULT '',
            description TEXT,
            data TEXT NOT NULL DEFAULT '{}',
            change_type TEXT NOT NULL DEFAULT 'create',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            created_by TEXT NOT NULL DEFAULT 'system',
            PRIMARY KEY (relationship_id, version)
        )
    """)
    await conn.execute("INSERT OR IGNORE INTO sets VALUES ('test-set', 'Test Set', NULL, datetime('now'), 'system', datetime('now'), 0)")
    await conn.commit()


@pytest_asyncio.fixture
async def db():
    async with aiosqlite.connect(":memory:") as conn:
        await _minimal_schema(conn)
        await m026_up(conn)
        await m028_up(conn)
        # m051 adds the `purpose` column the composer filters on
        # (ADR-157, v5.12.0). Registry inserts in m051 are auto-skipped
        # when their tables aren't present in this minimal fixture.
        await m051_up(conn)
        yield conn


# ── build_creation_system_prompt ──────────────────────────────────────────────

class TestBuildCreationSystemPrompt:
    @pytest.mark.asyncio
    async def test_returns_string(self, db: aiosqlite.Connection) -> None:
        result = await build_creation_system_prompt(db, notation="doview")
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_base_layer_included(self, db: aiosqlite.Connection) -> None:
        result = await build_creation_system_prompt(db, notation="doview")
        # Base prompt should reference the output schema
        assert "diagrams" in result.lower()

    @pytest.mark.asyncio
    async def test_doview_notation_layer_included(self, db: aiosqlite.Connection) -> None:
        result = await build_creation_system_prompt(db, notation="doview")
        # DoView prompt should include methodology language
        assert "doview" in result.lower()

    @pytest.mark.asyncio
    async def test_diagram_type_layer_included(self, db: aiosqlite.Connection) -> None:
        result = await build_creation_system_prompt(db, notation="doview", diagram_type="outcomes_map")
        # Should include both notation and diagram-type layers
        assert "outcomes_map" in result.lower() or "outcomes map" in result.lower()

    @pytest.mark.asyncio
    async def test_override_replaces_all_layers(self, db: aiosqlite.Connection) -> None:
        # Insert an override prompt
        await db.execute("""
            INSERT INTO ai_creation_prompts (id, name, layer, notation, diagram_type, prompt_text)
            VALUES ('test-override', 'Override', 'override', 'doview', NULL, 'ONLY THIS TEXT')
        """)
        await db.commit()
        result = await build_creation_system_prompt(db, notation="doview")
        assert result == "ONLY THIS TEXT"

    @pytest.mark.asyncio
    async def test_inactive_prompts_excluded(self, db: aiosqlite.Connection) -> None:
        # Disable all prompts
        await db.execute("UPDATE ai_creation_prompts SET is_active = 0")
        await db.commit()
        result = await build_creation_system_prompt(db, notation="doview")
        assert result == ""

    @pytest.mark.asyncio
    async def test_unknown_notation_returns_base_only(self, db: aiosqlite.Connection) -> None:
        result = await build_creation_system_prompt(db, notation="nonexistent")
        # Should return base prompt only (no notation-specific layer)
        base_only = await build_creation_system_prompt(db, notation="doview")
        # Should be shorter than full doview prompt
        assert len(result) < len(base_only)


# ── create_diagrams_from_ai ───────────────────────────────────────────────────

class TestCreateDiagramsFromAI:
    @pytest.mark.asyncio
    async def test_creates_single_diagram(self, db: aiosqlite.Connection) -> None:
        ai_json = {
            "diagrams": [
                {
                    "name": "Climate Action",
                    "diagram_type": "outcomes_map",
                    "notation": "doview",
                    "nodes": [
                        {
                            "id": "n1",
                            "type": "outcome_box",
                            "label": "Funding secured",
                            "position": {"x": 100, "y": 100},
                            "size": {"width": 200, "height": 86},
                            "visual": {"bgColor": "#FFF2CC", "borderColor": "#D6B656"},
                        }
                    ],
                    "edges": [],
                }
            ]
        }
        ids = await create_diagrams_from_ai(db, "test-set", ai_json, "user-1")
        assert len(ids) == 1

    @pytest.mark.asyncio
    async def test_creates_multiple_diagrams(self, db: aiosqlite.Connection) -> None:
        ai_json = {
            "diagrams": [
                {"name": "Overview", "diagram_type": "overview", "notation": "doview", "nodes": [], "edges": []},
                {"name": "Final Outcomes", "diagram_type": "outcomes_map", "notation": "doview", "nodes": [], "edges": []},
                {"name": "Climate", "diagram_type": "outcomes_map", "notation": "doview", "nodes": [], "edges": []},
            ]
        }
        ids = await create_diagrams_from_ai(db, "test-set", ai_json, "user-1")
        assert len(ids) == 3

    @pytest.mark.asyncio
    async def test_diagram_notation_set_correctly(self, db: aiosqlite.Connection) -> None:
        ai_json = {
            "diagrams": [
                {"name": "Test", "diagram_type": "outcomes_map", "notation": "doview", "nodes": [], "edges": []}
            ]
        }
        ids = await create_diagrams_from_ai(db, "test-set", ai_json, "user-1")
        cursor = await db.execute("SELECT notation FROM diagrams WHERE id = ?", (ids[0],))
        row = await cursor.fetchone()
        assert row[0] == "doview"

    @pytest.mark.asyncio
    async def test_canvas_data_stored(self, db: aiosqlite.Connection) -> None:
        ai_json = {
            "diagrams": [
                {
                    "name": "With Nodes",
                    "diagram_type": "outcomes_map",
                    "notation": "doview",
                    "nodes": [
                        {"id": "n1", "type": "outcome_box", "label": "Test outcome",
                         "position": {"x": 0, "y": 0}, "size": {"width": 200, "height": 86}, "visual": {}}
                    ],
                    "edges": [
                        {"id": "e1", "type": "causal_link", "source": "n1", "target": "n1", "visual": {}}
                    ],
                }
            ]
        }
        ids = await create_diagrams_from_ai(db, "test-set", ai_json, "user-1")
        cursor = await db.execute(
            "SELECT data FROM diagram_versions WHERE diagram_id = ?", (ids[0],)
        )
        row = await cursor.fetchone()
        data = json.loads(row[0])
        assert "nodes" in data
        assert len(data["nodes"]) == 1
        assert data["nodes"][0]["data"]["label"] == "Test outcome"

    @pytest.mark.asyncio
    async def test_linked_diagram_index_resolved(self, db: aiosqlite.Connection) -> None:
        """overview_tile linkedDiagramIndex should be resolved to actual diagram ID."""
        ai_json = {
            "diagrams": [
                {
                    "name": "Overview",
                    "diagram_type": "overview",
                    "notation": "doview",
                    "nodes": [
                        {
                            "id": "tile-1",
                            "type": "overview_tile",
                            "label": "Climate",
                            "position": {"x": 0, "y": 0},
                            "size": {"width": 200, "height": 86},
                            "visual": {},
                            "linkedDiagramIndex": 1,
                        }
                    ],
                    "edges": [],
                },
                {
                    "name": "Climate Subpage",
                    "diagram_type": "outcomes_map",
                    "notation": "doview",
                    "nodes": [],
                    "edges": [],
                },
            ]
        }
        ids = await create_diagrams_from_ai(db, "test-set", ai_json, "user-1")
        # Overview is ids[0], Climate is ids[1]
        # The overview_tile node should have linkedModelId = ids[1]
        cursor = await db.execute(
            "SELECT data FROM diagram_versions WHERE diagram_id = ?", (ids[0],)
        )
        row = await cursor.fetchone()
        data = json.loads(row[0])
        tile_node = next(n for n in data["nodes"] if n["data"]["entityType"] == "overview_tile")
        assert tile_node["data"].get("linkedModelId") == ids[1]

    @pytest.mark.asyncio
    async def test_empty_diagrams_array_returns_empty(self, db: aiosqlite.Connection) -> None:
        ai_json = {"diagrams": []}
        ids = await create_diagrams_from_ai(db, "test-set", ai_json, "user-1")
        assert ids == []

    @pytest.mark.asyncio
    async def test_invalid_json_raises(self, db: aiosqlite.Connection) -> None:
        with pytest.raises((ValueError, KeyError)):
            await create_diagrams_from_ai(db, "test-set", {"wrong_key": []}, "user-1")
