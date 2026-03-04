"""Search service using SQLite FTS5."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


async def rebuild_search_index(db: aiosqlite.Connection) -> None:
    """Rebuild FTS indices from current element and diagram data."""
    # Clear existing FTS data
    await db.execute("DELETE FROM elements_fts")
    await db.execute("DELETE FROM diagrams_fts")

    # Re-index all non-deleted elements
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

    # Re-index all non-deleted diagrams
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
    db: aiosqlite.Connection,
    *,
    element_id: str,
    name: str,
    element_type: str,
    description: str | None,
) -> None:
    """Index or re-index an element in the FTS table."""
    # Delete existing entry then insert fresh
    await db.execute(
        "DELETE FROM elements_fts WHERE element_id = ?", (element_id,),
    )
    await db.execute(
        "INSERT INTO elements_fts (element_id, name, element_type, description) "
        "VALUES (?, ?, ?, ?)",
        (element_id, name, element_type, description or ""),
    )


async def index_diagram(
    db: aiosqlite.Connection,
    *,
    diagram_id: str,
    name: str,
    diagram_type: str,
    description: str | None,
) -> None:
    """Index or re-index a diagram in the FTS table."""
    await db.execute(
        "DELETE FROM diagrams_fts WHERE diagram_id = ?", (diagram_id,),
    )
    await db.execute(
        "INSERT INTO diagrams_fts (diagram_id, name, diagram_type, description) "
        "VALUES (?, ?, ?, ?)",
        (diagram_id, name, diagram_type, description or ""),
    )


async def remove_element_index(
    db: aiosqlite.Connection, element_id: str,
) -> None:
    """Remove an element from the FTS index."""
    await db.execute(
        "DELETE FROM elements_fts WHERE element_id = ?", (element_id,),
    )


async def remove_diagram_index(
    db: aiosqlite.Connection, diagram_id: str,
) -> None:
    """Remove a diagram from the FTS index."""
    await db.execute(
        "DELETE FROM diagrams_fts WHERE diagram_id = ?", (diagram_id,),
    )


async def search(
    db: aiosqlite.Connection,
    query: str,
    *,
    limit: int = 50,
    set_id: str | None = None,
) -> list[dict[str, object]]:
    """Search elements and diagrams using FTS5.

    Returns combined results sorted by relevance rank.
    When set_id is provided, only results belonging to that set are returned.
    """
    results: list[dict[str, object]] = []

    # Escape FTS5 special characters for safe matching
    safe_query = _escape_fts_query(query)
    if not safe_query:
        return results

    # Search elements
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

    # Search diagrams
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

    # Sort combined results by rank (FTS5 rank is negative, closer to 0 = better)
    results.sort(key=lambda r: r["rank"])
    return results[:limit]


def _escape_fts_query(query: str) -> str:
    """Escape a user query for safe FTS5 matching.

    Wraps each word in quotes to avoid FTS5 syntax errors
    from special characters.
    """
    words = query.strip().split()
    if not words:
        return ""
    # Quote each token to avoid FTS5 syntax issues
    return " ".join(f'"{w}"' for w in words)
