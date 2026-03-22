"""Database connection management (ADR-094).

Provides a DatabaseManager that maintains connections to the application database(s).

SQLite mode (default): Dual aiosqlite connections (iris.db + iris_audit.db) with all
7 PRAGMA settings applied. Connections are wrapped in SqliteAdapter.

Supabase mode: A single asyncpg connection pool targeting the Supabase PostgreSQL database.
The audit log uses a table in the same database (not a separate file). Connections are
wrapped in SupabaseAdapter per-request via the pool.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Union

import aiosqlite

from app.db.adapter import DatabasePort, SqliteAdapter, SupabaseAdapter

if TYPE_CHECKING:
    import asyncpg

    from app.config import AppConfig, DatabaseConfig

_AUTO_VACUUM_INCREMENTAL = 2


async def configure_connection(db: aiosqlite.Connection) -> None:
    """Apply all 7 required PRAGMAs to a SQLite database connection."""
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
    """Create and configure a SQLite database connection."""
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    await configure_connection(db)
    return db


class DatabaseManager:
    """Manages database connections for iris.db and iris_audit.db (or Supabase PostgreSQL).

    SQLite usage:
        manager = DatabaseManager(config)
        await manager.connect()
        db = manager.main_db      # SqliteAdapter
        await manager.close()

    Supabase usage:
        manager = DatabaseManager(config)
        await manager.connect()
        db = manager.main_db      # SupabaseAdapter (per-connection from pool)
        await manager.close()
    """

    def __init__(self, config: Union[AppConfig, DatabaseConfig]) -> None:
        # Accept either AppConfig or legacy DatabaseConfig (backward compatible)
        from app.config import AppConfig as _AppConfig, DatabaseConfig as _DatabaseConfig  # noqa: PLC0415

        if isinstance(config, _DatabaseConfig):
            # Wrap bare DatabaseConfig in an AppConfig (SQLite mode, default settings)
            config = _AppConfig(database=config)
        self._config: AppConfig = config
        # SQLite state
        self._main_db: aiosqlite.Connection | None = None
        self._audit_db: aiosqlite.Connection | None = None
        # Supabase state
        self._pool: asyncpg.Pool | None = None  # type: ignore[name-defined]

    @property
    def is_supabase(self) -> bool:
        return self._config.db_backend == "supabase"

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Open database connections."""
        if self.is_supabase:
            await self._connect_supabase()
        else:
            await self._connect_sqlite()

    async def _connect_sqlite(self) -> None:
        db_config: DatabaseConfig = self._config.database
        import os

        os.makedirs(db_config.data_dir, exist_ok=True)
        self._main_db = await get_connection(db_config.main_db_path)
        self._audit_db = await get_connection(db_config.audit_db_path)

    async def _connect_supabase(self) -> None:
        import asyncpg  # noqa: PLC0415 (conditional import)

        assert self._config.supabase is not None, "SupabaseConfig required for supabase backend"
        self._pool = await asyncpg.create_pool(
            self._config.supabase.db_url,
            min_size=1,
            max_size=10,
            command_timeout=30,
            statement_cache_size=0,  # Transaction pooler does not support PREPARE
        )

    async def close(self) -> None:
        """Close all database connections."""
        if self._main_db is not None:
            await self._main_db.close()
            self._main_db = None
        if self._audit_db is not None:
            await self._audit_db.close()
            self._audit_db = None
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    # ------------------------------------------------------------------
    # Connection accessors
    # ------------------------------------------------------------------

    @property
    def main_db(self) -> DatabasePort:
        """Main application database connection (adapter)."""
        if self.is_supabase:
            return self._acquire_supabase()
        if self._main_db is None:
            msg = "Database not connected. Call connect() first."
            raise RuntimeError(msg)
        return SqliteAdapter(self._main_db)

    @property
    def audit_db(self) -> DatabasePort:
        """Audit database connection (adapter).

        In SQLite mode: separate iris_audit.db file.
        In Supabase mode: same PostgreSQL database (audit_log table).
        """
        if self.is_supabase:
            return self._acquire_supabase()
        if self._audit_db is None:
            msg = "Database not connected. Call connect() first."
            raise RuntimeError(msg)
        return SqliteAdapter(self._audit_db)

    def _acquire_supabase(self) -> SupabaseAdapter:
        """Return SupabaseAdapter wrapping the connection pool."""
        if self._pool is None:
            msg = "Database not connected. Call connect() first."
            raise RuntimeError(msg)
        return SupabaseAdapter(self._pool)

    # ------------------------------------------------------------------
    # Raw SQLite connection (for migrations and startup only)
    # ------------------------------------------------------------------

    @property
    def raw_main_db(self) -> aiosqlite.Connection:
        """Raw aiosqlite connection for use in SQLite migrations only."""
        if self._main_db is None:
            msg = "Database not connected. Call connect() first."
            raise RuntimeError(msg)
        return self._main_db

    @property
    def raw_audit_db(self) -> aiosqlite.Connection:
        """Raw aiosqlite connection for use in SQLite audit migrations only."""
        if self._audit_db is None:
            msg = "Database not connected. Call connect() first."
            raise RuntimeError(msg)
        return self._audit_db

    @property
    def pool(self) -> asyncpg.Pool:  # type: ignore[name-defined]
        """asyncpg pool for Supabase mode (for use in startup/migrations only)."""
        if self._pool is None:
            msg = "Database not connected. Call connect() first."
            raise RuntimeError(msg)
        return self._pool
