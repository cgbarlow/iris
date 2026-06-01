"""Per-user collection write-scope loader (ADR-237).

A user's *scope* is the set of collection ids they are permitted to **write**
in. An empty set means *unscoped* — the user's role applies everywhere (the
pre-ADR-237 behaviour). Assignment lives in the ``user_collection_scope`` table
(managed directly in Supabase); this module only reads it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.adapter import DatabasePort


async def load_scope(db: DatabasePort, user_id: str) -> set[str]:
    """Return the set of collection ids this user may write in.

    Empty set == unscoped (caller must treat as "write everywhere").
    Positional row access (§15) — asyncpg returns plain tuples.
    """
    cursor = await db.execute(
        "SELECT collection_id FROM user_collection_scope WHERE user_id = ?",
        (user_id,),
    )
    return {row[0] for row in await cursor.fetchall()}
