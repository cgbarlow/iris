"""Tests for AI creation with element/relationship materialisation (ADR-100).

Verifies that create_diagrams_from_ai() materialises element and relationship
records alongside diagram nodes and edges, so DoView diagrams have entityId
and relationshipId references to real database records.
"""

from __future__ import annotations

import json

import aiosqlite
import pytest
import pytest_asyncio

from app.ai.creation import create_diagrams_from_ai


_TEST_USER_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
_TEST_SET_ID = "test-set-0001"


async def _setup_schema(conn: aiosqlite.Connection) -> None:
    """Create minimal schema for AI creation + element/relationship tables.

    Mirrors the real schema after all migrations: diagrams, diagram_versions,
    elements, element_versions, relationships, relationship_versions.
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
            set_id TEXT NOT NULL,
            current_version INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            created_by TEXT NOT NULL DEFAULT 'system',
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            is_deleted INTEGER NOT NULL DEFAULT 0,
            notation TEXT DEFAULT 'simple'
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS element_versions (
            element_id TEXT NOT NULL,
            version INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            data TEXT NOT NULL DEFAULT '{}',
            change_type TEXT NOT NULL DEFAULT 'create',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            created_by TEXT NOT NULL DEFAULT 'system',
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
            label TEXT,
            description TEXT,
            data TEXT,
            change_type TEXT NOT NULL DEFAULT 'create',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            created_by TEXT NOT NULL DEFAULT 'system',
            PRIMARY KEY (relationship_id, version)
        )
    """)
    await conn.execute(
        "INSERT OR IGNORE INTO sets VALUES (?, 'Test Set', NULL, datetime('now'), 'system', datetime('now'), 0)",
        (_TEST_SET_ID,),
    )
    await conn.commit()


def _sample_ai_json() -> dict:
    """Return a minimal DoView AI JSON with 1 diagram, 2 nodes, and 1 edge."""
    return {
        "diagrams": [
            {
                "name": "Climate Outcomes",
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
                    },
                    {
                        "id": "n2",
                        "type": "outcome_box",
                        "label": "Programs delivered",
                        "position": {"x": 400, "y": 100},
                        "size": {"width": 200, "height": 86},
                        "visual": {"bgColor": "#D5E8D4", "borderColor": "#82B366"},
                    },
                ],
                "edges": [
                    {
                        "id": "e1",
                        "type": "causal_link",
                        "source": "n1",
                        "target": "n2",
                        "visual": {},
                    },
                ],
            }
        ]
    }


@pytest_asyncio.fixture
async def db() -> aiosqlite.Connection:
    async with aiosqlite.connect(":memory:") as conn:
        await _setup_schema(conn)
        yield conn


class TestAICreationMaterialisation:
    """Tests verifying that AI-created diagrams materialise element and relationship records."""

    @pytest.mark.asyncio
    async def test_nodes_have_entity_id(self, db: aiosqlite.Connection) -> None:
        """Each node in the saved diagram data has an entityId field."""
        ids = await create_diagrams_from_ai(db, _TEST_SET_ID, _sample_ai_json(), _TEST_USER_ID)
        assert len(ids) == 1

        cursor = await db.execute(
            "SELECT data FROM diagram_versions WHERE diagram_id = ? AND version = 1",
            (ids[0],),
        )
        row = await cursor.fetchone()
        data = json.loads(row[0])

        for node in data["nodes"]:
            entity_id = node["data"].get("entityId")
            assert entity_id, (
                f"Node {node['id']} missing entityId in diagram data"
            )

    @pytest.mark.asyncio
    async def test_element_records_exist_for_each_node(self, db: aiosqlite.Connection) -> None:
        """An element record exists in the database for every node entityId."""
        ids = await create_diagrams_from_ai(db, _TEST_SET_ID, _sample_ai_json(), _TEST_USER_ID)

        cursor = await db.execute(
            "SELECT data FROM diagram_versions WHERE diagram_id = ? AND version = 1",
            (ids[0],),
        )
        row = await cursor.fetchone()
        data = json.loads(row[0])

        for node in data["nodes"]:
            entity_id = node["data"]["entityId"]
            cursor = await db.execute(
                "SELECT id FROM elements WHERE id = ?", (entity_id,),
            )
            elem_row = await cursor.fetchone()
            assert elem_row is not None, (
                f"Element {entity_id} for node {node['id']} not found in elements table"
            )

            # Verify element_versions row exists too
            cursor = await db.execute(
                "SELECT name FROM element_versions WHERE element_id = ? AND version = 1",
                (entity_id,),
            )
            ver_row = await cursor.fetchone()
            assert ver_row is not None, (
                f"element_versions missing for element {entity_id}"
            )

    @pytest.mark.asyncio
    async def test_edge_has_relationship_id(self, db: aiosqlite.Connection) -> None:
        """The causal_link edge in the saved diagram data has a relationshipId field."""
        ids = await create_diagrams_from_ai(db, _TEST_SET_ID, _sample_ai_json(), _TEST_USER_ID)

        cursor = await db.execute(
            "SELECT data FROM diagram_versions WHERE diagram_id = ? AND version = 1",
            (ids[0],),
        )
        row = await cursor.fetchone()
        data = json.loads(row[0])

        causal_edges = [
            e for e in data["edges"]
            if e["data"].get("relationshipType") == "causal_link"
        ]
        assert len(causal_edges) == 1
        rel_id = causal_edges[0]["data"].get("relationshipId")
        assert rel_id, "Edge missing relationshipId"

    @pytest.mark.asyncio
    async def test_relationship_record_exists(self, db: aiosqlite.Connection) -> None:
        """A relationship record exists for the edge's relationshipId."""
        ids = await create_diagrams_from_ai(db, _TEST_SET_ID, _sample_ai_json(), _TEST_USER_ID)

        cursor = await db.execute(
            "SELECT data FROM diagram_versions WHERE diagram_id = ? AND version = 1",
            (ids[0],),
        )
        row = await cursor.fetchone()
        data = json.loads(row[0])

        for edge in data["edges"]:
            rel_id = edge["data"].get("relationshipId")
            if not rel_id:
                continue
            cursor = await db.execute(
                "SELECT id FROM relationships WHERE id = ?", (rel_id,),
            )
            rel_row = await cursor.fetchone()
            assert rel_row is not None, (
                f"Relationship {rel_id} for edge {edge['id']} not found in relationships table"
            )

            # Verify relationship_versions row exists too
            cursor = await db.execute(
                "SELECT label FROM relationship_versions WHERE relationship_id = ? AND version = 1",
                (rel_id,),
            )
            ver_row = await cursor.fetchone()
            assert ver_row is not None, (
                f"relationship_versions missing for relationship {rel_id}"
            )

    @pytest.mark.asyncio
    async def test_element_notation_matches_diagram(self, db: aiosqlite.Connection) -> None:
        """Elements created from a DoView diagram have notation='doview'."""
        ids = await create_diagrams_from_ai(db, _TEST_SET_ID, _sample_ai_json(), _TEST_USER_ID)

        # Get diagram notation
        cursor = await db.execute(
            "SELECT notation FROM diagrams WHERE id = ?", (ids[0],),
        )
        diagram_notation = (await cursor.fetchone())[0]
        assert diagram_notation == "doview"

        # Get all element notations created for this diagram
        cursor = await db.execute(
            "SELECT data FROM diagram_versions WHERE diagram_id = ? AND version = 1",
            (ids[0],),
        )
        row = await cursor.fetchone()
        data = json.loads(row[0])

        for node in data["nodes"]:
            entity_id = node["data"].get("entityId")
            if not entity_id:
                continue
            cursor = await db.execute(
                "SELECT notation FROM elements WHERE id = ?", (entity_id,),
            )
            elem_row = await cursor.fetchone()
            assert elem_row is not None, f"Element {entity_id} not found"
            assert elem_row[0] == diagram_notation, (
                f"Element {entity_id} notation={elem_row[0]}, expected {diagram_notation}"
            )

    @pytest.mark.asyncio
    async def test_element_count_matches_node_count(self, db: aiosqlite.Connection) -> None:
        """Two nodes produce exactly two element records."""
        await create_diagrams_from_ai(db, _TEST_SET_ID, _sample_ai_json(), _TEST_USER_ID)

        cursor = await db.execute(
            "SELECT COUNT(*) FROM elements WHERE set_id = ?", (_TEST_SET_ID,),
        )
        count = (await cursor.fetchone())[0]
        assert count == 2

    @pytest.mark.asyncio
    async def test_relationship_count_matches_edge_count(self, db: aiosqlite.Connection) -> None:
        """One causal_link edge produces exactly one relationship record."""
        await create_diagrams_from_ai(db, _TEST_SET_ID, _sample_ai_json(), _TEST_USER_ID)

        cursor = await db.execute("SELECT COUNT(*) FROM relationships")
        count = (await cursor.fetchone())[0]
        assert count == 1
