"""SQLite connection management with PRAGMA configuration per SPEC-004-A."""

from __future__ import annotations

import aiosqlite

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
