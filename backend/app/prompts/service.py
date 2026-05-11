"""Service layer for the scope-prompt index (ADR-152; ADR-154; ADR-156).

v5.11.0 (ADR-156): scope-level prompt entries (`set:<uuid>` /
`collection:<uuid>`) are no longer emitted. The scope's MCP
`mcp_system_context` is now passed through as a data field on
`get_set` / `get_collection` MCP tool responses (ADR-156
supersedes ADR-155's slash-command approach), so it no longer
needs a picker entry. The picker now contains **named prompts
only** (ADR-154).

`system_prompt` continues to auto-apply in Iris AI server-side
composition (ADR-150) and is stripped from MCP tool responses
(ADR-151) — unchanged.

Returns:
- one entry per named prompt on a Collection / Set
  (`entry_kind="named_prompt"`, name `set:<uuid>:<name>` /
  `collection:<uuid>:<name>`)

Ordered by scope_type, then scope_name, then prompt_name.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.adapter import DatabasePort


async def list_scope_prompts(db: DatabasePort) -> list[dict[str, object]]:
    """Return MCP-picker index entries — named prompts only (ADR-156)."""
    items: list[dict[str, object]] = []

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
