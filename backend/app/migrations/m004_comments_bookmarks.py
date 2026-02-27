"""Migration 004: Comments and bookmarks tables per SPEC-003-A."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m004_comments_bookmarks"

UP_SQL = """
-- Comments table
CREATE TABLE IF NOT EXISTS comments (
    id TEXT PRIMARY KEY,
    target_type TEXT NOT NULL CHECK (target_type IN ('entity', 'model')),
    target_id TEXT NOT NULL,
    user_id TEXT NOT NULL REFERENCES users(id),
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    is_deleted INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_comments_target
    ON comments(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_comments_user ON comments(user_id);
CREATE INDEX IF NOT EXISTS idx_comments_created_at ON comments(created_at);

-- Bookmarks table (per-user model bookmarks)
CREATE TABLE IF NOT EXISTS bookmarks (
    user_id TEXT NOT NULL REFERENCES users(id),
    model_id TEXT NOT NULL REFERENCES models(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, model_id)
);

CREATE INDEX IF NOT EXISTS idx_bookmarks_model ON bookmarks(model_id);
"""


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up."""
    await db.executescript(UP_SQL)
    await db.commit()
