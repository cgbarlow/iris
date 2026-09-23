"""Deployment-aware user lookup shared by the JWT and PAT auth paths (ADR-247).

SQLite mode stores users in ``users`` (TEXT ids). Supabase mode's authority
is ``profiles`` (UUID ids): ``users`` there is only a mirror synced from
``profiles`` at startup to satisfy ``created_by`` foreign keys, so it can be
missing new sign-ups and hold stale roles.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.auth.supabase_service import get_profile

if TYPE_CHECKING:
    from app.db.adapter import DatabasePort


async def get_user(
    db: DatabasePort,
    user_id: str,
    db_backend: str,
) -> dict[str, Any] | None:
    """Return ``{id, username, role, is_active}`` for ``user_id``, or None."""
    if db_backend == "supabase":
        return await get_profile(db, user_id)
    cursor = await db.execute(
        "SELECT id, username, role, is_active FROM users WHERE id = ?",
        (user_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    return {
        "id": row[0],
        "username": row[1],
        "role": row[2],
        "is_active": bool(row[3]),
    }
