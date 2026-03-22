"""Database connection adapters for SQLite and Supabase/PostgreSQL (ADR-094).

Provides a unified `DatabasePort` interface so service code works unchanged across both
deployment modes. The only difference for callers is the type annotation: use `DatabasePort`
instead of `aiosqlite.Connection`.

SQLite mode (default):  SqliteAdapter wraps aiosqlite.Connection — zero overhead passthrough.
Supabase mode:          SupabaseAdapter wraps asyncpg pool — auto-converts ? → $N placeholders.
"""

from __future__ import annotations

import re
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
    - ``= 0`` / ``= 1`` to ``= FALSE`` / ``= TRUE`` for boolean column compatibility
    """
    # SQLite: INSERT OR IGNORE INTO ... → PostgreSQL: INSERT INTO ... ON CONFLICT DO NOTHING
    converted = re.sub(r"(?i)\bINSERT\s+OR\s+IGNORE\s+INTO\b", "INSERT INTO", query)
    needs_on_conflict = converted is not query

    # SQLite uses 0/1 for booleans; PostgreSQL requires TRUE/FALSE
    converted = re.sub(r"(?<==\s)0(?=\s|$|,|\))", "FALSE", converted)
    converted = re.sub(r"(?<==\s)1(?=\s|$|,|\))", "TRUE", converted)

    counter = 0

    def _replacer(_match: re.Match[str]) -> str:
        nonlocal counter
        counter += 1
        return f"${counter}"

    pg_query = _PLACEHOLDER_RE.sub(_replacer, converted)

    if needs_on_conflict:
        pg_query = pg_query.rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"

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

    @property
    def lastrowid(self) -> int | None:
        return self._lastrowid

    @property
    def rowcount(self) -> int:
        return self._rowcount


class SupabaseAdapter:
    """DatabasePort adapter backed by an asyncpg connection pool.

    Handles:
    - Automatic ? → $N placeholder conversion
    - Result wrapping to match the aiosqlite cursor interface

    Each execute() acquires a connection from the pool and releases it after.
    For DML, each statement auto-commits (no explicit transaction needed).
    commit() is a no-op for compatibility with the DatabasePort interface.
    """

    def __init__(self, pool: asyncpg.Pool) -> None:  # type: ignore[name-defined]
        self._pool = pool

    async def execute(self, query: str, params: tuple[Any, ...] = ()) -> _AsyncpgCursor:
        pg_query = _convert_placeholders(query)

        async with self._pool.acquire() as conn:
            if _is_select(pg_query):
                rows: list[asyncpg.Record] = await conn.fetch(pg_query, *params)
                return _AsyncpgCursor(rows, rowcount=len(rows))
            else:
                upper = pg_query.strip().upper()
                if "RETURNING" in upper:
                    rows = await conn.fetch(pg_query, *params)
                    return _AsyncpgCursor(rows, rowcount=len(rows))
                else:
                    status: str = await conn.execute(pg_query, *params)
                    return _AsyncpgCursor([], rowcount=_parse_rowcount(status))

    async def commit(self) -> None:
        # Each execute() auto-commits via the pool; no-op for interface compat.
        pass

    async def rollback(self) -> None:
        pass

    @property
    def raw(self) -> asyncpg.Pool:  # type: ignore[name-defined]
        return self._pool
