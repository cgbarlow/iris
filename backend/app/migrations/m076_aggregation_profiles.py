"""Migration 076: ``aggregation_profiles`` table (ADR-212, issue #211).

Generic library of aggregation rulesets. Profiles drive the
aggregation engine (``backend/app/aggregation/``) — same shape as
element_templates for scope semantics (is_global ↔ set_id).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m076_aggregation_profiles"


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up. Idempotent — CREATE TABLE IF NOT EXISTS."""
    await db.execute("""
        CREATE TABLE IF NOT EXISTS aggregation_profiles (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            set_id TEXT REFERENCES sets(id),
            is_global INTEGER NOT NULL DEFAULT 0,
            profile_data TEXT NOT NULL,
            is_default_for_set INTEGER NOT NULL DEFAULT 0,
            created_by TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            is_deleted INTEGER NOT NULL DEFAULT 0,
            CHECK ((is_global = 1 AND set_id IS NULL)
                OR (is_global = 0 AND set_id IS NOT NULL))
        )
    """)
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_agg_profiles_set "
        "ON aggregation_profiles(set_id) WHERE is_deleted = 0",
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_agg_profiles_global "
        "ON aggregation_profiles(is_global) WHERE is_deleted = 0",
    )
    await db.commit()
