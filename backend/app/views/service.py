"""Service layer for admin-configurable views."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


async def create_view(
    db: aiosqlite.Connection,
    *,
    name: str,
    description: str | None = None,
    config: dict[str, object] | None = None,
    is_default: bool = False,
    created_by: str,
) -> dict[str, object]:
    """Create a new view."""
    view_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()
    await db.execute(
        "INSERT INTO views (id, name, description, config, is_default, created_by, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (view_id, name, description, json.dumps(config or {}), int(is_default), created_by, now, now),
    )
    await db.commit()
    return {
        "id": view_id,
        "name": name,
        "description": description,
        "config": config or {},
        "is_default": is_default,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }


async def list_views(
    db: aiosqlite.Connection,
) -> list[dict[str, object]]:
    """List all views."""
    cursor = await db.execute(
        "SELECT id, name, description, config, is_default, created_by, created_at, updated_at "
        "FROM views ORDER BY is_default DESC, name ASC"
    )
    rows = await cursor.fetchall()
    return [
        {
            "id": r[0],
            "name": r[1],
            "description": r[2],
            "config": json.loads(r[3]) if r[3] else {},
            "is_default": bool(r[4]),
            "created_by": r[5],
            "created_at": r[6],
            "updated_at": r[7],
        }
        for r in rows
    ]


async def get_view(
    db: aiosqlite.Connection,
    view_id: str,
) -> dict[str, object] | None:
    """Get a single view by ID."""
    cursor = await db.execute(
        "SELECT id, name, description, config, is_default, created_by, created_at, updated_at "
        "FROM views WHERE id = ?",
        (view_id,),
    )
    r = await cursor.fetchone()
    if r is None:
        return None
    return {
        "id": r[0],
        "name": r[1],
        "description": r[2],
        "config": json.loads(r[3]) if r[3] else {},
        "is_default": bool(r[4]),
        "created_by": r[5],
        "created_at": r[6],
        "updated_at": r[7],
    }


async def update_view(
    db: aiosqlite.Connection,
    view_id: str,
    *,
    name: str,
    description: str | None = None,
    config: dict[str, object] | None = None,
) -> dict[str, object] | None:
    """Update a view. Returns None if not found."""
    now = datetime.now(tz=UTC).isoformat()
    cursor = await db.execute(
        "UPDATE views SET name = ?, description = ?, config = ?, updated_at = ? WHERE id = ?",
        (name, description, json.dumps(config or {}), now, view_id),
    )
    if cursor.rowcount == 0:
        return None
    await db.commit()
    return await get_view(db, view_id)


async def delete_view(
    db: aiosqlite.Connection,
    view_id: str,
) -> bool:
    """Delete a view. Returns False if not found or is default."""
    # Prevent deleting default views
    cursor = await db.execute(
        "SELECT is_default FROM views WHERE id = ?",
        (view_id,),
    )
    row = await cursor.fetchone()
    if row is None or row[0]:
        return False
    await db.execute("DELETE FROM views WHERE id = ?", (view_id,))
    await db.commit()
    return True


async def seed_default_views(db: aiosqlite.Connection) -> None:
    """Seed default views if none exist."""
    cursor = await db.execute("SELECT COUNT(*) FROM views")
    count = (await cursor.fetchone())[0]
    if count > 0:
        return

    now = datetime.now(tz=UTC).isoformat()

    # Standard view — simplified, hides advanced features
    standard_config = {
        "toolbar": {
            "element_types": [
                "component", "service", "interface", "package", "actor", "database", "queue",
                "person", "software_system", "container", "c4_component",
            ],
            "relationship_types": [
                "uses", "depends_on", "composes", "implements", "contains",
                "c4_relationship",
            ],
            "show_routing_type": False,
            "show_edge_properties": False,
        },
        "metadata": {
            "show_overview": True,
            "show_details": True,
            "show_extended": False,
        },
        "canvas": {
            "show_cardinality": False,
            "show_role_names": False,
            "show_stereotypes": False,
            "show_description_on_nodes": True,
        },
    }

    await db.execute(
        "INSERT INTO views (id, name, description, config, is_default, created_by, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("standard", "Standard", "Simplified view for common use", json.dumps(standard_config), 1, "system", now, now),
    )

    # Advanced view — full functionality
    advanced_config = {
        "toolbar": {
            "element_types": [],
            "relationship_types": [],
            "show_routing_type": True,
            "show_edge_properties": True,
        },
        "metadata": {
            "show_overview": True,
            "show_details": True,
            "show_extended": True,
        },
        "canvas": {
            "show_cardinality": True,
            "show_role_names": True,
            "show_stereotypes": True,
            "show_description_on_nodes": True,
        },
    }

    await db.execute(
        "INSERT INTO views (id, name, description, config, is_default, created_by, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("advanced", "Advanced", "Full functionality visible", json.dumps(advanced_config), 1, "system", now, now),
    )

    await db.commit()
