"""SQLite connection management with PRAGMA configuration per SPEC-004-A.

Provides a DatabaseManager that maintains dual connections to iris.db and iris_audit.db
with all 7 required PRAGMAs applied to each connection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import aiosqlite

if TYPE_CHECKING:
    from app.config import DatabaseConfig

_AUTO_VACUUM_INCREMENTAL = 2


async def configure_connection(db: aiosqlite.Connection) -> None:
    """Apply all 7 required PRAGMAs to a database connection."""
    # auto_vacuum must be set before tables are created; VACUUM activates it on existing DBs
    cur = await db.execute("PRAGMA auto_vacuum")
    row = await cur.fetchone()
    if row is None or row[0] != _AUTO_VACUUM_INCREMENTAL:
        await db.execute("PRAGMA auto_vacuum=INCREMENTAL")
        await db.execute("VACUUM")
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    await db.execute("PRAGMA busy_timeout=5000")
    await db.execute("PRAGMA synchronous=NORMAL")
    await db.execute("PRAGMA cache_size=-64000")
    await db.execute("PRAGMA journal_size_limit=67108864")


async def get_connection(db_path: str) -> aiosqlite.Connection:
    """Create and configure a database connection."""
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    await configure_connection(db)
    return db


class DatabaseManager:
    """Manages dual database connections for iris.db and iris_audit.db.

    Usage:
        manager = DatabaseManager(config.database)
        await manager.connect()
        # Use manager.main_db and manager.audit_db
        await manager.close()
    """

    def __init__(self, config: DatabaseConfig) -> None:
        self.config = config
        self._main_db: aiosqlite.Connection | None = None
        self._audit_db: aiosqlite.Connection | None = None

    @property
    def main_db(self) -> aiosqlite.Connection:
        """Get the main application database connection."""
        if self._main_db is None:
            msg = "Database not connected. Call connect() first."
            raise RuntimeError(msg)
        return self._main_db

    @property
    def audit_db(self) -> aiosqlite.Connection:
        """Get the audit database connection."""
        if self._audit_db is None:
            msg = "Database not connected. Call connect() first."
            raise RuntimeError(msg)
        return self._audit_db

    async def connect(self) -> None:
        """Open and configure both database connections."""
        self._main_db = await get_connection(self.config.main_db_path)
        self._audit_db = await get_connection(self.config.audit_db_path)

    async def close(self) -> None:
        """Close both database connections."""
        if self._main_db is not None:
            await self._main_db.close()
            self._main_db = None
        if self._audit_db is not None:
            await self._audit_db.close()
            self._audit_db = None
