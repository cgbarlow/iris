"""Migration 019: Add deleted_group_id for recycle bin cascade grouping.

Also updates CHECK constraint on element_versions.change_type to include 'restore'.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


async def up(db: aiosqlite.Connection) -> None:
    """Add deleted_group_id column and update change_type constraints."""
    # 1. Add deleted_group_id column to identity tables
    for table in ("packages", "diagrams", "elements"):
        cursor = await db.execute(f"PRAGMA table_info({table})")  # noqa: S608
        columns = [row[1] for row in await cursor.fetchall()]
        if "deleted_group_id" not in columns:
            await db.execute(
                f"ALTER TABLE {table} ADD COLUMN deleted_group_id TEXT"  # noqa: S608
            )
            await db.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{table}_deleted_group "  # noqa: S608
                f"ON {table}(deleted_group_id) WHERE deleted_group_id IS NOT NULL"
            )

    # 2. Recreate element_versions to update CHECK constraint (add 'restore')
    # The original entity_versions had CHECK(change_type IN ('create','update','rollback','delete'))
    # which was carried over when renamed to element_versions in m016.
    cursor = await db.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='element_versions'"
    )
    row = await cursor.fetchone()
    if row and "'restore'" not in (row[0] or ""):
        await db.execute("ALTER TABLE element_versions RENAME TO _old_element_versions")
        await db.execute("""
            CREATE TABLE element_versions (
                element_id TEXT NOT NULL REFERENCES elements(id),
                version INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                data TEXT NOT NULL,
                metadata TEXT,
                change_type TEXT NOT NULL CHECK (
                    change_type IN ('create', 'update', 'rollback', 'delete', 'restore')
                ),
                change_summary TEXT,
                rollback_to INTEGER,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                created_by TEXT NOT NULL REFERENCES users(id),
                PRIMARY KEY (element_id, version)
            )
        """)
        await db.execute("""
            INSERT INTO element_versions
            SELECT * FROM _old_element_versions
        """)
        await db.execute("DROP TABLE _old_element_versions")
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_element_versions_created_at "
            "ON element_versions(created_at)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_element_versions_created_by "
            "ON element_versions(created_by)"
        )

    # 3. Also update relationship_versions CHECK constraint
    cursor = await db.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='relationship_versions'"
    )
    row = await cursor.fetchone()
    if row and "'restore'" not in (row[0] or ""):
        await db.execute(
            "ALTER TABLE relationship_versions RENAME TO _old_relationship_versions"
        )
        await db.execute("""
            CREATE TABLE relationship_versions (
                relationship_id TEXT NOT NULL REFERENCES relationships(id),
                version INTEGER NOT NULL,
                label TEXT,
                description TEXT,
                data TEXT,
                metadata TEXT,
                change_type TEXT NOT NULL CHECK (
                    change_type IN ('create', 'update', 'rollback', 'delete', 'restore')
                ),
                change_summary TEXT,
                rollback_to INTEGER,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                created_by TEXT NOT NULL REFERENCES users(id),
                PRIMARY KEY (relationship_id, version)
            )
        """)
        await db.execute("""
            INSERT INTO relationship_versions
            SELECT * FROM _old_relationship_versions
        """)
        await db.execute("DROP TABLE _old_relationship_versions")
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_rel_versions_created_at "
            "ON relationship_versions(created_at)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_rel_versions_created_by "
            "ON relationship_versions(created_by)"
        )

    await db.commit()
