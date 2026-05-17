"""Migration 067: Element Templates table (ADR-191, issue #153).

Captures a snapshot of selected fields from an existing element so
later element creation can be pre-filled from the template. Templates
are set-scoped by default with an optional ``is_global`` promotion
flag; the CHECK constraint enforces scoping consistency.

No back-fill — existing elements never appear in this table; users
must explicitly create templates from them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m067_element_templates"


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up. Idempotent — CREATE TABLE IF NOT EXISTS."""
    await db.execute("""
        CREATE TABLE IF NOT EXISTS element_templates (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            set_id TEXT REFERENCES sets(id),
            is_global INTEGER NOT NULL DEFAULT 0,
            source_element_id TEXT REFERENCES elements(id),
            included_fields TEXT NOT NULL,
            template_data TEXT NOT NULL,
            created_by TEXT REFERENCES users(id),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            is_deleted INTEGER NOT NULL DEFAULT 0,
            CHECK (
                (is_global = 1 AND set_id IS NULL) OR
                (is_global = 0 AND set_id IS NOT NULL)
            )
        )
    """)
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_element_templates_set "
        "ON element_templates(set_id) WHERE is_deleted = 0"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_element_templates_global "
        "ON element_templates(is_global) WHERE is_global = 1 AND is_deleted = 0"
    )
    await db.commit()
