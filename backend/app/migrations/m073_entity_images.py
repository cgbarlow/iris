"""Migration 073: entity_images junction table (ADR-209, v6.17.0).

Lets any collection / set / package / diagram / element have zero or
more attached images, reusing the existing ``images`` table for the
bytes (one image_id can reference multiple entities).

Idempotent (``CREATE TABLE IF NOT EXISTS`` + ``CREATE INDEX IF NOT
EXISTS``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m073_entity_images"


async def up(db: aiosqlite.Connection) -> None:
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS entity_images (
            id            TEXT PRIMARY KEY,
            entity_type   TEXT NOT NULL,
            entity_id     TEXT NOT NULL,
            image_id      TEXT NOT NULL,
            display_order INTEGER NOT NULL DEFAULT 0,
            created_at    TEXT NOT NULL,
            created_by    TEXT NOT NULL,
            UNIQUE (entity_type, entity_id, image_id)
        )
        """,
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_entity_images_entity "
        "ON entity_images (entity_type, entity_id, display_order)",
    )
    await db.commit()
