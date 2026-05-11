"""Service layer for the scope-prompt index (ADR-152; extended ADR-154).

Returns:
- one entry per Collection / Set with a non-null, non-empty
  `system_prompt` (`entry_kind="system_prompt"`)
- one entry per named prompt on a Collection / Set
  (`entry_kind="named_prompt"`)

Order: system prompts first (collections then sets, both alphabetical),
then named prompts (grouped by scope, alphabetical scope name, then
alphabetical prompt name within each scope).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.adapter import DatabasePort


async def list_scope_prompts(db: DatabasePort) -> list[dict[str, object]]:
    """Return scope-prompt index entries (system prompts then named prompts)."""
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
            "name": f"collection:{row[0]}",
            "entry_kind": "system_prompt",
            "scope_type": "collection",
            "scope_id": str(row[0]),
            "scope_name": str(row[1]),
            "description": row[2],
            "body": body,
            "prompt_name": None,
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
            "name": f"set:{row[0]}",
            "entry_kind": "system_prompt",
            "scope_type": "set",
            "scope_id": str(row[0]),
            "scope_name": str(row[1]),
            "description": row[2],
            "body": body,
            "prompt_name": None,
        })

    # ADR-154 named prompts. Join to fetch scope_name; exclude entries
    # whose scope has been soft-deleted (LEFT JOIN + WHERE on scope id).
    cursor = await db.execute(
        """
        SELECT p.id, p.scope_type, p.scope_id, p.name, p.description, p.body,
               COALESCE(c.name, s.name) AS scope_name
        FROM prompts p
        LEFT JOIN collections c ON p.scope_type = 'collection' AND p.scope_id = c.id AND c.is_deleted = 0
        LEFT JOIN sets        s ON p.scope_type = 'set'        AND p.scope_id = s.id AND s.is_deleted = 0
        WHERE COALESCE(c.id, s.id) IS NOT NULL
        ORDER BY p.scope_type, scope_name, p.name
        """,
    )
    for row in await cursor.fetchall():
        scope_type = str(row[1])
        scope_id = str(row[2])
        prompt_name = str(row[3])
        items.append({
            "name": f"{scope_type}:{scope_id}:{prompt_name}",
            "entry_kind": "named_prompt",
            "scope_type": scope_type,
            "scope_id": scope_id,
            "scope_name": str(row[6]),
            "description": row[4],
            "body": str(row[5]),
            "prompt_name": prompt_name,
        })

    return items
