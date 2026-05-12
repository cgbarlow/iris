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
    await db.execute("DELETE FROM packages_fts")
    await db.execute("DELETE FROM sets_fts")
    await db.execute("DELETE FROM collections_fts")

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

    cursor = await db.execute(
        "SELECT p.id, pv.name, pv.description "
        "FROM packages p "
        "JOIN package_versions pv ON p.id = pv.package_id AND p.current_version = pv.version "
        "WHERE p.is_deleted = 0"
    )
    for row in await cursor.fetchall():
        await db.execute(
            "INSERT INTO packages_fts (package_id, name, description) "
            "VALUES (?, ?, ?)",
            (row[0], row[1], row[2] or ""),
        )

    cursor = await db.execute(
        "SELECT id, name, description FROM sets WHERE is_deleted = 0"
    )
    for row in await cursor.fetchall():
        await db.execute(
            "INSERT INTO sets_fts (set_id, name, description) VALUES (?, ?, ?)",
            (row[0], row[1], row[2] or ""),
        )

    cursor = await db.execute(
        "SELECT id, name, description FROM collections WHERE is_deleted = 0"
    )
    for row in await cursor.fetchall():
        await db.execute(
            "INSERT INTO collections_fts (collection_id, name, description) VALUES (?, ?, ?)",
            (row[0], row[1], row[2] or ""),
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


async def index_package(
    db: DatabasePort,
    *,
    package_id: str,
    name: str,
    description: str | None,
) -> None:
    """Index or re-index a package (SQLite only)."""
    from app.db.adapter import SupabaseAdapter  # noqa: PLC0415

    if isinstance(db, SupabaseAdapter):
        return

    await db.execute(
        "DELETE FROM packages_fts WHERE package_id = ?", (package_id,),
    )
    await db.execute(
        "INSERT INTO packages_fts (package_id, name, description) "
        "VALUES (?, ?, ?)",
        (package_id, name, description or ""),
    )


async def remove_package_index(db: DatabasePort, package_id: str) -> None:
    """Remove a package from the FTS index (SQLite only)."""
    from app.db.adapter import SupabaseAdapter  # noqa: PLC0415

    if isinstance(db, SupabaseAdapter):
        return

    await db.execute(
        "DELETE FROM packages_fts WHERE package_id = ?", (package_id,),
    )


async def index_set(
    db: DatabasePort,
    *,
    set_id: str,
    name: str,
    description: str | None,
) -> None:
    """Index or re-index a set (SQLite only)."""
    from app.db.adapter import SupabaseAdapter  # noqa: PLC0415

    if isinstance(db, SupabaseAdapter):
        return

    await db.execute("DELETE FROM sets_fts WHERE set_id = ?", (set_id,))
    await db.execute(
        "INSERT INTO sets_fts (set_id, name, description) VALUES (?, ?, ?)",
        (set_id, name, description or ""),
    )


async def remove_set_index(db: DatabasePort, set_id: str) -> None:
    """Remove a set from the FTS index (SQLite only)."""
    from app.db.adapter import SupabaseAdapter  # noqa: PLC0415

    if isinstance(db, SupabaseAdapter):
        return

    await db.execute("DELETE FROM sets_fts WHERE set_id = ?", (set_id,))


async def index_collection(
    db: DatabasePort,
    *,
    collection_id: str,
    name: str,
    description: str | None,
) -> None:
    """Index or re-index a collection (SQLite only)."""
    from app.db.adapter import SupabaseAdapter  # noqa: PLC0415

    if isinstance(db, SupabaseAdapter):
        return

    await db.execute("DELETE FROM collections_fts WHERE collection_id = ?", (collection_id,))
    await db.execute(
        "INSERT INTO collections_fts (collection_id, name, description) VALUES (?, ?, ?)",
        (collection_id, name, description or ""),
    )


async def remove_collection_index(db: DatabasePort, collection_id: str) -> None:
    """Remove a collection from the FTS index (SQLite only)."""
    from app.db.adapter import SupabaseAdapter  # noqa: PLC0415

    if isinstance(db, SupabaseAdapter):
        return

    await db.execute("DELETE FROM collections_fts WHERE collection_id = ?", (collection_id,))


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


async def search(
    db: DatabasePort,
    query: str,
    *,
    limit: int = 50,
    set_id: str | None = None,
    collection_id: str | None = None,
) -> list[dict[str, object]]:
    """Search elements and diagrams.

    SQLite mode:   FTS5 MATCH queries with rank ordering.
    Supabase mode: PostgreSQL tsvector/tsquery with ts_rank ordering.
    """
    from app.db.adapter import SupabaseAdapter  # noqa: PLC0415

    if isinstance(db, SupabaseAdapter):
        return await _search_postgres(db, query, limit=limit, set_id=set_id, collection_id=collection_id)
    return await _search_sqlite(db, query, limit=limit, set_id=set_id, collection_id=collection_id)


async def _search_sqlite(
    db: DatabasePort,
    query: str,
    *,
    limit: int,
    set_id: str | None,
    collection_id: str | None = None,
) -> list[dict[str, object]]:
    """FTS5-based search for SQLite deployment."""
    results: list[dict[str, object]] = []
    safe_query = _escape_fts_query(query)
    if not safe_query:
        return results

    _ELEMENT_COLS = (
        "f.element_id, f.name, f.element_type, f.description, f.rank, "
        "s.name, c.name, e.set_id"
    )
    _ELEMENT_JOINS = (
        "FROM elements_fts f "
        "JOIN elements e ON e.id = f.element_id "
        "LEFT JOIN sets s ON e.set_id = s.id "
        "LEFT JOIN collections c ON s.collection_id = c.id "
    )
    if set_id:
        cursor = await db.execute(
            f"SELECT {_ELEMENT_COLS} {_ELEMENT_JOINS}"  # noqa: S608
            "WHERE elements_fts MATCH ? AND e.set_id = ? "
            "ORDER BY f.rank LIMIT ?",
            (safe_query, set_id, limit),
        )
    elif collection_id:
        cursor = await db.execute(
            f"SELECT {_ELEMENT_COLS} {_ELEMENT_JOINS}"  # noqa: S608
            "WHERE elements_fts MATCH ? AND e.set_id IN (SELECT id FROM sets WHERE collection_id = ?) "
            "ORDER BY f.rank LIMIT ?",
            (safe_query, collection_id, limit),
        )
    else:
        cursor = await db.execute(
            f"SELECT {_ELEMENT_COLS} {_ELEMENT_JOINS}"  # noqa: S608
            "WHERE elements_fts MATCH ? "
            "ORDER BY f.rank LIMIT ?",
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
            "set_id": row[7],
            "set_name": row[5],
            "collection_name": row[6],
        }
        for row in element_rows
    )

    _DIAGRAM_COLS = (
        "f.diagram_id, f.name, f.diagram_type, f.description, f.rank, "
        "s.name, c.name, pv.name, m.set_id"
    )
    _DIAGRAM_JOINS = (
        "FROM diagrams_fts f "
        "JOIN diagrams m ON m.id = f.diagram_id "
        "LEFT JOIN sets s ON m.set_id = s.id "
        "LEFT JOIN collections c ON s.collection_id = c.id "
        "LEFT JOIN packages p ON m.parent_package_id = p.id "
        "LEFT JOIN package_versions pv ON p.id = pv.package_id AND p.current_version = pv.version "
    )
    if set_id:
        cursor = await db.execute(
            f"SELECT {_DIAGRAM_COLS} {_DIAGRAM_JOINS}"  # noqa: S608
            "WHERE diagrams_fts MATCH ? AND m.set_id = ? "
            "ORDER BY f.rank LIMIT ?",
            (safe_query, set_id, limit),
        )
    elif collection_id:
        cursor = await db.execute(
            f"SELECT {_DIAGRAM_COLS} {_DIAGRAM_JOINS}"  # noqa: S608
            "WHERE diagrams_fts MATCH ? AND m.set_id IN (SELECT id FROM sets WHERE collection_id = ?) "
            "ORDER BY f.rank LIMIT ?",
            (safe_query, collection_id, limit),
        )
    else:
        cursor = await db.execute(
            f"SELECT {_DIAGRAM_COLS} {_DIAGRAM_JOINS}"  # noqa: S608
            "WHERE diagrams_fts MATCH ? "
            "ORDER BY f.rank LIMIT ?",
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
            "set_id": row[8],
            "set_name": row[5],
            "collection_name": row[6],
            "package_name": row[7],
        }
        for row in diagram_rows
    )

    # Packages
    _PKG_COLS = (
        "f.package_id, pv.name, pv.description, f.rank, "
        "s.name, c.name, p.set_id"
    )
    _PKG_JOINS = (
        "FROM packages_fts f "
        "JOIN packages p ON p.id = f.package_id "
        "JOIN package_versions pv ON p.id = pv.package_id AND p.current_version = pv.version "
        "LEFT JOIN sets s ON p.set_id = s.id "
        "LEFT JOIN collections c ON s.collection_id = c.id "
    )
    if set_id:
        cursor = await db.execute(
            f"SELECT {_PKG_COLS} {_PKG_JOINS}"  # noqa: S608
            "WHERE packages_fts MATCH ? AND p.set_id = ? "
            "ORDER BY f.rank LIMIT ?",
            (safe_query, set_id, limit),
        )
    elif collection_id:
        cursor = await db.execute(
            f"SELECT {_PKG_COLS} {_PKG_JOINS}"  # noqa: S608
            "WHERE packages_fts MATCH ? AND p.set_id IN (SELECT id FROM sets WHERE collection_id = ?) "
            "ORDER BY f.rank LIMIT ?",
            (safe_query, collection_id, limit),
        )
    else:
        cursor = await db.execute(
            f"SELECT {_PKG_COLS} {_PKG_JOINS}"  # noqa: S608
            "WHERE packages_fts MATCH ? "
            "ORDER BY f.rank LIMIT ?",
            (safe_query, limit),
        )
    package_rows = await cursor.fetchall()
    results.extend(
        {
            "id": row[0],
            "result_type": "package",
            "name": row[1],
            "type_detail": "package",
            "description": row[2] or None,
            "rank": float(row[3]),
            "deep_link": f"/packages/{row[0]}",
            "set_id": row[6],
            "set_name": row[4],
            "collection_name": row[5],
        }
        for row in package_rows
    )

    # Sets
    if not set_id:  # Don't search sets when already filtered to a specific set
        # ADR-159 (v5.14.0): include s.mcp_system_context so the orient
        # guidance lands on the search hit, not just on get_set.
        _SET_COLS = "f.set_id, s.name, s.description, f.rank, c.id, c.name, s.mcp_system_context"
        _SET_JOINS = (
            "FROM sets_fts f "
            "JOIN sets s ON s.id = f.set_id "
            "LEFT JOIN collections c ON s.collection_id = c.id "
        )
        if collection_id:
            cursor = await db.execute(
                f"SELECT {_SET_COLS} {_SET_JOINS}"  # noqa: S608
                "WHERE sets_fts MATCH ? AND s.collection_id = ? "
                "ORDER BY f.rank LIMIT ?",
                (safe_query, collection_id, limit),
            )
        else:
            cursor = await db.execute(
                f"SELECT {_SET_COLS} {_SET_JOINS}"  # noqa: S608
                "WHERE sets_fts MATCH ? "
                "ORDER BY f.rank LIMIT ?",
                (safe_query, limit),
            )
        set_rows = await cursor.fetchall()
        results.extend(
            {
                "id": row[0],
                "result_type": "set",
                "name": row[1],
                "type_detail": "set",
                "description": row[2] or None,
                "rank": float(row[3]),
                "deep_link": f"/sets",
                "set_id": row[0],
                "set_name": row[1],
                "collection_name": row[5],
                "mcp_system_context": row[6],
            }
            for row in set_rows
        )

    # Collections
    if not set_id and not collection_id:
        cursor = await db.execute(
            "SELECT f.collection_id, c.name, c.description, f.rank, c.mcp_system_context "
            "FROM collections_fts f "
            "JOIN collections c ON c.id = f.collection_id "
            "WHERE collections_fts MATCH ? "
            "ORDER BY f.rank LIMIT ?",
            (safe_query, limit),
        )
        collection_rows = await cursor.fetchall()
        results.extend(
            {
                "id": row[0],
                "result_type": "collection",
                "name": row[1],
                "type_detail": "collection",
                "description": row[2] or None,
                "rank": float(row[3]),
                "deep_link": f"/collections",
                "mcp_system_context": row[4],
            }
            for row in collection_rows
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
    collection_id: str | None = None,
) -> list[dict[str, object]]:
    """tsvector-based search for Supabase/PostgreSQL deployment."""
    results: list[dict[str, object]] = []

    # Build safe tsquery: prefix-match each word with :*
    words = query.strip().split()
    if not words:
        return results
    tsquery = " & ".join(f"{w}:*" for w in words)

    _PG_ELEM = (
        "SELECT e.id, ev.name, e.element_type, ev.description, "
        "ts_rank(e.search_vector, to_tsquery('english', ?)) AS rank, "
        "s.name AS set_name, col.name AS collection_name, e.set_id "
        "FROM elements e "
        "JOIN element_versions ev ON e.id = ev.element_id AND e.current_version = ev.version "
        "LEFT JOIN sets s ON e.set_id = s.id "
        "LEFT JOIN collections col ON s.collection_id = col.id "
    )
    if set_id:
        cursor = await db.execute(
            f"{_PG_ELEM}"  # noqa: S608
            "WHERE e.search_vector @@ to_tsquery('english', ?) AND e.set_id = ? "
            "AND e.is_deleted = FALSE "
            "ORDER BY rank DESC LIMIT ?",
            (tsquery, tsquery, set_id, limit),
        )
    elif collection_id:
        cursor = await db.execute(
            f"{_PG_ELEM}"  # noqa: S608
            "WHERE e.search_vector @@ to_tsquery('english', ?) "
            "AND e.set_id IN (SELECT id FROM sets WHERE collection_id = ?) "
            "AND e.is_deleted = FALSE "
            "ORDER BY rank DESC LIMIT ?",
            (tsquery, tsquery, collection_id, limit),
        )
    else:
        cursor = await db.execute(
            f"{_PG_ELEM}"  # noqa: S608
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
            "set_id": row[7],
            "set_name": row[5],
            "collection_name": row[6],
        }
        for row in element_rows
    )

    _PG_DIAG = (
        "SELECT m.id, mv.name, m.diagram_type, mv.description, "
        "ts_rank(m.search_vector, to_tsquery('english', ?)) AS rank, "
        "s.name AS set_name, col.name AS collection_name, pv.name AS package_name, m.set_id "
        "FROM diagrams m "
        "JOIN diagram_versions mv ON m.id = mv.diagram_id AND m.current_version = mv.version "
        "LEFT JOIN sets s ON m.set_id = s.id "
        "LEFT JOIN collections col ON s.collection_id = col.id "
        "LEFT JOIN packages p ON m.parent_package_id = p.id "
        "LEFT JOIN package_versions pv ON p.id = pv.package_id AND p.current_version = pv.version "
    )
    if set_id:
        cursor = await db.execute(
            f"{_PG_DIAG}"  # noqa: S608
            "WHERE m.search_vector @@ to_tsquery('english', ?) AND m.set_id = ? "
            "AND m.is_deleted = FALSE "
            "ORDER BY rank DESC LIMIT ?",
            (tsquery, tsquery, set_id, limit),
        )
    elif collection_id:
        cursor = await db.execute(
            f"{_PG_DIAG}"  # noqa: S608
            "WHERE m.search_vector @@ to_tsquery('english', ?) "
            "AND m.set_id IN (SELECT id FROM sets WHERE collection_id = ?) "
            "AND m.is_deleted = FALSE "
            "ORDER BY rank DESC LIMIT ?",
            (tsquery, tsquery, collection_id, limit),
        )
    else:
        cursor = await db.execute(
            f"{_PG_DIAG}"  # noqa: S608
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
            "set_id": row[8],
            "set_name": row[5],
            "collection_name": row[6],
            "package_name": row[7],
        }
        for row in diagram_rows
    )

    # Packages (ADR-125 — parity with SQLite).
    # Ranks are merged with elements + diagrams at the end.
    _PG_PKG = (
        "SELECT p.id, pv.name, pv.description, "
        "ts_rank(p.search_vector, to_tsquery('english', ?)) AS rank, "
        "s.name AS set_name, col.name AS collection_name, p.set_id "
        "FROM packages p "
        "JOIN package_versions pv ON p.id = pv.package_id AND p.current_version = pv.version "
        "LEFT JOIN sets s ON p.set_id = s.id "
        "LEFT JOIN collections col ON s.collection_id = col.id "
    )
    if set_id:
        cursor = await db.execute(
            f"{_PG_PKG}"  # noqa: S608
            "WHERE p.search_vector @@ to_tsquery('english', ?) AND p.set_id = ? "
            "AND p.is_deleted = FALSE "
            "ORDER BY rank DESC LIMIT ?",
            (tsquery, tsquery, set_id, limit),
        )
    elif collection_id:
        cursor = await db.execute(
            f"{_PG_PKG}"  # noqa: S608
            "WHERE p.search_vector @@ to_tsquery('english', ?) "
            "AND p.set_id IN (SELECT id FROM sets WHERE collection_id = ?) "
            "AND p.is_deleted = FALSE "
            "ORDER BY rank DESC LIMIT ?",
            (tsquery, tsquery, collection_id, limit),
        )
    else:
        cursor = await db.execute(
            f"{_PG_PKG}"  # noqa: S608
            "WHERE p.search_vector @@ to_tsquery('english', ?) "
            "AND p.is_deleted = FALSE "
            "ORDER BY rank DESC LIMIT ?",
            (tsquery, tsquery, limit),
        )
    package_rows = await cursor.fetchall()
    results.extend(
        {
            "id": row[0],
            "result_type": "package",
            "name": row[1],
            "type_detail": "package",
            "description": row[2] or None,
            "rank": float(row[3]),
            "deep_link": f"/packages/{row[0]}",
            "set_id": row[6],
            "set_name": row[4],
            "collection_name": row[5],
        }
        for row in package_rows
    )

    # Sets (ADR-125). Skipped when already scoped to a specific set.
    if not set_id:
        # ADR-159 (v5.14.0): include s.mcp_system_context.
        _PG_SET = (
            "SELECT s.id, s.name, s.description, "
            "ts_rank(s.search_vector, to_tsquery('english', ?)) AS rank, "
            "col.id AS collection_id, col.name AS collection_name, "
            "s.mcp_system_context "
            "FROM sets s "
            "LEFT JOIN collections col ON s.collection_id = col.id "
        )
        if collection_id:
            cursor = await db.execute(
                f"{_PG_SET}"  # noqa: S608
                "WHERE s.search_vector @@ to_tsquery('english', ?) "
                "AND s.collection_id = ? AND s.is_deleted = FALSE "
                "ORDER BY rank DESC LIMIT ?",
                (tsquery, tsquery, collection_id, limit),
            )
        else:
            cursor = await db.execute(
                f"{_PG_SET}"  # noqa: S608
                "WHERE s.search_vector @@ to_tsquery('english', ?) "
                "AND s.is_deleted = FALSE "
                "ORDER BY rank DESC LIMIT ?",
                (tsquery, tsquery, limit),
            )
        set_rows = await cursor.fetchall()
        results.extend(
            {
                "id": row[0],
                "result_type": "set",
                "name": row[1],
                "type_detail": "set",
                "description": row[2] or None,
                "rank": float(row[3]),
                "deep_link": "/sets",
                "set_id": row[0],
                "set_name": row[1],
                "collection_name": row[5],
                "mcp_system_context": row[6],
            }
            for row in set_rows
        )

    # Collections (ADR-125). Skipped when scoped to a set or collection.
    if not set_id and not collection_id:
        cursor = await db.execute(
            "SELECT c.id, c.name, c.description, "
            "ts_rank(c.search_vector, to_tsquery('english', ?)) AS rank, "
            "c.mcp_system_context "
            "FROM collections c "
            "WHERE c.search_vector @@ to_tsquery('english', ?) "
            "AND c.is_deleted = FALSE "
            "ORDER BY rank DESC LIMIT ?",
            (tsquery, tsquery, limit),
        )
        collection_rows = await cursor.fetchall()
        results.extend(
            {
                "id": row[0],
                "result_type": "collection",
                "name": row[1],
                "type_detail": "collection",
                "description": row[2] or None,
                "rank": float(row[3]),
                "deep_link": "/collections",
                "mcp_system_context": row[4],
            }
            for row in collection_rows
        )

    # PostgreSQL ts_rank is positive; higher = better match
    results.sort(key=lambda r: r["rank"], reverse=True)
    return results[:limit]


def _escape_fts_query(query: str) -> str:
    """Escape a user query for safe FTS5 prefix matching."""
    words = query.strip().split()
    if not words:
        return ""
    return " ".join(f'"{w}"*' for w in words)
