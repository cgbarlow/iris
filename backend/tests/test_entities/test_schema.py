"""Tests for Migration 002: entities, relationships, models and their version tables."""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING

import pytest

from app.migrations.m001_roles_users import up as m001_up
from app.migrations.m002_entities_relationships_models import up as m002_up

if TYPE_CHECKING:
    import aiosqlite


async def _setup_db(db: aiosqlite.Connection) -> None:
    """Run prerequisite migrations and seed a test user."""
    await m001_up(db)
    await m002_up(db)
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

    async def test_entities_table_exists(self, main_db: aiosqlite.Connection) -> None:
        await _setup_db(main_db)
        cursor = await main_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='entities'"
        )
        assert await cursor.fetchone() is not None

    async def test_entity_versions_table_exists(self, main_db: aiosqlite.Connection) -> None:
        await _setup_db(main_db)
        cursor = await main_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='entity_versions'"
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

    async def test_models_table_exists(self, main_db: aiosqlite.Connection) -> None:
        await _setup_db(main_db)
        cursor = await main_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='models'"
        )
        assert await cursor.fetchone() is not None

    async def test_model_versions_table_exists(self, main_db: aiosqlite.Connection) -> None:
        await _setup_db(main_db)
        cursor = await main_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='model_versions'"
        )
        assert await cursor.fetchone() is not None


class TestEntityVersioning:
    """Verify entity versioning schema constraints."""

    async def test_create_entity_with_version(self, main_db: aiosqlite.Connection) -> None:
        await _setup_db(main_db)
        await main_db.execute(
            "INSERT INTO entities (id, entity_type, current_version, created_by) "
            "VALUES ('e1', 'component', 1, 'user1')"
        )
        await main_db.execute(
            "INSERT INTO entity_versions "
            "(entity_id, version, name, description, data, change_type, created_by) "
            "VALUES ('e1', 1, 'Auth Service', 'Handles auth', '{}', 'create', 'user1')"
        )
        await main_db.commit()
        cursor = await main_db.execute("SELECT name FROM entity_versions WHERE entity_id='e1'")
        row = await cursor.fetchone()
        assert row[0] == "Auth Service"

    async def test_change_type_check_constraint(self, main_db: aiosqlite.Connection) -> None:
        await _setup_db(main_db)
        await main_db.execute(
            "INSERT INTO entities (id, entity_type, current_version, created_by) "
            "VALUES ('e1', 'component', 1, 'user1')"
        )
        with pytest.raises(sqlite3.IntegrityError):
            await main_db.execute(
                "INSERT INTO entity_versions "
                "(entity_id, version, name, data, change_type, created_by) "
                "VALUES ('e1', 1, 'Test', '{}', 'invalid_type', 'user1')"
            )

    async def test_entity_version_composite_key(self, main_db: aiosqlite.Connection) -> None:
        await _setup_db(main_db)
        await main_db.execute(
            "INSERT INTO entities (id, entity_type, current_version, created_by) "
            "VALUES ('e1', 'component', 2, 'user1')"
        )
        await main_db.execute(
            "INSERT INTO entity_versions "
            "(entity_id, version, name, data, change_type, created_by) "
            "VALUES ('e1', 1, 'V1', '{}', 'create', 'user1')"
        )
        await main_db.execute(
            "INSERT INTO entity_versions "
            "(entity_id, version, name, data, change_type, created_by) "
            "VALUES ('e1', 2, 'V2', '{}', 'update', 'user1')"
        )
        await main_db.commit()
        cursor = await main_db.execute(
            "SELECT COUNT(*) FROM entity_versions WHERE entity_id='e1'"
        )
        row = await cursor.fetchone()
        assert row[0] == 2


class TestRelationshipSchema:
    """Verify relationship tables and indexes."""

    async def test_create_relationship(self, main_db: aiosqlite.Connection) -> None:
        await _setup_db(main_db)
        # Create two entities first
        for eid in ("e1", "e2"):
            await main_db.execute(
                "INSERT INTO entities (id, entity_type, current_version, created_by) "
                "VALUES (?, 'component', 1, 'user1')",
                (eid,),
            )
            await main_db.execute(
                "INSERT INTO entity_versions "
                "(entity_id, version, name, data, change_type, created_by) "
                "VALUES (?, 1, ?, '{}', 'create', 'user1')",
                (eid, f"Entity {eid}"),
            )
        await main_db.execute(
            "INSERT INTO relationships "
            "(id, source_entity_id, target_entity_id, relationship_type, "
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


class TestModelSchema:
    """Verify model tables with denormalized placements."""

    async def test_create_model_with_placements(self, main_db: aiosqlite.Connection) -> None:
        await _setup_db(main_db)
        placement = {
            "entity_id": "e1",
            "position": {"x": 100, "y": 200},
            "size": {"width": 180, "height": 80},
        }
        placements_data = json.dumps({
            "placements": [placement],
            "displayed_relationships": [],
            "canvas": {"viewport": {"x": 0, "y": 0, "zoom": 1.0}},
        })
        await main_db.execute(
            "INSERT INTO models (id, model_type, current_version, created_by) "
            "VALUES ('m1', 'component_diagram', 1, 'user1')"
        )
        await main_db.execute(
            "INSERT INTO model_versions "
            "(model_id, version, name, data, change_type, created_by) "
            "VALUES ('m1', 1, 'Auth Architecture', ?, 'create', 'user1')",
            (placements_data,),
        )
        await main_db.commit()
        cursor = await main_db.execute(
            "SELECT data FROM model_versions WHERE model_id='m1'"
        )
        row = await cursor.fetchone()
        parsed = json.loads(row[0])
        assert len(parsed["placements"]) == 1
        assert parsed["placements"][0]["entity_id"] == "e1"

    async def test_migration_is_idempotent(self, main_db: aiosqlite.Connection) -> None:
        await _setup_db(main_db)
        await m002_up(main_db)  # Run again
        cursor = await main_db.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='entities'"
        )
        row = await cursor.fetchone()
        assert row[0] == 1
