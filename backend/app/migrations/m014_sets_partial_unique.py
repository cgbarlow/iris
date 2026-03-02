"""Migration 014: Replace full UNIQUE on sets.name with partial unique index for active rows.

Per ADR-063 (Pagination, Set Uniqueness, Tree Explorer).

Allows soft-deleted sets to release their names for reuse while preventing
duplicate names among active (non-deleted) sets.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


async def up(db: aiosqlite.Connection) -> None:
    """Recreate sets table without UNIQUE on name, add partial unique index."""
    # Idempotent guard: if the partial unique index already exists, skip
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_sets_name_active'"
    )
    if await cursor.fetchone():
        return

    # 1. Create new table without UNIQUE on name
    await db.execute(
        "CREATE TABLE sets_new ("
        "  id TEXT PRIMARY KEY,"
        "  name TEXT NOT NULL,"
        "  description TEXT,"
        "  created_at TEXT NOT NULL,"
        "  created_by TEXT NOT NULL,"
        "  updated_at TEXT NOT NULL,"
        "  is_deleted INTEGER NOT NULL DEFAULT 0,"
        "  thumbnail_source TEXT,"
        "  thumbnail_model_id TEXT REFERENCES models(id),"
        "  thumbnail_image BLOB"
        ")"
    )

    # 2. Copy all data
    await db.execute(
        "INSERT INTO sets_new "
        "(id, name, description, created_at, created_by, updated_at, "
        " is_deleted, thumbnail_source, thumbnail_model_id, thumbnail_image) "
        "SELECT id, name, description, created_at, created_by, updated_at, "
        "       is_deleted, thumbnail_source, thumbnail_model_id, thumbnail_image "
        "FROM sets"
    )

    # 3. Drop old table
    await db.execute("DROP TABLE sets")

    # 4. Rename new table
    await db.execute("ALTER TABLE sets_new RENAME TO sets")

    # 5. Recreate regular index on name
    await db.execute("CREATE INDEX idx_sets_name ON sets(name)")

    # 6. Create partial unique index — only enforced for active (non-deleted) rows
    await db.execute(
        "CREATE UNIQUE INDEX idx_sets_name_active ON sets(name) WHERE is_deleted = 0"
    )

    await db.commit()
