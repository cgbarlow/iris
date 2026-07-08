"""Migration 083: content-hash guard for thumbnail regeneration (ADR-242).

Adds a nullable ``content_hash`` column to ``diagram_thumbnails`` so startup
regeneration can skip the cairosvg render and the DB write for any
``(diagram_id, theme)`` whose rendered SVG is unchanged. Eliminates the
~56 MB-per-boot Supabase egress the free-tier ``iris-api`` was paying on every
restart. No back-fill — pre-existing rows keep ``content_hash = NULL`` and
regenerate exactly once (hash mismatch), which populates the column.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m083_thumbnail_content_hash"


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up. Idempotent."""
    cursor = await db.execute("PRAGMA table_info(diagram_thumbnails)")
    cols = {row[1] for row in await cursor.fetchall()}
    if "content_hash" not in cols:
        await db.execute(
            "ALTER TABLE diagram_thumbnails ADD COLUMN content_hash TEXT"
        )
    await db.commit()
