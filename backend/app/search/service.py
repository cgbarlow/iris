"""Search service — FTS5 (SQLite) and tsvector (PostgreSQL/Supabase) implementations."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.adapter import DatabasePort


# ---------------------------------------------------------------------------
# Index management
# ---------------------------------------------------------------------------


async def rebuild_search_index(db: DatabasePort) -> None:
    """Rebuild FTS indices from current element and diagram data.

    SQLite mode: rebuilds FTS5 virtual tables.
    Supabase mode: no-op — tsvector columns are maintained by triggers.
    """
    from app.db.adapter import SupabaseAdapter  # noqa: PLC0415

    if isinstance(db, SupabaseAdapter):
        return  # Triggers keep tsvector columns up to date automatically

    # SQLite: rebuild FTS5 tables from scratch
    await db.execute("DELETE FROM elements_fts")
    await db.execute("DELETE FROM diagrams_fts")

    cursor = await db.execute(
        "SELECT e.id, e.element_type, ev.name, ev.description "
        "FROM elements e "
        "JOIN element_versions ev ON e.id = ev.element_id AND e.current_version = ev.version "
        "WHERE e.is_deleted = 0"
    )
    for row in await cursor.fetchall():
        await db.execute(
            "INSERT INTO elements_fts (element_id, name, element_type, description) "
            "VALUES (?, ?, ?, ?)",
            (row[0], row[2], row[1], row[3] or ""),
        )

    cursor = await db.execute(
        "SELECT m.id, m.diagram_type, mv.name, mv.description "
        "FROM diagrams m "
        "JOIN diagram_versions mv ON m.id = mv.diagram_id AND m.current_version = mv.version "
        "WHERE m.is_deleted = 0"
    )
    for row in await cursor.fetchall():
        await db.execute(
            "INSERT INTO diagrams_fts (diagram_id, name, diagram_type, description) "
            "VALUES (?, ?, ?, ?)",
            (row[0], row[2], row[1], row[3] or ""),
        )

    await db.commit()


async def index_element(
    db: DatabasePort,
    *,
    element_id: str,
    name: str,
    element_type: str,
    description: str | None,
) -> None:
    """Index or re-index an element.

    SQLite: updates elements_fts virtual table.
    Supabase: no-op — tsvector trigger fires on the elements table INSERT/UPDATE.
    """
    from app.db.adapter import SupabaseAdapter  # noqa: PLC0415

    if isinstance(db, SupabaseAdapter):
        return

    await db.execute(
        "DELETE FROM elements_fts WHERE element_id = ?", (element_id,),
    )
    await db.execute(
        "INSERT INTO elements_fts (element_id, name, element_type, description) "
        "VALUES (?, ?, ?, ?)",
        (element_id, name, element_type, description or ""),
    )


async def index_diagram(
    db: DatabasePort,
    *,
    diagram_id: str,
    name: str,
    diagram_type: str,
    description: str | None,
) -> None:
    """Index or re-index a diagram.

    SQLite: updates diagrams_fts virtual table.
    Supabase: no-op — tsvector trigger fires on the diagrams table INSERT/UPDATE.
    """
    from app.db.adapter import SupabaseAdapter  # noqa: PLC0415

    if isinstance(db, SupabaseAdapter):
        return

    await db.execute(
        "DELETE FROM diagrams_fts WHERE diagram_id = ?", (diagram_id,),
    )
    await db.execute(
        "INSERT INTO diagrams_fts (diagram_id, name, diagram_type, description) "
        "VALUES (?, ?, ?, ?)",
        (diagram_id, name, diagram_type, description or ""),
    )


async def remove_element_index(db: DatabasePort, element_id: str) -> None:
    """Remove an element from the FTS index (SQLite only)."""
    from app.db.adapter import SupabaseAdapter  # noqa: PLC0415

    if isinstance(db, SupabaseAdapter):
        return

    await db.execute(
        "DELETE FROM elements_fts WHERE element_id = ?", (element_id,),
    )


async def remove_diagram_index(db: DatabasePort, diagram_id: str) -> None:
    """Remove a diagram from the FTS index (SQLite only)."""
    from app.db.adapter import SupabaseAdapter  # noqa: PLC0415

    if isinstance(db, SupabaseAdapter):
        return

    await db.execute(
        "DELETE FROM diagrams_fts WHERE diagram_id = ?", (diagram_id,),
    )


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


async def search(
    db: DatabasePort,
    query: str,
    *,
    limit: int = 50,
    set_id: str | None = None,
) -> list[dict[str, object]]:
    """Search elements and diagrams.

    SQLite mode:   FTS5 MATCH queries with rank ordering.
    Supabase mode: PostgreSQL tsvector/tsquery with ts_rank ordering.
    """
    from app.db.adapter import SupabaseAdapter  # noqa: PLC0415

    if isinstance(db, SupabaseAdapter):
        return await _search_postgres(db, query, limit=limit, set_id=set_id)
    return await _search_sqlite(db, query, limit=limit, set_id=set_id)


async def _search_sqlite(
    db: DatabasePort,
    query: str,
    *,
    limit: int,
    set_id: str | None,
) -> list[dict[str, object]]:
    """FTS5-based search for SQLite deployment."""
    results: list[dict[str, object]] = []
    safe_query = _escape_fts_query(query)
    if not safe_query:
        return results

    if set_id:
        cursor = await db.execute(
            "SELECT f.element_id, f.name, f.element_type, f.description, f.rank "
            "FROM elements_fts f "
            "JOIN elements e ON e.id = f.element_id "
            "WHERE elements_fts MATCH ? AND e.set_id = ? "
            "ORDER BY f.rank LIMIT ?",
            (safe_query, set_id, limit),
        )
    else:
        cursor = await db.execute(
            "SELECT element_id, name, element_type, description, rank "
            "FROM elements_fts WHERE elements_fts MATCH ? "
            "ORDER BY rank LIMIT ?",
            (safe_query, limit),
        )
    element_rows = await cursor.fetchall()
    results.extend(
        {
            "id": row[0],
            "result_type": "element",
            "name": row[1],
            "type_detail": row[2],
            "description": row[3] or None,
            "rank": float(row[4]),
            "deep_link": f"/elements/{row[0]}",
        }
        for row in element_rows
    )

    if set_id:
        cursor = await db.execute(
            "SELECT f.diagram_id, f.name, f.diagram_type, f.description, f.rank "
            "FROM diagrams_fts f "
            "JOIN diagrams m ON m.id = f.diagram_id "
            "WHERE diagrams_fts MATCH ? AND m.set_id = ? "
            "ORDER BY f.rank LIMIT ?",
            (safe_query, set_id, limit),
        )
    else:
        cursor = await db.execute(
            "SELECT diagram_id, name, diagram_type, description, rank "
            "FROM diagrams_fts WHERE diagrams_fts MATCH ? "
            "ORDER BY rank LIMIT ?",
            (safe_query, limit),
        )
    diagram_rows = await cursor.fetchall()
    results.extend(
        {
            "id": row[0],
            "result_type": "diagram",
            "name": row[1],
            "type_detail": row[2],
            "description": row[3] or None,
            "rank": float(row[4]),
            "deep_link": f"/diagrams/{row[0]}",
        }
        for row in diagram_rows
    )

    # FTS5 rank is negative; closer to 0 = better match
    results.sort(key=lambda r: r["rank"])
    return results[:limit]


async def _search_postgres(
    db: DatabasePort,
    query: str,
    *,
    limit: int,
    set_id: str | None,
) -> list[dict[str, object]]:
    """tsvector-based search for Supabase/PostgreSQL deployment."""
    results: list[dict[str, object]] = []

    # Build safe tsquery: prefix-match each word with :*
    words = query.strip().split()
    if not words:
        return results
    tsquery = " & ".join(f"{w}:*" for w in words)

    if set_id:
        cursor = await db.execute(
            "SELECT e.id, ev.name, e.element_type, ev.description, "
            "ts_rank(e.search_vector, to_tsquery('english', ?)) AS rank "
            "FROM elements e "
            "JOIN element_versions ev ON e.id = ev.element_id AND e.current_version = ev.version "
            "WHERE e.search_vector @@ to_tsquery('english', ?) AND e.set_id = ? "
            "AND e.is_deleted = FALSE "
            "ORDER BY rank DESC LIMIT ?",
            (tsquery, tsquery, set_id, limit),
        )
    else:
        cursor = await db.execute(
            "SELECT e.id, ev.name, e.element_type, ev.description, "
            "ts_rank(e.search_vector, to_tsquery('english', ?)) AS rank "
            "FROM elements e "
            "JOIN element_versions ev ON e.id = ev.element_id AND e.current_version = ev.version "
            "WHERE e.search_vector @@ to_tsquery('english', ?) "
            "AND e.is_deleted = FALSE "
            "ORDER BY rank DESC LIMIT ?",
            (tsquery, tsquery, limit),
        )
    element_rows = await cursor.fetchall()
    results.extend(
        {
            "id": row[0],
            "result_type": "element",
            "name": row[1],
            "type_detail": row[2],
            "description": row[3] or None,
            "rank": float(row[4]),
            "deep_link": f"/elements/{row[0]}",
        }
        for row in element_rows
    )

    if set_id:
        cursor = await db.execute(
            "SELECT m.id, mv.name, m.diagram_type, mv.description, "
            "ts_rank(m.search_vector, to_tsquery('english', ?)) AS rank "
            "FROM diagrams m "
            "JOIN diagram_versions mv ON m.id = mv.diagram_id AND m.current_version = mv.version "
            "WHERE m.search_vector @@ to_tsquery('english', ?) AND m.set_id = ? "
            "AND m.is_deleted = FALSE "
            "ORDER BY rank DESC LIMIT ?",
            (tsquery, tsquery, set_id, limit),
        )
    else:
        cursor = await db.execute(
            "SELECT m.id, mv.name, m.diagram_type, mv.description, "
            "ts_rank(m.search_vector, to_tsquery('english', ?)) AS rank "
            "FROM diagrams m "
            "JOIN diagram_versions mv ON m.id = mv.diagram_id AND m.current_version = mv.version "
            "WHERE m.search_vector @@ to_tsquery('english', ?) "
            "AND m.is_deleted = FALSE "
            "ORDER BY rank DESC LIMIT ?",
            (tsquery, tsquery, limit),
        )
    diagram_rows = await cursor.fetchall()
    results.extend(
        {
            "id": row[0],
            "result_type": "diagram",
            "name": row[1],
            "type_detail": row[2],
            "description": row[3] or None,
            "rank": float(row[4]),
            "deep_link": f"/diagrams/{row[0]}",
        }
        for row in diagram_rows
    )

    # PostgreSQL ts_rank is positive; higher = better match
    results.sort(key=lambda r: r["rank"], reverse=True)
    return results[:limit]


def _escape_fts_query(query: str) -> str:
    """Escape a user query for safe FTS5 matching."""
    words = query.strip().split()
    if not words:
        return ""
    return " ".join(f'"{w}"' for w in words)
