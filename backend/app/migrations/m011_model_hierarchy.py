"""Migration 011: Add parent_model_id to models for hierarchy support.

Per ADR-055 (Model Hierarchy).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


async def up(db: aiosqlite.Connection) -> None:
    """Add parent_model_id column and index to models table."""
    # Guard: skip if m016 naming rename has already been applied
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='elements'"
    )
    if await cursor.fetchone():
        return

    cursor = await db.execute("PRAGMA table_info(models)")
    columns = [row[1] for row in await cursor.fetchall()]
    if "parent_model_id" in columns:
        return

    await db.execute(
        "ALTER TABLE models ADD COLUMN parent_model_id TEXT REFERENCES models(id)"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_models_parent ON models(parent_model_id)"
    )
    await db.commit()
