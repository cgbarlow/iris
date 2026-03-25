"""Migration 032: Create Scenia-specific tables."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


async def up(db: aiosqlite.Connection) -> None:
    """Create Scenia tables for timeline settings, versions, categories, statuses."""
    # Guard: skip if scenia_timeline_settings already exists
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='scenia_timeline_settings'"
    )
    if await cursor.fetchone():
        return

    await db.execute(
        "CREATE TABLE IF NOT EXISTS scenia_timeline_settings ("
        "  id TEXT PRIMARY KEY,"
        "  set_id TEXT REFERENCES sets(id),"
        "  start_date TEXT,"
        "  end_date TEXT,"
        "  view_mode TEXT DEFAULT 'quarterly',"
        "  zoom_level REAL DEFAULT 1.0,"
        "  data TEXT DEFAULT '{}',"
        "  updated_at TEXT NOT NULL"
        ")"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_scenia_timeline_settings_set_id "
        "ON scenia_timeline_settings(set_id)"
    )

    await db.execute(
        "CREATE TABLE IF NOT EXISTS scenia_versions ("
        "  id TEXT PRIMARY KEY,"
        "  set_id TEXT REFERENCES sets(id),"
        "  version_number INTEGER NOT NULL,"
        "  name TEXT,"
        "  data TEXT DEFAULT '{}',"
        "  created_at TEXT NOT NULL,"
        "  created_by TEXT NOT NULL"
        ")"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_scenia_versions_set_id "
        "ON scenia_versions(set_id)"
    )

    await db.execute(
        "CREATE TABLE IF NOT EXISTS scenia_asset_categories ("
        "  id TEXT PRIMARY KEY,"
        "  set_id TEXT REFERENCES sets(id),"
        "  name TEXT NOT NULL,"
        "  color TEXT,"
        "  display_order INTEGER DEFAULT 0"
        ")"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_scenia_asset_categories_set_id "
        "ON scenia_asset_categories(set_id)"
    )

    await db.execute(
        "CREATE TABLE IF NOT EXISTS scenia_application_statuses ("
        "  id TEXT PRIMARY KEY,"
        "  set_id TEXT REFERENCES sets(id),"
        "  name TEXT NOT NULL,"
        "  color TEXT,"
        "  display_order INTEGER DEFAULT 0"
        ")"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_scenia_application_statuses_set_id "
        "ON scenia_application_statuses(set_id)"
    )

    await db.commit()
