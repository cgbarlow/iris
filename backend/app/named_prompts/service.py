"""Service layer for named prompts (ADR-154, SPEC-154-A).

Each named prompt is attached to a Collection or Set. The MCP `prompts`
channel surfaces them as `set:<uuid>:<name>` / `collection:<uuid>:<name>`
alongside the existing scope `system_prompt` entries; they are picker-
invoked only and never participate in Ask Iris server-side composition.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from app.db.adapter import DatabasePort

ScopeType = Literal["collection", "set"]


def _row_to_dict(row: tuple) -> dict[str, object]:
    return {
        "id": str(row[0]),
        "scope_type": str(row[1]),
        "scope_id": str(row[2]),
        "name": str(row[3]),
        "description": str(row[4]),
        "body": str(row[5]),
        "created_at": str(row[6]),
        "updated_at": str(row[7]),
        "created_by": (str(row[8]) if row[8] is not None else None),
    }


_SELECT_COLS = "id, scope_type, scope_id, name, description, body, created_at, updated_at, created_by"


async def list_prompts_for_scope(
    db: DatabasePort, scope_type: ScopeType, scope_id: str,
) -> list[dict[str, object]]:
    """List named prompts for a single scope, alphabetical by name."""
    cursor = await db.execute(
        f"SELECT {_SELECT_COLS} FROM prompts "
        "WHERE scope_type = ? AND scope_id = ? "
        "ORDER BY name",
        (scope_type, scope_id),
    )
    return [_row_to_dict(row) for row in await cursor.fetchall()]


async def list_effective_prompts_for_set(
    db: DatabasePort, set_id: str,
) -> list[dict[str, object]]:
    """List a Set's own named prompts plus its parent collection's.

    Set-scoped names shadow Collection-scoped names with the same string.
    Order: own first (alphabetical), then inherited (alphabetical),
    excluding inherited entries whose names collide with own entries.
    """
    cursor = await db.execute("SELECT collection_id FROM sets WHERE id = ?", (set_id,))
    row = await cursor.fetchone()
    if row is None:
        return []
    parent_collection_id = row[0]

    own = await list_prompts_for_scope(db, "set", set_id)
    own_names = {p["name"] for p in own}

    inherited: list[dict[str, object]] = []
    if parent_collection_id is not None:
        for entry in await list_prompts_for_scope(db, "collection", str(parent_collection_id)):
            if entry["name"] not in own_names:
                inherited.append(entry)

    return own + inherited


async def list_prompts_for_collection_effective(
    db: DatabasePort, collection_id: str,
) -> list[dict[str, object]]:
    """A Collection has no parent — effective list is its own list."""
    return await list_prompts_for_scope(db, "collection", collection_id)


async def get_prompt(db: DatabasePort, prompt_id: str) -> dict[str, object] | None:
    cursor = await db.execute(
        f"SELECT {_SELECT_COLS} FROM prompts WHERE id = ?", (prompt_id,),
    )
    row = await cursor.fetchone()
    return _row_to_dict(row) if row is not None else None


async def _scope_exists(db: DatabasePort, scope_type: ScopeType, scope_id: str) -> bool:
    table = "collections" if scope_type == "collection" else "sets"
    cursor = await db.execute(
        f"SELECT 1 FROM {table} WHERE id = ? AND is_deleted = 0", (scope_id,),
    )
    return (await cursor.fetchone()) is not None


async def create_prompt(
    db: DatabasePort,
    *,
    scope_type: ScopeType,
    scope_id: str,
    name: str,
    description: str,
    body: str,
    created_by: str | None,
) -> dict[str, object]:
    """Insert a new named prompt.

    Raises ValueError("scope_not_found") if the scope does not exist.
    Raises IntegrityError on (scope_type, scope_id, name) collision —
    translated to HTTP 409 in the router.
    """
    if not await _scope_exists(db, scope_type, scope_id):
        raise ValueError("scope_not_found")

    prompt_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()
    await db.execute(
        "INSERT INTO prompts "
        "(id, scope_type, scope_id, name, description, body, created_at, updated_at, created_by) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (prompt_id, scope_type, scope_id, name, description, body, now, now, created_by),
    )
    await db.commit()
    return {
        "id": prompt_id,
        "scope_type": scope_type,
        "scope_id": scope_id,
        "name": name,
        "description": description,
        "body": body,
        "created_at": now,
        "updated_at": now,
        "created_by": created_by,
    }


async def update_prompt(
    db: DatabasePort,
    prompt_id: str,
    *,
    description: str | None = None,
    body: str | None = None,
) -> dict[str, object] | None:
    """Update mutable fields. Returns None if the prompt does not exist."""
    if description is None and body is None:
        return await get_prompt(db, prompt_id)

    sets: list[str] = []
    params: list[object] = []
    if description is not None:
        sets.append("description = ?")
        params.append(description)
    if body is not None:
        sets.append("body = ?")
        params.append(body)
    now = datetime.now(tz=UTC).isoformat()
    sets.append("updated_at = ?")
    params.append(now)
    params.append(prompt_id)

    cursor = await db.execute(
        f"UPDATE prompts SET {', '.join(sets)} WHERE id = ?", tuple(params),
    )
    if cursor.rowcount == 0:
        return None
    await db.commit()
    return await get_prompt(db, prompt_id)


async def delete_prompt(db: DatabasePort, prompt_id: str) -> bool:
    """Hard-delete a named prompt (no soft-delete column; cheap to recreate)."""
    cursor = await db.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))
    if cursor.rowcount == 0:
        return False
    await db.commit()
    return True
