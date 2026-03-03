"""Model relationship CRUD service per SPEC-066-A."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


async def create_model_relationship(
    db: aiosqlite.Connection,
    *,
    source_model_id: str,
    target_model_id: str,
    relationship_type: str,
    label: str | None = None,
    description: str | None = None,
    created_by: str,
) -> dict[str, object]:
    """Create a model-to-model relationship."""
    rel_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()

    await db.execute(
        "INSERT INTO model_relationships "
        "(id, source_model_id, target_model_id, relationship_type, label, description, "
        "created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (rel_id, source_model_id, target_model_id, relationship_type,
         label, description, created_by, now),
    )
    await db.commit()

    return {
        "id": rel_id,
        "source_model_id": source_model_id,
        "target_model_id": target_model_id,
        "relationship_type": relationship_type,
        "label": label,
        "description": description,
        "created_by": created_by,
        "created_at": now,
    }


async def list_model_relationships(
    db: aiosqlite.Connection,
    model_id: str,
) -> list[dict[str, object]]:
    """List all relationships where model_id is source or target."""
    cursor = await db.execute(
        "SELECT mr.id, mr.source_model_id, mr.target_model_id, "
        "mr.relationship_type, mr.label, mr.description, "
        "mr.created_by, mr.created_at, "
        "smv.name AS source_name, tmv.name AS target_name "
        "FROM model_relationships mr "
        "JOIN models sm ON mr.source_model_id = sm.id "
        "JOIN model_versions smv ON sm.id = smv.model_id AND sm.current_version = smv.version "
        "JOIN models tm ON mr.target_model_id = tm.id "
        "JOIN model_versions tmv ON tm.id = tmv.model_id AND tm.current_version = tmv.version "
        "WHERE mr.source_model_id = ? OR mr.target_model_id = ? "
        "ORDER BY mr.created_at DESC",
        (model_id, model_id),
    )
    rows = await cursor.fetchall()
    return [
        {
            "id": r[0],
            "source_model_id": r[1],
            "target_model_id": r[2],
            "relationship_type": r[3],
            "label": r[4],
            "description": r[5],
            "created_by": r[6],
            "created_at": r[7],
            "source_name": r[8],
            "target_name": r[9],
        }
        for r in rows
    ]


async def list_entity_relationships_for_model(
    db: aiosqlite.Connection,
    model_id: str,
) -> list[dict[str, object]]:
    """List entity-to-entity relationships for entities on a model's canvas."""
    # Get model's canvas data to extract entity IDs
    cursor = await db.execute(
        "SELECT mv.data FROM models m "
        "JOIN model_versions mv ON m.id = mv.model_id AND m.current_version = mv.version "
        "WHERE m.id = ? AND m.is_deleted = 0",
        (model_id,),
    )
    row = await cursor.fetchone()
    if not row or not row[0]:
        return []

    try:
        data = json.loads(row[0]) if isinstance(row[0], str) else row[0]
    except (json.JSONDecodeError, TypeError):
        return []

    nodes = data.get("nodes", [])
    entity_ids: set[str] = set()
    for node in nodes:
        node_data = node.get("data", {})
        if isinstance(node_data, dict):
            eid = node_data.get("entityId")
            if eid:
                entity_ids.add(eid)

    if not entity_ids:
        return []

    # Query relationships where both source and target are in this model's entities
    placeholders = ",".join("?" for _ in entity_ids)
    id_list = list(entity_ids)
    cursor = await db.execute(
        f"SELECT r.id, r.source_entity_id, r.target_entity_id, "  # noqa: S608
        f"r.relationship_type, rv.label, rv.description, "
        f"r.created_by, r.created_at, "
        f"sev.name AS source_name, tev.name AS target_name "
        f"FROM relationships r "
        f"JOIN relationship_versions rv ON r.id = rv.relationship_id "
        f"  AND r.current_version = rv.version "
        f"LEFT JOIN entities se ON r.source_entity_id = se.id "
        f"LEFT JOIN entity_versions sev ON se.id = sev.entity_id "
        f"  AND se.current_version = sev.version "
        f"LEFT JOIN entities te ON r.target_entity_id = te.id "
        f"LEFT JOIN entity_versions tev ON te.id = tev.entity_id "
        f"  AND te.current_version = tev.version "
        f"WHERE r.is_deleted = 0 "
        f"  AND (r.source_entity_id IN ({placeholders}) "
        f"       OR r.target_entity_id IN ({placeholders})) "
        f"ORDER BY r.created_at DESC",
        id_list + id_list,
    )
    rows = await cursor.fetchall()
    return [
        {
            "id": r[0],
            "source_entity_id": r[1],
            "target_entity_id": r[2],
            "relationship_type": r[3],
            "label": r[4],
            "description": r[5],
            "created_by": r[6],
            "created_at": r[7],
            "source_name": r[8] or "",
            "target_name": r[9] or "",
        }
        for r in rows
    ]


async def list_all_relationships_for_model(
    db: aiosqlite.Connection,
    model_id: str,
) -> dict[str, list[dict[str, object]]]:
    """Return both model-to-model and entity-to-entity relationships for a model."""
    model_rels = await list_model_relationships(db, model_id)
    entity_rels = await list_entity_relationships_for_model(db, model_id)
    return {
        "model_relationships": model_rels,
        "entity_relationships": entity_rels,
    }


async def delete_model_relationship(
    db: aiosqlite.Connection,
    relationship_id: str,
) -> bool:
    """Delete a model relationship. Returns False if not found."""
    cursor = await db.execute(
        "DELETE FROM model_relationships WHERE id = ?",
        (relationship_id,),
    )
    await db.commit()
    return cursor.rowcount > 0
