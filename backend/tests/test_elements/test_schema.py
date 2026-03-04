"""Tests for Migration 002: elements, relationships, diagrams and their version tables."""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING

import pytest

from app.migrations.m001_roles_users import up as m001_up
from app.migrations.m002_entities_relationships_models import up as m002_up
from app.migrations.m004_comments_bookmarks import up as m004_up
from app.migrations.m005_search import up as m005_up
from app.migrations.m006_settings import up as m006_up
from app.migrations.m007_thumbnails import up as m007_up
from app.migrations.m008_entity_tags import up as m008_up
from app.migrations.m009_model_tags import up as m009_up
from app.migrations.m010_thumbnail_themes import up as m010_up
from app.migrations.m011_model_hierarchy import up as m011_up
from app.migrations.m012_sets import up as m012_up
from app.migrations.m013_set_thumbnails import up as m013_up
from app.migrations.m014_sets_partial_unique import up as m014_up
from app.migrations.m015_model_relationships import up as m015_up
from app.migrations.m016_naming_rename import up as m016_up

if TYPE_CHECKING:
    import aiosqlite


async def _setup_db(db: aiosqlite.Connection) -> None:
    """Run all migrations and seed a test user."""
    await m001_up(db)
    await m002_up(db)
    await m004_up(db)
    await m005_up(db)
    await m006_up(db)
    await m007_up(db)
    await m008_up(db)
    await m009_up(db)
    await m010_up(db)
    await m011_up(db)
    await m012_up(db)
    await m013_up(db)
    await m014_up(db)
    await m015_up(db)
    await m016_up(db)
    await db.execute(
        "INSERT INTO roles (id, name, description) VALUES ('admin', 'Admin', 'Admin role')"
    )
    await db.execute(
        "INSERT INTO users (id, username, password_hash, role) "
        "VALUES ('user1', 'testadmin', 'hash', 'admin')"
    )
    await db.commit()


class TestMigration002Tables:
    """Verify all 6 tables are created."""

    async def test_elements_table_exists(self, main_db: aiosqlite.Connection) -> None:
        await _setup_db(main_db)
        cursor = await main_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='elements'"
        )
        assert await cursor.fetchone() is not None

    async def test_element_versions_table_exists(self, main_db: aiosqlite.Connection) -> None:
        await _setup_db(main_db)
        cursor = await main_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='element_versions'"
        )
        assert await cursor.fetchone() is not None

    async def test_relationships_table_exists(self, main_db: aiosqlite.Connection) -> None:
        await _setup_db(main_db)
        cursor = await main_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='relationships'"
        )
        assert await cursor.fetchone() is not None

    async def test_relationship_versions_table_exists(
        self, main_db: aiosqlite.Connection
    ) -> None:
        await _setup_db(main_db)
        cursor = await main_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='relationship_versions'"
        )
        assert await cursor.fetchone() is not None

    async def test_diagrams_table_exists(self, main_db: aiosqlite.Connection) -> None:
        await _setup_db(main_db)
        cursor = await main_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='diagrams'"
        )
        assert await cursor.fetchone() is not None

    async def test_diagram_versions_table_exists(self, main_db: aiosqlite.Connection) -> None:
        await _setup_db(main_db)
        cursor = await main_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='diagram_versions'"
        )
        assert await cursor.fetchone() is not None


class TestElementVersioning:
    """Verify element versioning schema constraints."""

    async def test_create_element_with_version(self, main_db: aiosqlite.Connection) -> None:
        await _setup_db(main_db)
        await main_db.execute(
            "INSERT INTO elements (id, element_type, current_version, created_by) "
            "VALUES ('e1', 'component', 1, 'user1')"
        )
        await main_db.execute(
            "INSERT INTO element_versions "
            "(element_id, version, name, description, data, change_type, created_by) "
            "VALUES ('e1', 1, 'Auth Service', 'Handles auth', '{}', 'create', 'user1')"
        )
        await main_db.commit()
        cursor = await main_db.execute("SELECT name FROM element_versions WHERE element_id='e1'")
        row = await cursor.fetchone()
        assert row[0] == "Auth Service"

    async def test_change_type_check_constraint(self, main_db: aiosqlite.Connection) -> None:
        await _setup_db(main_db)
        await main_db.execute(
            "INSERT INTO elements (id, element_type, current_version, created_by) "
            "VALUES ('e1', 'component', 1, 'user1')"
        )
        with pytest.raises(sqlite3.IntegrityError):
            await main_db.execute(
                "INSERT INTO element_versions "
                "(element_id, version, name, data, change_type, created_by) "
                "VALUES ('e1', 1, 'Test', '{}', 'invalid_type', 'user1')"
            )

    async def test_element_version_composite_key(self, main_db: aiosqlite.Connection) -> None:
        await _setup_db(main_db)
        await main_db.execute(
            "INSERT INTO elements (id, element_type, current_version, created_by) "
            "VALUES ('e1', 'component', 2, 'user1')"
        )
        await main_db.execute(
            "INSERT INTO element_versions "
            "(element_id, version, name, data, change_type, created_by) "
            "VALUES ('e1', 1, 'V1', '{}', 'create', 'user1')"
        )
        await main_db.execute(
            "INSERT INTO element_versions "
            "(element_id, version, name, data, change_type, created_by) "
            "VALUES ('e1', 2, 'V2', '{}', 'update', 'user1')"
        )
        await main_db.commit()
        cursor = await main_db.execute(
            "SELECT COUNT(*) FROM element_versions WHERE element_id='e1'"
        )
        row = await cursor.fetchone()
        assert row[0] == 2


class TestRelationshipSchema:
    """Verify relationship tables and indexes."""

    async def test_create_relationship(self, main_db: aiosqlite.Connection) -> None:
        await _setup_db(main_db)
        # Create two elements first
        for eid in ("e1", "e2"):
            await main_db.execute(
                "INSERT INTO elements (id, element_type, current_version, created_by) "
                "VALUES (?, 'component', 1, 'user1')",
                (eid,),
            )
            await main_db.execute(
                "INSERT INTO element_versions "
                "(element_id, version, name, data, change_type, created_by) "
                "VALUES (?, 1, ?, '{}', 'create', 'user1')",
                (eid, f"Element {eid}"),
            )
        await main_db.execute(
            "INSERT INTO relationships "
            "(id, source_element_id, target_element_id, relationship_type, "
            "current_version, created_by) "
            "VALUES ('r1', 'e1', 'e2', 'uses', 1, 'user1')"
        )
        await main_db.execute(
            "INSERT INTO relationship_versions "
            "(relationship_id, version, label, change_type, created_by) "
            "VALUES ('r1', 1, 'uses API', 'create', 'user1')"
        )
        await main_db.commit()
        cursor = await main_db.execute(
            "SELECT label FROM relationship_versions WHERE relationship_id='r1'"
        )
        row = await cursor.fetchone()
        assert row[0] == "uses API"

    async def test_relationship_indexes(self, main_db: aiosqlite.Connection) -> None:
        await _setup_db(main_db)
        cursor = await main_db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_relationships%'"
        )
        indexes = {row[0] for row in await cursor.fetchall()}
        assert "idx_relationships_source" in indexes
        assert "idx_relationships_target" in indexes
        assert "idx_relationships_type" in indexes
        assert "idx_relationships_created_by" in indexes


class TestDiagramSchema:
    """Verify diagram tables with denormalized placements."""

    async def test_create_diagram_with_placements(self, main_db: aiosqlite.Connection) -> None:
        await _setup_db(main_db)
        placement = {
            "element_id": "e1",
            "position": {"x": 100, "y": 200},
            "size": {"width": 180, "height": 80},
        }
        placements_data = json.dumps({
            "placements": [placement],
            "displayed_relationships": [],
            "canvas": {"viewport": {"x": 0, "y": 0, "zoom": 1.0}},
        })
        await main_db.execute(
            "INSERT INTO diagrams (id, diagram_type, current_version, created_by) "
            "VALUES ('m1', 'component_diagram', 1, 'user1')"
        )
        await main_db.execute(
            "INSERT INTO diagram_versions "
            "(diagram_id, version, name, data, change_type, created_by) "
            "VALUES ('m1', 1, 'Auth Architecture', ?, 'create', 'user1')",
            (placements_data,),
        )
        await main_db.commit()
        cursor = await main_db.execute(
            "SELECT data FROM diagram_versions WHERE diagram_id='m1'"
        )
        row = await cursor.fetchone()
        parsed = json.loads(row[0])
        assert len(parsed["placements"]) == 1
        assert parsed["placements"][0]["element_id"] == "e1"

    async def test_migration_is_idempotent(self, main_db: aiosqlite.Connection) -> None:
        await _setup_db(main_db)
        await m002_up(main_db)  # Run again
        cursor = await main_db.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='elements'"
        )
        row = await cursor.fetchone()
        assert row[0] == 1
