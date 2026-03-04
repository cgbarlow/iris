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
from app.migrations.m004_comments_bookmarks import up as m004_up
from app.migrations.m005_search import up as m005_up
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
from app.migrations.seed import seed_roles_and_permissions
from app.search.service import rebuild_search_index, search

if TYPE_CHECKING:
    import aiosqlite


async def _run_migrations(db: aiosqlite.Connection) -> None:
    """Run all required migrations for search tests."""
    await m001_up(db)
    await m002_up(db)
    await m004_up(db)
    await m005_up(db)
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


async def _insert_element_directly(
    db: aiosqlite.Connection,
    *,
    user_id: str,
    name: str,
    element_type: str = "application",
    description: str | None = None,
    is_deleted: int = 0,
) -> str:
    """Insert an element and version directly into the DB (bypassing service layer)."""
    element_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()
    await db.execute(
        "INSERT INTO elements (id, element_type, current_version, "
        "created_at, created_by, updated_at, is_deleted) "
        "VALUES (?, ?, 1, ?, ?, ?, ?)",
        (element_id, element_type, now, user_id, now, is_deleted),
    )
    await db.execute(
        "INSERT INTO element_versions (element_id, version, name, description, "
        "data, change_type, created_at, created_by) "
        "VALUES (?, 1, ?, ?, ?, 'create', ?, ?)",
        (element_id, name, description, json.dumps({}), now, user_id),
    )
    await db.commit()
    return element_id


async def _insert_diagram_directly(
    db: aiosqlite.Connection,
    *,
    user_id: str,
    name: str,
    diagram_type: str = "simple",
    description: str | None = None,
    is_deleted: int = 0,
) -> str:
    """Insert a diagram and version directly into the DB (bypassing service layer)."""
    diagram_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()
    await db.execute(
        "INSERT INTO diagrams (id, diagram_type, current_version, "
        "created_at, created_by, updated_at, is_deleted) "
        "VALUES (?, ?, 1, ?, ?, ?, ?)",
        (diagram_id, diagram_type, now, user_id, now, is_deleted),
    )
    await db.execute(
        "INSERT INTO diagram_versions (diagram_id, version, name, description, "
        "data, change_type, created_at, created_by) "
        "VALUES (?, 1, ?, ?, ?, 'create', ?, ?)",
        (diagram_id, name, description, json.dumps({}), now, user_id),
    )
    await db.commit()
    return diagram_id


class TestRebuildSearchIndex:
    """Verify rebuild_search_index() populates FTS tables correctly."""

    async def test_rebuild_indexes_existing_elements(
        self, main_db: aiosqlite.Connection,
    ) -> None:
        await _run_migrations(main_db)
        user_id = await _create_test_user(main_db)

        await _insert_element_directly(
            main_db, user_id=user_id,
            name="Payment Gateway", element_type="application",
            description="Processes payments",
        )

        results = await search(main_db, "Payment")
        assert len(results) == 0

        await rebuild_search_index(main_db)
        results = await search(main_db, "Payment")
        assert len(results) == 1
        assert results[0]["name"] == "Payment Gateway"
        assert results[0]["result_type"] == "element"

    async def test_rebuild_indexes_existing_diagrams(
        self, main_db: aiosqlite.Connection,
    ) -> None:
        await _run_migrations(main_db)
        user_id = await _create_test_user(main_db)

        await _insert_diagram_directly(
            main_db, user_id=user_id,
            name="Network Topology", diagram_type="simple",
            description="Core network layout",
        )

        results = await search(main_db, "Network")
        assert len(results) == 0

        await rebuild_search_index(main_db)
        results = await search(main_db, "Network")
        assert len(results) == 1
        assert results[0]["name"] == "Network Topology"
        assert results[0]["result_type"] == "diagram"

    async def test_rebuild_is_idempotent(
        self, main_db: aiosqlite.Connection,
    ) -> None:
        await _run_migrations(main_db)
        user_id = await _create_test_user(main_db)

        await _insert_element_directly(
            main_db, user_id=user_id,
            name="Auth Service", element_type="application",
        )
        await _insert_diagram_directly(
            main_db, user_id=user_id,
            name="Auth Diagram", diagram_type="simple",
        )

        await rebuild_search_index(main_db)
        await rebuild_search_index(main_db)

        element_results = await search(main_db, "Auth Service")
        diagram_results = await search(main_db, "Auth Diagram")
        assert len(element_results) == 1
        assert len(diagram_results) == 1

    async def test_rebuild_excludes_deleted(
        self, main_db: aiosqlite.Connection,
    ) -> None:
        await _run_migrations(main_db)
        user_id = await _create_test_user(main_db)

        await _insert_element_directly(
            main_db, user_id=user_id,
            name="Deleted Service", element_type="application",
            is_deleted=1,
        )
        await _insert_element_directly(
            main_db, user_id=user_id,
            name="Live Service", element_type="application",
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
        from app.elements.service import (
            create_element,
            rollback_element,
            update_element,
        )

        await _run_migrations(main_db)
        user_id = await _create_test_user(main_db)

        element = await create_element(
            main_db,
            element_type="application",
            name="Original Name",
            description="Original description",
            data={},
            created_by=user_id,
        )
        element_id: str = element["id"]  # type: ignore[assignment]

        await update_element(
            main_db, element_id,
            name="Updated Name",
            description="Updated description",
            data={},
            change_summary="Changed name",
            updated_by=user_id,
            expected_version=1,
        )

        results = await search(main_db, "Updated Name")
        assert len(results) == 1

        await rollback_element(
            main_db, element_id,
            target_version=1,
            rolled_back_by=user_id,
            expected_version=2,
        )

        original_results = await search(main_db, "Original Name")
        assert len(original_results) == 1
        assert original_results[0]["name"] == "Original Name"

        updated_results = await search(main_db, "Updated Name")
        assert len(updated_results) == 0
