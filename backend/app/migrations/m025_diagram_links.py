"""Migration 025: Create diagram_links table for NavigationCell diagram references."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


async def up(db: aiosqlite.Connection) -> None:
    """Create diagram_links table for storing diagram-to-diagram navigation links."""
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='diagram_links'"
    )
    if await cursor.fetchone():
        return

    await db.execute("""
        CREATE TABLE diagram_links (
            id TEXT PRIMARY KEY,
            source_diagram_id TEXT NOT NULL REFERENCES diagrams(id) ON DELETE CASCADE,
            target_diagram_id TEXT NOT NULL REFERENCES diagrams(id) ON DELETE CASCADE,
            link_type TEXT NOT NULL DEFAULT 'navigation',
            label TEXT,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(source_diagram_id, target_diagram_id, link_type)
        )
    """)
    await db.execute(
        "CREATE INDEX idx_diagram_links_source ON diagram_links(source_diagram_id)"
    )
    await db.execute(
        "CREATE INDEX idx_diagram_links_target ON diagram_links(target_diagram_id)"
    )
    await db.commit()
