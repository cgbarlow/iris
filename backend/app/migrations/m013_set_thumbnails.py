"""Migration 013: Add thumbnail columns to sets table.

Supports set thumbnails sourced from a model's existing thumbnail
or a user-uploaded image.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


async def up(db: aiosqlite.Connection) -> None:
    """Add thumbnail_source, thumbnail_model_id, and thumbnail_image to sets."""
    # Guard: skip if m016 naming rename has already been applied
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='elements'"
    )
    if await cursor.fetchone():
        return

    cursor = await db.execute("PRAGMA table_info(sets)")
    columns = [row[1] for row in await cursor.fetchall()]

    if "thumbnail_source" not in columns:
        await db.execute(
            "ALTER TABLE sets ADD COLUMN thumbnail_source TEXT"
        )

    if "thumbnail_model_id" not in columns:
        await db.execute(
            "ALTER TABLE sets ADD COLUMN thumbnail_model_id TEXT REFERENCES models(id)"
        )

    if "thumbnail_image" not in columns:
        await db.execute(
            "ALTER TABLE sets ADD COLUMN thumbnail_image BLOB"
        )

    await db.commit()
