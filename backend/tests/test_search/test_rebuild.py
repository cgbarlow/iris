"""Tests for FTS search index rebuild and rollback re-indexing.

Verifies SPEC-016-A: rebuild_search_index() populates FTS tables from
existing data, is idempotent, excludes deleted records, and rollback
operations update the FTS index.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from app.migrations.m001_roles_users import up as m001_up
from app.migrations.m002_entities_relationships_models import up as m002_up
from app.migrations.m005_search import up as m005_up
from app.migrations.seed import seed_roles_and_permissions
from app.search.service import rebuild_search_index, search

if TYPE_CHECKING:
    import aiosqlite


async def _run_migrations(db: aiosqlite.Connection) -> None:
    """Run all required migrations for search tests."""
    await m001_up(db)
    await m002_up(db)
    await m005_up(db)
    await seed_roles_and_permissions(db)


async def _create_test_user(db: aiosqlite.Connection) -> str:
    """Insert a minimal test user and return the user id."""
    user_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO users (id, username, password_hash, role) VALUES (?, ?, ?, ?)",
        (user_id, f"testuser-{user_id[:8]}", "fakehash", "admin"),
    )
    await db.commit()
    return user_id


async def _insert_entity_directly(
    db: aiosqlite.Connection,
    *,
    user_id: str,
    name: str,
    entity_type: str = "application",
    description: str | None = None,
    is_deleted: int = 0,
) -> str:
    """Insert an entity and version directly into the DB (bypassing service layer)."""
    entity_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()
    await db.execute(
        "INSERT INTO entities (id, entity_type, current_version, "
        "created_at, created_by, updated_at, is_deleted) "
        "VALUES (?, ?, 1, ?, ?, ?, ?)",
        (entity_id, entity_type, now, user_id, now, is_deleted),
    )
    await db.execute(
        "INSERT INTO entity_versions (entity_id, version, name, description, "
        "data, change_type, created_at, created_by) "
        "VALUES (?, 1, ?, ?, ?, 'create', ?, ?)",
        (entity_id, name, description, json.dumps({}), now, user_id),
    )
    await db.commit()
    return entity_id


async def _insert_model_directly(
    db: aiosqlite.Connection,
    *,
    user_id: str,
    name: str,
    model_type: str = "simple",
    description: str | None = None,
    is_deleted: int = 0,
) -> str:
    """Insert a model and version directly into the DB (bypassing service layer)."""
    model_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()
    await db.execute(
        "INSERT INTO models (id, model_type, current_version, "
        "created_at, created_by, updated_at, is_deleted) "
        "VALUES (?, ?, 1, ?, ?, ?, ?)",
        (model_id, model_type, now, user_id, now, is_deleted),
    )
    await db.execute(
        "INSERT INTO model_versions (model_id, version, name, description, "
        "data, change_type, created_at, created_by) "
        "VALUES (?, 1, ?, ?, ?, 'create', ?, ?)",
        (model_id, name, description, json.dumps({}), now, user_id),
    )
    await db.commit()
    return model_id


class TestRebuildSearchIndex:
    """Verify rebuild_search_index() populates FTS tables correctly."""

    async def test_rebuild_indexes_existing_entities(
        self, main_db: aiosqlite.Connection,
    ) -> None:
        await _run_migrations(main_db)
        user_id = await _create_test_user(main_db)

        await _insert_entity_directly(
            main_db, user_id=user_id,
            name="Payment Gateway", entity_type="application",
            description="Processes payments",
        )

        results = await search(main_db, "Payment")
        assert len(results) == 0

        await rebuild_search_index(main_db)
        results = await search(main_db, "Payment")
        assert len(results) == 1
        assert results[0]["name"] == "Payment Gateway"
        assert results[0]["result_type"] == "entity"

    async def test_rebuild_indexes_existing_models(
        self, main_db: aiosqlite.Connection,
    ) -> None:
        await _run_migrations(main_db)
        user_id = await _create_test_user(main_db)

        await _insert_model_directly(
            main_db, user_id=user_id,
            name="Network Topology", model_type="simple",
            description="Core network layout",
        )

        results = await search(main_db, "Network")
        assert len(results) == 0

        await rebuild_search_index(main_db)
        results = await search(main_db, "Network")
        assert len(results) == 1
        assert results[0]["name"] == "Network Topology"
        assert results[0]["result_type"] == "model"

    async def test_rebuild_is_idempotent(
        self, main_db: aiosqlite.Connection,
    ) -> None:
        await _run_migrations(main_db)
        user_id = await _create_test_user(main_db)

        await _insert_entity_directly(
            main_db, user_id=user_id,
            name="Auth Service", entity_type="application",
        )
        await _insert_model_directly(
            main_db, user_id=user_id,
            name="Auth Model", model_type="simple",
        )

        await rebuild_search_index(main_db)
        await rebuild_search_index(main_db)

        entity_results = await search(main_db, "Auth Service")
        model_results = await search(main_db, "Auth Model")
        assert len(entity_results) == 1
        assert len(model_results) == 1

    async def test_rebuild_excludes_deleted(
        self, main_db: aiosqlite.Connection,
    ) -> None:
        await _run_migrations(main_db)
        user_id = await _create_test_user(main_db)

        await _insert_entity_directly(
            main_db, user_id=user_id,
            name="Deleted Service", entity_type="application",
            is_deleted=1,
        )
        await _insert_entity_directly(
            main_db, user_id=user_id,
            name="Live Service", entity_type="application",
        )

        await rebuild_search_index(main_db)

        deleted_results = await search(main_db, "Deleted Service")
        assert len(deleted_results) == 0

        live_results = await search(main_db, "Live Service")
        assert len(live_results) == 1

    async def test_rollback_updates_fts_index(
        self, main_db: aiosqlite.Connection,
    ) -> None:
        """After rollback, FTS should contain the rolled-back version's name."""
        from app.entities.service import (
            create_entity,
            rollback_entity,
            update_entity,
        )

        await _run_migrations(main_db)
        user_id = await _create_test_user(main_db)

        entity = await create_entity(
            main_db,
            entity_type="application",
            name="Original Name",
            description="Original description",
            data={},
            created_by=user_id,
        )
        entity_id: str = entity["id"]  # type: ignore[assignment]

        await update_entity(
            main_db, entity_id,
            name="Updated Name",
            description="Updated description",
            data={},
            change_summary="Changed name",
            updated_by=user_id,
            expected_version=1,
        )

        results = await search(main_db, "Updated Name")
        assert len(results) == 1

        await rollback_entity(
            main_db, entity_id,
            target_version=1,
            rolled_back_by=user_id,
            expected_version=2,
        )

        original_results = await search(main_db, "Original Name")
        assert len(original_results) == 1
        assert original_results[0]["name"] == "Original Name"

        updated_results = await search(main_db, "Updated Name")
        assert len(updated_results) == 0
