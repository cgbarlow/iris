"""Scope-level system prompt composition (ADR-150, SPEC-150-A).

Builds the additive prepend that lives at the front of the system
message for every Ask Iris and MCP `ask` request. Composition order:

    [collection prompt 1]
    [collection prompt 2]   # multi-collection multi-set ask
    [set prompt 1]
    [set prompt 2]

Each block is separated by a blank line. Collection prompts are
deduplicated by id. When the caller supplies `collection_id` (e.g.,
multi-set Q&A where the UI tracks an active collection), that
collection is placed first; any additional collections derived from
the sets follow in `set_ids` order.

Empty / whitespace-only prompts are skipped. If nothing applies, an
empty string is returned and the caller composes its existing
system content untouched.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


async def build_scope_prompts(
    db: Any,
    *,
    set_ids: list[str],
    collection_id: str | None,
) -> str:
    """Return the scope prepend text (or "" when nothing applies)."""
    # Per-set lookup: their prompt and parent collection.
    set_prompts: list[str] = []
    derived_collection_ids: list[str] = []
    seen_collections: set[str] = set()

    # If caller supplied an explicit collection_id, reserve its slot at
    # the front of the ordered collection list.
    ordered_collection_ids: list[str] = []
    if collection_id:
        ordered_collection_ids.append(collection_id)
        seen_collections.add(collection_id)

    for set_id in set_ids:
        cursor = await db.execute(
            "SELECT system_prompt, collection_id FROM sets "
            "WHERE id = ? AND is_deleted = 0",
            (set_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            continue
        sp = row[0]
        if sp and sp.strip():
            set_prompts.append(sp.strip())
        cid = row[1]
        if cid and cid not in seen_collections:
            ordered_collection_ids.append(cid)
            seen_collections.add(cid)
            derived_collection_ids.append(cid)

    # Fetch collection prompts in order. Orphan collection ids are
    # silently dropped (the SELECT just returns no row).
    collection_prompts: list[str] = []
    for cid in ordered_collection_ids:
        cursor = await db.execute(
            "SELECT system_prompt FROM collections "
            "WHERE id = ? AND is_deleted = 0",
            (cid,),
        )
        row = await cursor.fetchone()
        if row is None:
            continue
        cp = row[0]
        if cp and cp.strip():
            collection_prompts.append(cp.strip())

    parts = collection_prompts + set_prompts
    return "\n\n".join(parts)
