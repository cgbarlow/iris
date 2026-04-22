"""Migration 040: Personal Access Tokens (ADR-127, SPEC-127-A).

Adds the `personal_access_tokens` table used by iris-cli, iris-mcp, and
agent callers for long-lived authentication. Secrets are stored as
Argon2id hashes; only the prefix is indexed for lookup.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m040_personal_access_tokens"


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up."""
    cursor = await db.execute(
        "SELECT name FROM sqlite_master"
        " WHERE type='table' AND name='personal_access_tokens'"
    )
    if await cursor.fetchone():
        return

    await db.execute(
        "CREATE TABLE personal_access_tokens ("
        "  id TEXT PRIMARY KEY,"
        "  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,"
        "  name TEXT NOT NULL,"
        "  token_hash TEXT NOT NULL,"
        "  prefix TEXT NOT NULL,"
        "  created_at TEXT NOT NULL,"
        "  last_used_at TEXT,"
        "  expires_at TEXT,"
        "  revoked_at TEXT"
        ")"
    )
    await db.execute(
        "CREATE INDEX idx_pat_prefix ON personal_access_tokens(prefix)"
    )
    await db.execute(
        "CREATE INDEX idx_pat_user ON personal_access_tokens(user_id)"
    )
    await db.commit()
