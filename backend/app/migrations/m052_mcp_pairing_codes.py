"""Migration 052: MCP pairing codes (ADR-160, SPEC-160-A).

Adds the `pairing_codes` table used by the in-app MCP pairing flow. A
pairing code is a short typeable one-shot credential that the user
generates in Iris's web UI and pastes into Claude (or any MCP client)
to authenticate the MCP connection. The exchange endpoint issues a
fresh PAT via the existing `personal_access_tokens` machinery, so
audit and revocation use the same pathway.

Idempotent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m052_mcp_pairing_codes"


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up."""
    await db.execute(
        "CREATE TABLE IF NOT EXISTS pairing_codes ("
        "  code TEXT PRIMARY KEY,"
        "  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,"
        "  created_at TEXT NOT NULL,"
        "  expires_at TEXT NOT NULL,"
        "  exchanged_at TEXT,"
        "  issued_pat_id TEXT,"
        "  issued_pat_name TEXT NOT NULL"
        ")"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_pairing_codes_user"
        " ON pairing_codes(user_id)"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_pairing_codes_expires"
        " ON pairing_codes(expires_at)"
    )
    await db.commit()
