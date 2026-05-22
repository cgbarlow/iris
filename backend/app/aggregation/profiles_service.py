"""CRUD service for aggregation_profiles (ADR-212, v6.20.0).

Same shape as element_templates/service.py — scope rules
(is_global ↔ set_id), JSON profile_data column, positional row access
(Protocol §15).
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from app.aggregation.exceptions import (
    AggregationProfileInvalid,
    AggregationProfileScopeError,
)
from app.aggregation.models import ProfileData

if TYPE_CHECKING:
    from app.db.adapter import DatabasePort


def _validate_scope(*, set_id: str | None, is_global: bool) -> None:
    """is_global=True ↔ set_id is None. Otherwise reject."""
    if is_global and set_id is not None:
        msg = "is_global profiles must not have a set_id"
        raise AggregationProfileScopeError(msg)
    if not is_global and set_id is None:
        msg = "non-global profiles require a set_id"
        raise AggregationProfileScopeError(msg)


def _validate_profile_data(data: dict[str, Any]) -> None:
    """Validate the profile_data JSON against ProfileData. Raises
    AggregationProfileInvalid on failure."""
    try:
        ProfileData(**data)
    except ValidationError as exc:
        raise AggregationProfileInvalid(str(exc)) from exc


async def create_aggregation_profile(
    db: DatabasePort,
    *,
    name: str,
    description: str | None,
    set_id: str | None,
    is_global: bool,
    profile_data: dict[str, Any],
    is_default_for_set: bool,
    created_by: str | None,
) -> dict[str, Any]:
    """Create a new profile."""
    _validate_scope(set_id=set_id, is_global=is_global)
    _validate_profile_data(profile_data)
    profile_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()
    await db.execute(
        "INSERT INTO aggregation_profiles ("
        "id, name, description, set_id, is_global, profile_data, "
        "is_default_for_set, created_by, created_at, updated_at"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            profile_id, name, description, set_id,
            1 if is_global else 0,
            json.dumps(profile_data),
            1 if is_default_for_set else 0,
            created_by, now, now,
        ),
    )
    await db.commit()
    return await get_aggregation_profile(db, profile_id)  # type: ignore[return-value]


async def get_aggregation_profile(
    db: DatabasePort, profile_id: str,
) -> dict[str, Any] | None:
    """Fetch one profile, joined with sets + users for denormalised
    names."""
    cursor = await db.execute(
        "SELECT p.id, p.name, p.description, p.set_id, s.name, "
        "p.is_global, p.is_default_for_set, p.profile_data, "
        "p.created_by, u.username, p.created_at, p.updated_at "
        "FROM aggregation_profiles p "
        "LEFT JOIN sets s ON s.id = p.set_id "
        "LEFT JOIN users u ON u.id = p.created_by "
        "WHERE p.id = ? AND p.is_deleted = 0",
        (profile_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    return {
        "id": row[0],
        "name": row[1],
        "description": row[2],
        "set_id": row[3],
        "set_name": row[4],
        "is_global": bool(row[5]),
        "is_default_for_set": bool(row[6]),
        "profile_data": json.loads(row[7]) if row[7] else {},
        "created_by": row[8],
        "created_by_username": row[9] or "Unknown",
        "created_at": row[10],
        "updated_at": row[11],
    }


async def list_aggregation_profiles(
    db: DatabasePort,
    *,
    set_id: str | None = None,
    include_global: bool = True,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[dict[str, Any]], int]:
    """List with set + global scope filter. Same semantics as
    element_templates.list."""
    where_parts = ["p.is_deleted = 0"]
    params: list[Any] = []
    if set_id is not None and include_global:
        where_parts.append("(p.set_id = ? OR p.is_global = 1)")
        params.append(set_id)
    elif set_id is not None:
        where_parts.append("p.set_id = ?")
        params.append(set_id)
    elif include_global:
        where_parts.append("p.is_global = 1")
    else:
        return [], 0
    where_sql = " AND ".join(where_parts)

    count_cursor = await db.execute(
        f"SELECT COUNT(*) FROM aggregation_profiles p WHERE {where_sql}",
        tuple(params),
    )
    count_row = await count_cursor.fetchone()
    total: int = count_row[0] if count_row else 0

    offset = (page - 1) * page_size
    list_cursor = await db.execute(
        "SELECT p.id, p.name, p.description, p.set_id, s.name, "
        "p.is_global, p.is_default_for_set, p.profile_data, "
        "p.created_by, u.username, p.created_at, p.updated_at "
        "FROM aggregation_profiles p "
        "LEFT JOIN sets s ON s.id = p.set_id "
        "LEFT JOIN users u ON u.id = p.created_by "
        f"WHERE {where_sql} "
        "ORDER BY p.is_global DESC, p.name ASC "
        "LIMIT ? OFFSET ?",
        (*params, page_size, offset),
    )
    rows = await list_cursor.fetchall()
    items = [
        {
            "id": r[0],
            "name": r[1],
            "description": r[2],
            "set_id": r[3],
            "set_name": r[4],
            "is_global": bool(r[5]),
            "is_default_for_set": bool(r[6]),
            "profile_data": json.loads(r[7]) if r[7] else {},
            "created_by": r[8],
            "created_by_username": r[9] or "Unknown",
            "created_at": r[10],
            "updated_at": r[11],
        }
        for r in rows
    ]
    return items, total


async def update_aggregation_profile(
    db: DatabasePort,
    profile_id: str,
    *,
    name: str | None = None,
    description: str | None = None,
    set_id: str | None | type[Ellipsis] = ...,
    is_global: bool | None = None,
    profile_data: dict[str, Any] | None = None,
    is_default_for_set: bool | None = None,
) -> dict[str, Any] | None:
    """Edit a profile. Profiles are not versioned."""
    existing = await get_aggregation_profile(db, profile_id)
    if existing is None:
        return None

    new_name = name if name is not None else existing["name"]
    new_description = (
        description if description is not None else existing["description"]
    )
    new_is_global = (
        is_global if is_global is not None else existing["is_global"]
    )
    new_set_id: str | None
    if set_id is ...:
        new_set_id = existing["set_id"]
    else:
        new_set_id = set_id
    _validate_scope(set_id=new_set_id, is_global=new_is_global)

    new_data: dict[str, Any]
    if profile_data is not None:
        _validate_profile_data(profile_data)
        new_data = profile_data
    else:
        new_data = existing["profile_data"]

    new_default = (
        is_default_for_set
        if is_default_for_set is not None
        else existing["is_default_for_set"]
    )

    now = datetime.now(tz=UTC).isoformat()
    await db.execute(
        "UPDATE aggregation_profiles SET "
        "name = ?, description = ?, set_id = ?, is_global = ?, "
        "profile_data = ?, is_default_for_set = ?, updated_at = ? "
        "WHERE id = ? AND is_deleted = 0",
        (
            new_name, new_description, new_set_id,
            1 if new_is_global else 0,
            json.dumps(new_data),
            1 if new_default else 0,
            now,
            profile_id,
        ),
    )
    await db.commit()
    return await get_aggregation_profile(db, profile_id)


async def delete_aggregation_profile(
    db: DatabasePort, profile_id: str,
) -> bool:
    """Soft-delete. Returns True if a row was updated."""
    cursor = await db.execute(
        "UPDATE aggregation_profiles SET is_deleted = 1 "
        "WHERE id = ? AND is_deleted = 0",
        (profile_id,),
    )
    await db.commit()
    return (cursor.rowcount or 0) > 0
