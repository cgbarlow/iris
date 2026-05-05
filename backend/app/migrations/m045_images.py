"""Migration 045: Images (ADR-145, SPEC-145-A) — v5.4.0.

Adds the `images` table that backs paste-image-from-clipboard in the
markdown editor. Stores the bytes inline (BLOB) for SQLite parity with
the Supabase BYTEA column.

Limits enforced at the service layer (5 MB max, MIME ∈ {png, jpeg, gif,
webp}) — matched in m046_images.sql.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m045_images"


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up."""
    cursor = await db.execute(
        "SELECT name FROM sqlite_master"
        " WHERE type='table' AND name='images'"
    )
    if await cursor.fetchone():
        return

    await db.execute(
        "CREATE TABLE images ("
        "  id TEXT PRIMARY KEY,"
        "  mime TEXT NOT NULL,"
        "  bytes BLOB NOT NULL,"
        "  size_bytes INTEGER NOT NULL,"
        "  uploaded_by TEXT,"
        "  created_at TEXT NOT NULL"
        ")"
    )
    await db.execute(
        "CREATE INDEX idx_images_uploaded_by ON images(uploaded_by)"
    )
    await db.commit()
