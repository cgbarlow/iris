"""Service layer for the scope-prompt index (ADR-152).

Returns one entry per Collection and Set with a non-null, non-empty
`system_prompt`. Collections first, then Sets — matches the
priority order users see in the MCP prompt picker (collection-level
context tends to be the broader framing).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.adapter import DatabasePort


async def list_scope_prompts(db: DatabasePort) -> list[dict[str, object]]:
    """Return scope-prompt index entries (collections then sets)."""
    items: list[dict[str, object]] = []

    cursor = await db.execute(
        "SELECT id, name, description, system_prompt FROM collections "
        "WHERE is_deleted = 0 AND system_prompt IS NOT NULL "
        "ORDER BY name",
    )
    for row in await cursor.fetchall():
        body = (row[3] or "").strip()
        if not body:
            continue
        items.append({
            "name": f"iris:collection:{row[0]}",
            "scope_type": "collection",
            "scope_id": str(row[0]),
            "scope_name": str(row[1]),
            "description": row[2],
            "body": body,
        })

    cursor = await db.execute(
        "SELECT id, name, description, system_prompt FROM sets "
        "WHERE is_deleted = 0 AND system_prompt IS NOT NULL "
        "ORDER BY name",
    )
    for row in await cursor.fetchall():
        body = (row[3] or "").strip()
        if not body:
            continue
        items.append({
            "name": f"iris:set:{row[0]}",
            "scope_type": "set",
            "scope_id": str(row[0]),
            "scope_name": str(row[1]),
            "description": row[2],
            "body": body,
        })

    return items
