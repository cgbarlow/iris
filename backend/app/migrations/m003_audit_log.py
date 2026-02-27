"""Migration 003: Audit log table in the audit database.

Per SPEC-007-A (Audit Log Schema and Hash Chain Implementation).
This migration runs against iris_audit.db, not iris.db.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m003_audit_log"

UP_SQL = """
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    user_id TEXT NOT NULL,
    username TEXT NOT NULL,
    action TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT,
    detail TEXT,
    ip_address TEXT,
    session_id TEXT,
    previous_hash TEXT NOT NULL,
    entry_hash TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp
    ON audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_log_user_id
    ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_action
    ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_log_target
    ON audit_log(target_type, target_id);
"""


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up against the audit database."""
    await db.executescript(UP_SQL)
    await db.commit()
