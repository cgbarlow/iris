"""Database connection adapters for SQLite and Supabase/PostgreSQL (ADR-094).

Provides a unified `DatabasePort` interface so service code works unchanged across both
deployment modes. The only difference for callers is the type annotation: use `DatabasePort`
instead of `aiosqlite.Connection`.

SQLite mode (default):  SqliteAdapter wraps aiosqlite.Connection — zero overhead passthrough.
Supabase mode:          SupabaseAdapter wraps asyncpg pool — auto-converts ? → $N placeholders.
"""

from __future__ import annotations

import contextlib
import re
from collections.abc import AsyncIterator
from datetime import date, datetime
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable
from uuid import UUID

if TYPE_CHECKING:
    import aiosqlite
    import asyncpg


# ---------------------------------------------------------------------------
# Protocol definitions
# ---------------------------------------------------------------------------


@runtime_checkable
class AsyncCursor(Protocol):
    """Cursor-like interface returned by DatabasePort.execute()."""

    async def fetchone(self) -> Any | None:
        """Return the next row, or None if no rows remain."""
        ...

    async def fetchall(self) -> list[Any]:
        """Return all remaining rows."""
        ...

    @property
    def lastrowid(self) -> int | None:
        """Row ID of the last INSERT, or None if not applicable."""
        ...

    @property
    def rowcount(self) -> int:
        """Number of rows affected by the last DML statement (DELETE/UPDATE/INSERT)."""
        ...


@runtime_checkable
class DatabasePort(Protocol):
    """Uniform async database interface for service code.

    Both SqliteAdapter and SupabaseAdapter implement this protocol so that
    services remain database-agnostic.
    """

    async def execute(self, query: str, params: tuple[Any, ...] = ()) -> AsyncCursor:
        """Execute a single SQL statement and return a cursor."""
        ...

    async def commit(self) -> None:
        """Commit the current transaction (no-op for autocommit backends)."""
        ...


# ---------------------------------------------------------------------------
# SQLite adapter (default deployment)
# ---------------------------------------------------------------------------


class _SqliteCursor:
    """Wraps aiosqlite.Cursor to satisfy AsyncCursor."""

    def __init__(self, cursor: aiosqlite.Cursor) -> None:
        self._cursor = cursor

    async def fetchone(self) -> Any | None:
        return await self._cursor.fetchone()

    async def fetchall(self) -> list[Any]:
        return await self._cursor.fetchall()

    @property
    def lastrowid(self) -> int | None:
        return self._cursor.lastrowid

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount  # type: ignore[return-value]


class SqliteAdapter:
    """DatabasePort adapter backed by an aiosqlite.Connection.

    This is a thin wrapper — all calls pass through to the underlying connection
    with no transformation. Used in the default SQLite deployment mode.
    """

    def __init__(self, connection: aiosqlite.Connection) -> None:
        self._conn = connection

    async def execute(self, query: str, params: tuple[Any, ...] = ()) -> _SqliteCursor:
        cursor = await self._conn.execute(query, params)
        return _SqliteCursor(cursor)

    async def commit(self) -> None:
        await self._conn.commit()

    # Expose the raw connection for migrations that use executescript.
    @property
    def raw(self) -> aiosqlite.Connection:
        return self._conn


# ---------------------------------------------------------------------------
# Supabase/PostgreSQL adapter
# ---------------------------------------------------------------------------

_PLACEHOLDER_RE = re.compile(r"\?")
_DML_PREFIXES = ("INSERT", "UPDATE", "DELETE", "WITH")
_SELECT_PREFIXES = ("SELECT", "WITH")


def _convert_placeholders(query: str) -> str:
    """Replace SQLite ? placeholders with PostgreSQL $1, $2, ... equivalents.

    Also converts:
    - ``INSERT OR IGNORE`` (SQLite) to ``INSERT ... ON CONFLICT DO NOTHING`` (PostgreSQL)
    - ``INSERT OR REPLACE`` (SQLite) to ``INSERT ... ON CONFLICT (id) DO UPDATE SET ...`` (PostgreSQL)
    - ``= 0`` / ``= 1`` to ``= FALSE`` / ``= TRUE`` for boolean column compatibility
    """
    needs_on_conflict = False
    needs_upsert = False
    upsert_columns: list[str] = []

    # SQLite: INSERT OR REPLACE INTO ... → PostgreSQL: INSERT INTO ... ON CONFLICT (...) DO UPDATE
    or_replace_match = re.match(
        r"(?i)INSERT\s+OR\s+REPLACE\s+INTO\s+\w+\s*\(([^)]+)\)", query
    )
    if or_replace_match:
        query = re.sub(r"(?i)\bINSERT\s+OR\s+REPLACE\s+INTO\b", "INSERT INTO", query)
        cols = [c.strip() for c in or_replace_match.group(1).split(",")]
        # Determine conflict target: use 'id' if present, otherwise first two columns
        # (handles composite PKs like (diagram_id, theme))
        if "id" in [c.lower() for c in cols]:
            upsert_pk = ["id"]
        else:
            # For tables without 'id', assume first two columns form the PK
            upsert_pk = cols[:2]
        pk_set = {c.lower() for c in upsert_pk}
        upsert_columns = [c for c in cols if c.lower() not in pk_set]
        needs_upsert = True

    # SQLite: INSERT OR IGNORE INTO ... → PostgreSQL: INSERT INTO ... ON CONFLICT DO NOTHING
    converted = re.sub(r"(?i)\bINSERT\s+OR\s+IGNORE\s+INTO\b", "INSERT INTO", query)
    if converted != query:
        needs_on_conflict = True
        query = converted

    # Boolean conversion for known boolean columns only (not version/count integers).
    # Match patterns like "is_deleted = 0", "is_active = 1", "is_default = 0"
    query = re.sub(r"(?i)\b(is_\w+)\s*=\s*0\b", r"\1 = FALSE", query)
    query = re.sub(r"(?i)\b(is_\w+)\s*=\s*1\b", r"\1 = TRUE", query)

    counter = 0

    def _replacer(_match: re.Match[str]) -> str:
        nonlocal counter
        counter += 1
        return f"${counter}"

    pg_query = _PLACEHOLDER_RE.sub(_replacer, query)

    if needs_on_conflict:
        pg_query = pg_query.rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"
    elif needs_upsert and upsert_columns:
        pk_cols = ", ".join(upsert_pk)
        updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in upsert_columns)
        pg_query = pg_query.rstrip().rstrip(";") + f" ON CONFLICT ({pk_cols}) DO UPDATE SET {updates}"

    return pg_query


def _is_select(query: str) -> bool:
    """Return True if the query is a SELECT (or CTE that produces rows)."""
    upper = query.strip().upper()
    return upper.startswith("SELECT") or (
        upper.startswith("WITH") and "SELECT" in upper and "RETURNING" not in upper
    )


def _parse_rowcount(status: str) -> int:
    """Parse affected row count from asyncpg DML status string (e.g. 'DELETE 3')."""
    parts = status.split()
    if parts and parts[-1].isdigit():
        return int(parts[-1])
    return 0


def _normalize_row(record: asyncpg.Record) -> tuple[Any, ...]:
    """Convert asyncpg Record to a tuple, converting PG types to SQLite-compatible types.

    PostgreSQL returns native datetime/UUID objects; SQLite returns strings.
    Convert so Pydantic models (expecting str) work unchanged.
    """
    values: list[Any] = []
    for val in record.values():
        if isinstance(val, datetime):
            values.append(val.isoformat())
        elif isinstance(val, date):
            values.append(val.isoformat())
        elif isinstance(val, UUID):
            values.append(str(val))
        else:
            values.append(val)
    return tuple(values)


class _AsyncpgCursor:
    """Wraps asyncpg query results to satisfy AsyncCursor."""

    def __init__(
        self,
        rows: list[asyncpg.Record],
        rowcount: int = 0,
        lastrowid: int | None = None,
    ) -> None:
        self._rows = [_normalize_row(r) for r in rows] if rows else []
        self._pos = 0
        self._rowcount = rowcount
        self._lastrowid = lastrowid

    async def fetchone(self) -> tuple[Any, ...] | None:
        if self._pos >= len(self._rows):
            return None
        row = self._rows[self._pos]
        self._pos += 1
        return row

    async def fetchall(self) -> list[tuple[Any, ...]]:
        remaining = self._rows[self._pos:]
        self._pos = len(self._rows)
        return remaining

    def __aiter__(self) -> _AsyncpgCursor:
        return self

    async def __anext__(self) -> tuple[Any, ...]:
        row = await self.fetchone()
        if row is None:
            raise StopAsyncIteration
        return row

    @property
    def lastrowid(self) -> int | None:
        return self._lastrowid

    @property
    def rowcount(self) -> int:
        return self._rowcount


_ISO_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}"
)


def _convert_params(params: tuple[Any, ...]) -> tuple[Any, ...]:
    """Convert SQLite-style parameters to asyncpg-compatible types.

    - ISO datetime strings → datetime objects (asyncpg requires native types)
    """
    converted: list[Any] = []
    for val in params:
        if isinstance(val, str) and _ISO_RE.match(val):
            try:
                converted.append(datetime.fromisoformat(val))
            except ValueError:
                converted.append(val)
        else:
            converted.append(val)
    return tuple(converted)


class SupabaseAdapter:
    """DatabasePort adapter backed by an asyncpg connection pool.

    Handles:
    - Automatic ? → $N placeholder conversion
    - ISO datetime string → datetime object conversion for parameters
    - Result wrapping to match the aiosqlite cursor interface

    Lazily acquires a connection from the pool on first execute() and holds it
    for the adapter's lifetime. Call release() to return the connection to the
    pool. This avoids per-statement pool acquire/release overhead.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:  # type: ignore[name-defined]
        self._pool = pool
        self._held_conn: asyncpg.Connection | None = None  # type: ignore[name-defined]

    # SQLite FTS virtual tables that don't exist in PostgreSQL (uses tsvector instead)
    _FTS_TABLES = {"elements_fts", "diagrams_fts", "packages_fts"}

    @contextlib.asynccontextmanager
    async def hold_connection(self) -> AsyncIterator[None]:
        """Hold a single pool connection for a batch of operations.

        Use this for bulk operations (e.g. import) to avoid per-execute
        pool acquire/release overhead. Normal requests should NOT use this.
        """
        self._held_conn = await self._pool.acquire()
        try:
            yield
        finally:
            await self._pool.release(self._held_conn)
            self._held_conn = None

    async def _execute_on(
        self, conn: asyncpg.Connection, pg_query: str, params: tuple[Any, ...]  # type: ignore[name-defined]
    ) -> _AsyncpgCursor:
        try:
            return await self._execute_on_inner(conn, pg_query, params)
        except Exception as exc:
            # Retry with int→bool conversion if asyncpg complains about boolean type
            if "boolean is required" in str(exc):
                bool_params = tuple(
                    bool(v) if isinstance(v, int) and not isinstance(v, bool) and v in (0, 1) else v
                    for v in params
                )
                return await self._execute_on_inner(conn, pg_query, bool_params)
            raise

    async def _execute_on_inner(
        self, conn: asyncpg.Connection, pg_query: str, params: tuple[Any, ...]  # type: ignore[name-defined]
    ) -> _AsyncpgCursor:
        upper = pg_query.strip().upper()
        if _is_select(pg_query):
            rows: list[asyncpg.Record] = await conn.fetch(pg_query, *params)
            return _AsyncpgCursor(rows, rowcount=len(rows))
        elif "RETURNING" in upper:
            rows = await conn.fetch(pg_query, *params)
            return _AsyncpgCursor(rows, rowcount=len(rows))
        else:
            status: str = await conn.execute(pg_query, *params)
            return _AsyncpgCursor([], rowcount=_parse_rowcount(status))

    async def execute(self, query: str, params: tuple[Any, ...] = ()) -> _AsyncpgCursor:
        pg_query = _convert_placeholders(query)
        params = _convert_params(params)

        # Skip operations on SQLite FTS virtual tables (not present in PostgreSQL)
        upper_stripped = pg_query.strip().upper()
        for fts in self._FTS_TABLES:
            if fts.upper() in upper_stripped:
                return _AsyncpgCursor([], rowcount=0)

        # Use held connection if available (bulk mode), otherwise acquire per-execute
        if self._held_conn is not None:
            return await self._execute_on(self._held_conn, pg_query, params)

        async with self._pool.acquire() as conn:
            return await self._execute_on(conn, pg_query, params)

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass

    @property
    def raw(self) -> asyncpg.Pool:  # type: ignore[name-defined]
        return self._pool
