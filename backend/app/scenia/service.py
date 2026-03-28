"""Scenia roadmapping service — CRUD for entities stored as Iris elements/relationships."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.migrations.m012_sets import DEFAULT_SET_ID

if TYPE_CHECKING:
    from app.db.adapter import DatabasePort

# Scenia element types (stored in elements.element_type)
ENTITY_TYPES = {
    "strategies": "scenia_strategy",
    "programmes": "scenia_programme",
    "initiatives": "scenia_initiative",
    "assets": "scenia_asset",
    "applications": "scenia_application",
    "app_segments": "scenia_app_segment",
    "milestones": "scenia_milestone",
    "resources": "scenia_resource",
}

DEPENDENCY_TYPE = "scenia_dependency"


# ---------------------------------------------------------------------------
# Generic element-backed CRUD
# ---------------------------------------------------------------------------


async def create_scenia_entity(
    db: DatabasePort,
    *,
    element_type: str,
    name: str,
    description: str | None,
    data: dict[str, object],
    set_id: str,
    created_by: str,
    element_id: str | None = None,
) -> dict[str, object]:
    """Create a Scenia entity as an Iris element."""
    element_id = element_id or str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()
    data_json = json.dumps(data)
    effective_set_id = set_id or DEFAULT_SET_ID

    await db.execute(
        "INSERT INTO elements (id, element_type, current_version, "
        "created_at, created_by, updated_at, set_id, notation) VALUES (?, ?, 1, ?, ?, ?, ?, ?)",
        (element_id, element_type, now, created_by, now, effective_set_id, "scenia"),
    )
    await db.execute(
        "INSERT INTO element_versions (element_id, version, name, description, "
        "data, change_type, change_summary, created_at, created_by) "
        "VALUES (?, 1, ?, ?, ?, 'create', ?, ?, ?)",
        (element_id, name, description, data_json, f"Create {element_type}", now, created_by),
    )
    await db.commit()

    return {
        "id": element_id,
        "element_type": element_type,
        "name": name,
        "description": description,
        "data": data,
        "set_id": effective_set_id,
        "created_at": now,
        "updated_at": now,
    }


async def get_scenia_entity(
    db: DatabasePort,
    element_id: str,
) -> dict[str, object] | None:
    """Get a single Scenia entity."""
    cursor = await db.execute(
        "SELECT e.id, e.element_type, ev.name, ev.description, ev.data, "
        "e.set_id, e.created_at, e.updated_at "
        "FROM elements e "
        "JOIN element_versions ev ON e.id = ev.element_id AND e.current_version = ev.version "
        "WHERE e.id = ? AND e.is_deleted = 0 AND e.element_type LIKE 'scenia_%'",
        (element_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    return {
        "id": row[0],
        "element_type": row[1],
        "name": row[2],
        "description": row[3],
        "data": json.loads(row[4]) if row[4] else {},
        "set_id": row[5],
        "created_at": row[6],
        "updated_at": row[7],
    }


async def list_scenia_entities(
    db: DatabasePort,
    element_type: str,
    *,
    set_id: str | None = None,
) -> list[dict[str, object]]:
    """List Scenia entities of a given type, optionally filtered by set."""
    where = "e.is_deleted = 0 AND e.element_type = ?"
    params: list[object] = [element_type]

    if set_id:
        where += " AND e.set_id = ?"
        params.append(set_id)

    cursor = await db.execute(
        f"SELECT e.id, e.element_type, ev.name, ev.description, ev.data, "  # noqa: S608
        "e.set_id, e.created_at, e.updated_at "
        "FROM elements e "
        "JOIN element_versions ev ON e.id = ev.element_id AND e.current_version = ev.version "
        f"WHERE {where} ORDER BY ev.name",
        tuple(params),
    )
    rows = await cursor.fetchall()
    return [
        {
            "id": r[0],
            "element_type": r[1],
            "name": r[2],
            "description": r[3],
            "data": json.loads(r[4]) if r[4] else {},
            "set_id": r[5],
            "created_at": r[6],
            "updated_at": r[7],
        }
        for r in rows
    ]


async def update_scenia_entity(
    db: DatabasePort,
    element_id: str,
    *,
    name: str,
    description: str | None,
    data: dict[str, object],
    updated_by: str,
) -> dict[str, object] | None:
    """Update a Scenia entity by creating a new version."""
    cursor = await db.execute(
        "SELECT current_version FROM elements WHERE id = ? AND is_deleted = 0 "
        "AND element_type LIKE 'scenia_%'",
        (element_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None

    new_version = row[0] + 1
    now = datetime.now(tz=UTC).isoformat()
    data_json = json.dumps(data)

    await db.execute(
        "UPDATE elements SET current_version = ?, updated_at = ? WHERE id = ?",
        (new_version, now, element_id),
    )
    await db.execute(
        "INSERT INTO element_versions (element_id, version, name, description, "
        "data, change_type, change_summary, created_at, created_by) "
        "VALUES (?, ?, ?, ?, ?, 'update', ?, ?, ?)",
        (element_id, new_version, name, description, data_json, "Update via Scenia", now, updated_by),
    )
    await db.commit()

    return await get_scenia_entity(db, element_id)


async def delete_scenia_entity(
    db: DatabasePort,
    element_id: str,
) -> bool:
    """Soft-delete a Scenia entity. Returns True if found."""
    cursor = await db.execute(
        "SELECT id FROM elements WHERE id = ? AND is_deleted = 0 "
        "AND element_type LIKE 'scenia_%'",
        (element_id,),
    )
    if await cursor.fetchone() is None:
        return False

    now = datetime.now(tz=UTC).isoformat()
    await db.execute(
        "UPDATE elements SET is_deleted = 1, updated_at = ? WHERE id = ?",
        (now, element_id),
    )
    await db.commit()
    return True


# ---------------------------------------------------------------------------
# Dependencies (relationship-backed)
# ---------------------------------------------------------------------------


async def create_scenia_dependency(
    db: DatabasePort,
    *,
    source_id: str,
    target_id: str,
    dependency_type: str,
    set_id: str,
    data: dict[str, object],
    created_by: str,
    rel_id: str | None = None,
) -> dict[str, object]:
    """Create a Scenia dependency as an Iris relationship."""
    rel_id = rel_id or str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()
    dep_data = {**data, "dependency_type": dependency_type, "set_id": set_id}
    data_json = json.dumps(dep_data)

    await db.execute(
        "INSERT INTO relationships "
        "(id, source_element_id, target_element_id, relationship_type, "
        "current_version, created_at, created_by, updated_at) "
        "VALUES (?, ?, ?, ?, 1, ?, ?, ?)",
        (rel_id, source_id, target_id, DEPENDENCY_TYPE, now, created_by, now),
    )
    await db.execute(
        "INSERT INTO relationship_versions "
        "(relationship_id, version, label, description, data, "
        "change_type, created_at, created_by) "
        "VALUES (?, 1, ?, ?, ?, 'create', ?, ?)",
        (rel_id, dependency_type, None, data_json, now, created_by),
    )
    await db.commit()

    return {
        "id": rel_id,
        "source_id": source_id,
        "target_id": target_id,
        "dependency_type": dependency_type,
        "set_id": set_id,
        "data": data,
        "created_at": now,
    }


async def list_scenia_dependencies(
    db: DatabasePort,
    *,
    set_id: str | None = None,
) -> list[dict[str, object]]:
    """List Scenia dependencies, optionally filtered by set_id stored in data."""
    cursor = await db.execute(
        "SELECT r.id, r.source_element_id, r.target_element_id, "
        "rv.label, rv.data, r.created_at "
        "FROM relationships r "
        "JOIN relationship_versions rv ON r.id = rv.relationship_id "
        "AND r.current_version = rv.version "
        "WHERE r.relationship_type = ? AND r.is_deleted = 0 "
        "ORDER BY r.created_at",
        (DEPENDENCY_TYPE,),
    )
    rows = await cursor.fetchall()
    results = []
    for r in rows:
        data = json.loads(r[4]) if r[4] else {}
        row_set_id = data.pop("set_id", None)
        dep_type = data.pop("dependency_type", r[3] or "blocks")
        if set_id and row_set_id != set_id:
            continue
        results.append({
            "id": r[0],
            "source_id": r[1],
            "target_id": r[2],
            "dependency_type": dep_type,
            "set_id": row_set_id,
            "data": data,
            "created_at": r[5],
        })
    return results


async def delete_scenia_dependency(
    db: DatabasePort,
    dependency_id: str,
) -> bool:
    """Soft-delete a Scenia dependency. Returns True if found."""
    cursor = await db.execute(
        "SELECT id FROM relationships WHERE id = ? AND relationship_type = ? AND is_deleted = 0",
        (dependency_id, DEPENDENCY_TYPE),
    )
    if await cursor.fetchone() is None:
        return False

    now = datetime.now(tz=UTC).isoformat()
    await db.execute(
        "UPDATE relationships SET is_deleted = 1, updated_at = ? WHERE id = ?",
        (now, dependency_id),
    )
    await db.commit()
    return True


# ---------------------------------------------------------------------------
# Timeline settings
# ---------------------------------------------------------------------------


async def get_timeline_settings(
    db: DatabasePort,
    set_id: str,
) -> dict[str, object] | None:
    """Get timeline settings for a set."""
    cursor = await db.execute(
        "SELECT id, set_id, start_date, end_date, view_mode, zoom_level, data, updated_at "
        "FROM scenia_timeline_settings WHERE set_id = ?",
        (set_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    return {
        "id": row[0],
        "set_id": row[1],
        "start_date": row[2],
        "end_date": row[3],
        "view_mode": row[4],
        "zoom_level": row[5],
        "data": json.loads(row[6]) if row[6] else {},
        "updated_at": row[7],
    }


async def upsert_timeline_settings(
    db: DatabasePort,
    set_id: str,
    *,
    start_date: str | None,
    end_date: str | None,
    view_mode: str,
    zoom_level: float,
    data: dict[str, object],
) -> dict[str, object]:
    """Create or update timeline settings for a set."""
    now = datetime.now(tz=UTC).isoformat()
    data_json = json.dumps(data)

    existing = await get_timeline_settings(db, set_id)
    if existing:
        await db.execute(
            "UPDATE scenia_timeline_settings SET start_date = ?, end_date = ?, "
            "view_mode = ?, zoom_level = ?, data = ?, updated_at = ? WHERE set_id = ?",
            (start_date, end_date, view_mode, zoom_level, data_json, now, set_id),
        )
    else:
        settings_id = str(uuid.uuid4())
        await db.execute(
            "INSERT INTO scenia_timeline_settings "
            "(id, set_id, start_date, end_date, view_mode, zoom_level, data, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (settings_id, set_id, start_date, end_date, view_mode, zoom_level, data_json, now),
        )
    await db.commit()

    return (await get_timeline_settings(db, set_id))  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Asset categories
# ---------------------------------------------------------------------------


async def create_asset_category(
    db: DatabasePort,
    *,
    set_id: str,
    name: str,
    color: str | None,
    display_order: int,
    cat_id: str | None = None,
) -> dict[str, object]:
    """Create an asset category."""
    cat_id = cat_id or str(uuid.uuid4())
    await db.execute(
        "INSERT INTO scenia_asset_categories (id, set_id, name, color, display_order) "
        "VALUES (?, ?, ?, ?, ?)",
        (cat_id, set_id, name, color, display_order),
    )
    await db.commit()
    return {"id": cat_id, "set_id": set_id, "name": name, "color": color, "display_order": display_order}


async def list_asset_categories(
    db: DatabasePort,
    set_id: str,
) -> list[dict[str, object]]:
    """List asset categories for a set."""
    cursor = await db.execute(
        "SELECT id, set_id, name, color, display_order "
        "FROM scenia_asset_categories WHERE set_id = ? ORDER BY display_order",
        (set_id,),
    )
    rows = await cursor.fetchall()
    return [
        {"id": r[0], "set_id": r[1], "name": r[2], "color": r[3], "display_order": r[4]}
        for r in rows
    ]


async def delete_asset_category(
    db: DatabasePort,
    category_id: str,
) -> bool:
    """Delete an asset category. Returns True if found."""
    cursor = await db.execute(
        "SELECT id FROM scenia_asset_categories WHERE id = ?", (category_id,)
    )
    if await cursor.fetchone() is None:
        return False
    await db.execute("DELETE FROM scenia_asset_categories WHERE id = ?", (category_id,))
    await db.commit()
    return True


# ---------------------------------------------------------------------------
# Application statuses
# ---------------------------------------------------------------------------


async def create_app_status(
    db: DatabasePort,
    *,
    set_id: str,
    name: str,
    color: str | None,
    display_order: int,
    status_id: str | None = None,
) -> dict[str, object]:
    """Create an application status."""
    status_id = status_id or str(uuid.uuid4())
    await db.execute(
        "INSERT INTO scenia_application_statuses (id, set_id, name, color, display_order) "
        "VALUES (?, ?, ?, ?, ?)",
        (status_id, set_id, name, color, display_order),
    )
    await db.commit()
    return {"id": status_id, "set_id": set_id, "name": name, "color": color, "display_order": display_order}


async def list_app_statuses(
    db: DatabasePort,
    set_id: str,
) -> list[dict[str, object]]:
    """List application statuses for a set."""
    cursor = await db.execute(
        "SELECT id, set_id, name, color, display_order "
        "FROM scenia_application_statuses WHERE set_id = ? ORDER BY display_order",
        (set_id,),
    )
    rows = await cursor.fetchall()
    return [
        {"id": r[0], "set_id": r[1], "name": r[2], "color": r[3], "display_order": r[4]}
        for r in rows
    ]


async def delete_app_status(
    db: DatabasePort,
    status_id: str,
) -> bool:
    """Delete an application status. Returns True if found."""
    cursor = await db.execute(
        "SELECT id FROM scenia_application_statuses WHERE id = ?", (status_id,)
    )
    if await cursor.fetchone() is None:
        return False
    await db.execute("DELETE FROM scenia_application_statuses WHERE id = ?", (status_id,))
    await db.commit()
    return True


# ---------------------------------------------------------------------------
# Versions
# ---------------------------------------------------------------------------


async def create_version(
    db: DatabasePort,
    *,
    set_id: str,
    name: str | None,
    data: dict[str, object],
    created_by: str,
) -> dict[str, object]:
    """Create a version snapshot."""
    version_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()
    data_json = json.dumps(data)

    # Get next version number
    cursor = await db.execute(
        "SELECT COALESCE(MAX(version_number), 0) FROM scenia_versions WHERE set_id = ?",
        (set_id,),
    )
    row = await cursor.fetchone()
    next_version = row[0] + 1

    await db.execute(
        "INSERT INTO scenia_versions (id, set_id, version_number, name, data, created_at, created_by) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (version_id, set_id, next_version, name, data_json, now, created_by),
    )
    await db.commit()
    return {
        "id": version_id,
        "set_id": set_id,
        "version_number": next_version,
        "name": name,
        "data": data,
        "created_at": now,
        "created_by": created_by,
    }


async def list_versions(
    db: DatabasePort,
    set_id: str,
) -> list[dict[str, object]]:
    """List version snapshots for a set."""
    cursor = await db.execute(
        "SELECT id, set_id, version_number, name, data, created_at, created_by "
        "FROM scenia_versions WHERE set_id = ? ORDER BY version_number DESC",
        (set_id,),
    )
    rows = await cursor.fetchall()
    return [
        {
            "id": r[0],
            "set_id": r[1],
            "version_number": r[2],
            "name": r[3],
            "data": json.loads(r[4]) if r[4] else {},
            "created_at": r[5],
            "created_by": r[6],
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Bulk data (primary integration point)
# ---------------------------------------------------------------------------


async def get_bulk_data(
    db: DatabasePort,
    set_id: str,
) -> dict[str, object]:
    """Get all Scenia data for a set — matches Scenia's getAppData() shape."""
    result: dict[str, object] = {}

    # Load all element-backed entities
    for key, etype in ENTITY_TYPES.items():
        result[key] = await list_scenia_entities(db, etype, set_id=set_id)

    # Dependencies
    result["dependencies"] = await list_scenia_dependencies(db, set_id=set_id)

    # Lookup tables
    result["asset_categories"] = await list_asset_categories(db, set_id)
    result["app_statuses"] = await list_app_statuses(db, set_id)

    # Timeline settings
    result["timeline_settings"] = await get_timeline_settings(db, set_id)

    # Versions
    result["versions"] = await list_versions(db, set_id)

    return result


async def _upsert_entity(
    db: DatabasePort,
    *,
    element_id: str,
    element_type: str,
    name: str,
    description: str | None,
    data: dict[str, object],
    set_id: str,
    updated_by: str,
) -> None:
    """Insert or update a single Scenia entity."""
    now = datetime.now(tz=UTC).isoformat()
    data_json = json.dumps(data)

    cursor = await db.execute(
        "SELECT id, current_version FROM elements WHERE id = ?",
        (element_id,),
    )
    row = await cursor.fetchone()

    if row:
        # Update existing — bump version, un-delete if needed
        new_version = row[1] + 1
        await db.execute(
            "UPDATE elements SET current_version = ?, updated_at = ?, is_deleted = 0 WHERE id = ?",
            (new_version, now, element_id),
        )
        await db.execute(
            "INSERT INTO element_versions (element_id, version, name, description, "
            "data, change_type, change_summary, created_at, created_by) "
            "VALUES (?, ?, ?, ?, ?, 'update', ?, ?, ?)",
            (element_id, new_version, name, description, data_json, "Update via Scenia", now, updated_by),
        )
    else:
        # Create new
        await create_scenia_entity(
            db,
            element_type=element_type,
            name=name,
            description=description,
            data=data,
            set_id=set_id,
            created_by=updated_by,
            element_id=element_id,
        )


async def save_bulk_data(
    db: DatabasePort,
    set_id: str,
    *,
    data: dict[str, object],
    saved_by: str,
) -> dict[str, object]:
    """Granular save of all Scenia data for a set.

    For each entity type, upserts items present in the payload and
    soft-deletes items that are no longer present. Preserves IDs
    so cross-references remain stable.
    """
    now = datetime.now(tz=UTC).isoformat()

    # --- Element-backed entities: upsert + prune ---
    for key, etype in ENTITY_TYPES.items():
        incoming = data.get(key, [])
        if not isinstance(incoming, list):
            continue

        incoming_ids = set()
        for entity in incoming:
            eid = entity.get("id") or str(uuid.uuid4())
            incoming_ids.add(eid)
            await _upsert_entity(
                db,
                element_id=eid,
                element_type=etype,
                name=entity.get("name", "Untitled"),
                description=entity.get("description"),
                data=entity.get("data", {}),
                set_id=set_id,
                updated_by=saved_by,
            )

        # Soft-delete entities of this type that aren't in the payload
        cursor = await db.execute(
            "SELECT id FROM elements WHERE element_type = ? AND set_id = ? AND is_deleted = 0",
            (etype, set_id),
        )
        existing = await cursor.fetchall()
        for row in existing:
            if row[0] not in incoming_ids:
                await db.execute(
                    "UPDATE elements SET is_deleted = 1, updated_at = ? WHERE id = ?",
                    (now, row[0]),
                )

    # --- Dependencies: replace (these are lightweight) ---
    incoming_deps = data.get("dependencies", [])
    if isinstance(incoming_deps, list):
        incoming_dep_ids = set()
        for dep in incoming_deps:
            dep_id = dep.get("id") or str(uuid.uuid4())
            incoming_dep_ids.add(dep_id)

            # Check if exists
            cursor = await db.execute(
                "SELECT id FROM relationships WHERE id = ?", (dep_id,)
            )
            if await cursor.fetchone():
                # Update
                dep_data = {**dep.get("data", {}), "dependency_type": dep.get("dependency_type", "blocks"), "set_id": set_id}
                await db.execute(
                    "UPDATE relationships SET source_element_id = ?, target_element_id = ?, "
                    "updated_at = ?, is_deleted = 0 WHERE id = ?",
                    (dep.get("source_id", ""), dep.get("target_id", ""), now, dep_id),
                )
            else:
                await create_scenia_dependency(
                    db,
                    source_id=dep.get("source_id", ""),
                    target_id=dep.get("target_id", ""),
                    dependency_type=dep.get("dependency_type", "blocks"),
                    set_id=set_id,
                    data=dep.get("data", {}),
                    created_by=saved_by,
                    rel_id=dep_id,
                )

        # Soft-delete removed dependencies
        cursor = await db.execute(
            "SELECT id FROM relationships WHERE relationship_type = ? AND is_deleted = 0",
            (DEPENDENCY_TYPE,),
        )
        existing_deps = await cursor.fetchall()
        for row in existing_deps:
            if row[0] not in incoming_dep_ids:
                await db.execute(
                    "UPDATE relationships SET is_deleted = 1, updated_at = ? WHERE id = ?",
                    (now, row[0]),
                )

    # --- Lookup tables: replace (small, no FK issues) ---
    await db.execute("DELETE FROM scenia_asset_categories WHERE set_id = ?", (set_id,))
    cats = data.get("asset_categories", [])
    if isinstance(cats, list):
        for cat in cats:
            await create_asset_category(
                db,
                set_id=set_id,
                name=cat.get("name", "Untitled"),
                color=cat.get("color"),
                display_order=cat.get("display_order", 0),
                cat_id=cat.get("id"),
            )

    await db.execute("DELETE FROM scenia_application_statuses WHERE set_id = ?", (set_id,))
    statuses = data.get("app_statuses", [])
    if isinstance(statuses, list):
        for status in statuses:
            await create_app_status(
                db,
                set_id=set_id,
                name=status.get("name", "Untitled"),
                color=status.get("color"),
                display_order=status.get("display_order", 0),
                status_id=status.get("id"),
            )

    # --- Timeline settings: upsert ---
    ts = data.get("timeline_settings")
    if isinstance(ts, dict):
        await upsert_timeline_settings(
            db,
            set_id,
            start_date=ts.get("start_date"),
            end_date=ts.get("end_date"),
            view_mode=str(ts.get("view_mode", "quarterly")),
            zoom_level=float(ts.get("zoom_level", 1.0)),
            data=ts.get("data", {}),
        )

    await db.commit()
    return await get_bulk_data(db, set_id)


# ---------------------------------------------------------------------------
# Cross-link check
# ---------------------------------------------------------------------------


async def get_element_scenia_link(
    db: DatabasePort,
    element_id: str,
) -> dict[str, object] | None:
    """Check if an element is a Scenia entity and return link info."""
    cursor = await db.execute(
        "SELECT e.id, e.element_type, e.set_id FROM elements e "
        "WHERE e.id = ? AND e.is_deleted = 0 AND e.element_type LIKE 'scenia_%'",
        (element_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    return {"element_id": row[0], "element_type": row[1], "set_id": row[2]}
