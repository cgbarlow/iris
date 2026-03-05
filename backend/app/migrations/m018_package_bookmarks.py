"""Migration 018: Extend bookmarks to support packages.

Adds package_id column alongside existing diagram_id.
Replaces composite PK with a rowid-based table since either
diagram_id or package_id can be NULL.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m018_package_bookmarks"


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up."""
    # Check if package_id column already exists
    cursor = await db.execute("PRAGMA table_info(bookmarks)")
    columns = [row[1] for row in await cursor.fetchall()]
    if "package_id" in columns:
        return

    # Recreate bookmarks table with package_id support
    await db.execute("""
        CREATE TABLE IF NOT EXISTS bookmarks_new (
            user_id TEXT NOT NULL REFERENCES users(id),
            diagram_id TEXT REFERENCES diagrams(id),
            package_id TEXT REFERENCES packages(id),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            CHECK (
                (diagram_id IS NOT NULL AND package_id IS NULL)
                OR (diagram_id IS NULL AND package_id IS NOT NULL)
            ),
            UNIQUE (user_id, diagram_id),
            UNIQUE (user_id, package_id)
        )
    """)
    await db.execute("""
        INSERT OR IGNORE INTO bookmarks_new (user_id, diagram_id, created_at)
        SELECT user_id, diagram_id, created_at FROM bookmarks
    """)
    await db.execute("DROP TABLE bookmarks")
    await db.execute("ALTER TABLE bookmarks_new RENAME TO bookmarks")
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_bookmarks_diagram ON bookmarks(diagram_id)"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_bookmarks_package ON bookmarks(package_id)"
    )
    await db.commit()
