"""Migration 082: Per-user collection write-scope (ADR-237).

Adds the ``user_collection_scope`` junction table. A row ``(user_id,
collection_id)`` whitelists a collection the user may **write** in. A user with
NO rows is *unscoped* — their role's write permissions apply everywhere (the
pre-ADR-237 behaviour). Read access is unchanged (anonymous reads, ADR-123).

Assignment is managed directly in Supabase (the admin inserts rows in the
dashboard); Iris only reads + enforces. Mirrored by Supabase ``m088``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m082_user_collection_scope"


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up. Idempotent."""
    await db.execute(
        "CREATE TABLE IF NOT EXISTS user_collection_scope ("
        "user_id TEXT NOT NULL REFERENCES users(id), "
        "collection_id TEXT NOT NULL REFERENCES collections(id), "
        "created_at TEXT NOT NULL DEFAULT (datetime('now')), "
        "PRIMARY KEY (user_id, collection_id)"
        ")"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_ucs_user "
        "ON user_collection_scope(user_id)"
    )
    await db.commit()
