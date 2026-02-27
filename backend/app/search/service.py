"""Search service using SQLite FTS5."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


async def index_entity(
    db: aiosqlite.Connection,
    *,
    entity_id: str,
    name: str,
    entity_type: str,
    description: str | None,
) -> None:
    """Index or re-index an entity in the FTS table."""
    # Delete existing entry then insert fresh
    await db.execute(
        "DELETE FROM entities_fts WHERE entity_id = ?", (entity_id,),
    )
    await db.execute(
        "INSERT INTO entities_fts (entity_id, name, entity_type, description) "
        "VALUES (?, ?, ?, ?)",
        (entity_id, name, entity_type, description or ""),
    )


async def index_model(
    db: aiosqlite.Connection,
    *,
    model_id: str,
    name: str,
    model_type: str,
    description: str | None,
) -> None:
    """Index or re-index a model in the FTS table."""
    await db.execute(
        "DELETE FROM models_fts WHERE model_id = ?", (model_id,),
    )
    await db.execute(
        "INSERT INTO models_fts (model_id, name, model_type, description) "
        "VALUES (?, ?, ?, ?)",
        (model_id, name, model_type, description or ""),
    )


async def remove_entity_index(
    db: aiosqlite.Connection, entity_id: str,
) -> None:
    """Remove an entity from the FTS index."""
    await db.execute(
        "DELETE FROM entities_fts WHERE entity_id = ?", (entity_id,),
    )


async def remove_model_index(
    db: aiosqlite.Connection, model_id: str,
) -> None:
    """Remove a model from the FTS index."""
    await db.execute(
        "DELETE FROM models_fts WHERE model_id = ?", (model_id,),
    )


async def search(
    db: aiosqlite.Connection,
    query: str,
    *,
    limit: int = 50,
) -> list[dict[str, object]]:
    """Search entities and models using FTS5.

    Returns combined results sorted by relevance rank.
    """
    results: list[dict[str, object]] = []

    # Escape FTS5 special characters for safe matching
    safe_query = _escape_fts_query(query)
    if not safe_query:
        return results

    # Search entities
    cursor = await db.execute(
        "SELECT entity_id, name, entity_type, description, rank "
        "FROM entities_fts WHERE entities_fts MATCH ? "
        "ORDER BY rank LIMIT ?",
        (safe_query, limit),
    )
    entity_rows = await cursor.fetchall()
    results.extend(
        {
            "id": row[0],
            "result_type": "entity",
            "name": row[1],
            "type_detail": row[2],
            "description": row[3] or None,
            "rank": float(row[4]),
            "deep_link": f"/entities/{row[0]}",
        }
        for row in entity_rows
    )

    # Search models
    cursor = await db.execute(
        "SELECT model_id, name, model_type, description, rank "
        "FROM models_fts WHERE models_fts MATCH ? "
        "ORDER BY rank LIMIT ?",
        (safe_query, limit),
    )
    model_rows = await cursor.fetchall()
    results.extend(
        {
            "id": row[0],
            "result_type": "model",
            "name": row[1],
            "type_detail": row[2],
            "description": row[3] or None,
            "rank": float(row[4]),
            "deep_link": f"/models/{row[0]}",
        }
        for row in model_rows
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
