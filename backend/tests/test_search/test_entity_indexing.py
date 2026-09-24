"""Tests for element search indexing during CRUD operations.

Verifies SPEC-033-A: Elements are indexed in FTS immediately when created,
updated, or deleted via the service layer -- without requiring a full
rebuild_search_index() call.

This covers the incremental indexing gap: elements created after application
startup must be searchable immediately, and updates/deletes must be reflected
in search results without restart.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from app.elements.service import (
    create_element,
    soft_delete_element,
    update_element,
)
from app.migrations.seed import seed_roles_and_permissions
from app.search.service import search
from app.startup import run_sqlite_main_migrations

if TYPE_CHECKING:
    import aiosqlite


async def _run_migrations(db: aiosqlite.Connection) -> None:
    """Run all required migrations for search tests."""
    await run_sqlite_main_migrations(db)
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


class TestElementCrudIndexing:
    """Verify elements are indexed immediately during CRUD operations."""

    async def test_create_element_indexes_for_search(
        self, main_db: aiosqlite.Connection,
    ) -> None:
        """Creating an element via the service layer makes it immediately searchable."""
        await _run_migrations(main_db)
        user_id = await _create_test_user(main_db)

        # Create element via service (not direct SQL insert)
        await create_element(
            main_db,
            element_type="application",
            name="Inventory Tracker",
            description="Tracks warehouse inventory levels",
            data={},
            created_by=user_id,
        )

        # Should be searchable immediately by name
        results = await search(main_db, "Inventory")
        assert len(results) == 1
        assert results[0]["name"] == "Inventory Tracker"
        assert results[0]["result_type"] == "element"
        assert results[0]["type_detail"] == "application"

    async def test_create_element_searchable_by_description(
        self, main_db: aiosqlite.Connection,
    ) -> None:
        """Element description is searchable immediately after creation."""
        await _run_migrations(main_db)
        user_id = await _create_test_user(main_db)

        await create_element(
            main_db,
            element_type="database",
            name="Central DB",
            description="Stores financial transaction records",
            data={},
            created_by=user_id,
        )

        results = await search(main_db, "financial transaction")
        assert len(results) == 1
        assert results[0]["name"] == "Central DB"

    async def test_update_element_updates_search_index(
        self, main_db: aiosqlite.Connection,
    ) -> None:
        """Updating an element name updates the search index immediately."""
        await _run_migrations(main_db)
        user_id = await _create_test_user(main_db)

        element = await create_element(
            main_db,
            element_type="service",
            name="Alpha Service",
            description="Original service",
            data={},
            created_by=user_id,
        )
        element_id: str = element["id"]  # type: ignore[assignment]

        # Verify original name is searchable
        results = await search(main_db, "Alpha Service")
        assert len(results) == 1

        # Update the name
        await update_element(
            main_db,
            element_id,
            name="Beta Service",
            description="Renamed service",
            data={},
            change_summary="Renamed from Alpha to Beta",
            updated_by=user_id,
            expected_version=1,
        )

        # New name should be searchable
        new_results = await search(main_db, "Beta Service")
        assert len(new_results) == 1
        assert new_results[0]["name"] == "Beta Service"

        # Old name should NOT be searchable
        old_results = await search(main_db, "Alpha Service")
        assert len(old_results) == 0

    async def test_delete_element_removes_from_search_index(
        self, main_db: aiosqlite.Connection,
    ) -> None:
        """Soft-deleting an element removes it from the search index."""
        await _run_migrations(main_db)
        user_id = await _create_test_user(main_db)

        element = await create_element(
            main_db,
            element_type="application",
            name="Temporary Widget",
            description="Will be deleted",
            data={},
            created_by=user_id,
        )
        element_id: str = element["id"]  # type: ignore[assignment]

        # Verify it's searchable
        results = await search(main_db, "Temporary Widget")
        assert len(results) == 1

        # Delete it
        deleted = await soft_delete_element(
            main_db,
            element_id,
            deleted_by=user_id,
            expected_version=1,
        )
        assert deleted is True

        # Should no longer be searchable
        results_after = await search(main_db, "Temporary Widget")
        assert len(results_after) == 0

    async def test_multiple_elements_all_searchable(
        self, main_db: aiosqlite.Connection,
    ) -> None:
        """Multiple elements created via the service are all searchable."""
        await _run_migrations(main_db)
        user_id = await _create_test_user(main_db)

        names = [
            "Procurement Portal",
            "Procurement Database",
            "Procurement API Gateway",
        ]
        for name in names:
            await create_element(
                main_db,
                element_type="application",
                name=name,
                description=None,
                data={},
                created_by=user_id,
            )

        results = await search(main_db, "Procurement")
        assert len(results) == 3
        result_names = {r["name"] for r in results}
        assert result_names == set(names)

    async def test_element_deep_link_format(
        self, main_db: aiosqlite.Connection,
    ) -> None:
        """Search results for elements include correct deep_link format."""
        await _run_migrations(main_db)
        user_id = await _create_test_user(main_db)

        element = await create_element(
            main_db,
            element_type="application",
            name="Deep Link Test Element",
            description=None,
            data={},
            created_by=user_id,
        )
        element_id: str = element["id"]  # type: ignore[assignment]

        results = await search(main_db, "Deep Link Test")
        assert len(results) == 1
        assert results[0]["deep_link"] == f"/elements/{element_id}"
