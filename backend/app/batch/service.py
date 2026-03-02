"""Batch operations service per ADR-060."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.search.service import index_entity as _index_entity
from app.search.service import index_model as _index_model
from app.search.service import remove_entity_index as _remove_entity_index
from app.search.service import remove_model_index as _remove_model_index

if TYPE_CHECKING:
    import aiosqlite


async def batch_delete_models(
    db: aiosqlite.Connection,
    ids: list[str],
    deleted_by: str,
) -> dict[str, object]:
    """Soft-delete multiple models."""
    succeeded = 0
    failed = 0
    errors: list[str] = []

    for model_id in ids:
        try:
            cursor = await db.execute(
                "SELECT current_version FROM models WHERE id = ? AND is_deleted = 0",
                (model_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                failed += 1
                errors.append(f"Model {model_id} not found or already deleted")
                continue

            new_version = row[0] + 1
            now = datetime.now(tz=UTC).isoformat()

            cursor = await db.execute(
                "SELECT name, description, data FROM model_versions "
                "WHERE model_id = ? AND version = ?",
                (model_id, row[0]),
            )
            ver_row = await cursor.fetchone()
            if ver_row is None:
                failed += 1
                errors.append(f"Model {model_id} version data missing")
                continue

            await db.execute(
                "UPDATE models SET current_version = ?, updated_at = ?, "
                "is_deleted = 1 WHERE id = ?",
                (new_version, now, model_id),
            )
            await db.execute(
                "INSERT INTO model_versions (model_id, version, name, description, "
                "data, change_type, created_at, created_by) "
                "VALUES (?, ?, ?, ?, ?, 'delete', ?, ?)",
                (model_id, new_version, ver_row[0], ver_row[1],
                 ver_row[2], now, deleted_by),
            )
            await _remove_model_index(db, model_id)
            succeeded += 1
        except Exception as exc:
            failed += 1
            errors.append(f"Model {model_id}: {exc}")

    await db.commit()
    return {"succeeded": succeeded, "failed": failed, "errors": errors}


async def batch_clone_models(
    db: aiosqlite.Connection,
    ids: list[str],
    cloned_by: str,
) -> dict[str, object]:
    """Clone multiple models (shallow copy)."""
    succeeded = 0
    failed = 0
    errors: list[str] = []

    for model_id in ids:
        try:
            cursor = await db.execute(
                "SELECT m.model_type, m.parent_model_id, m.set_id, "
                "mv.name, mv.description, mv.data "
                "FROM models m "
                "JOIN model_versions mv ON m.id = mv.model_id "
                "AND m.current_version = mv.version "
                "WHERE m.id = ? AND m.is_deleted = 0",
                (model_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                failed += 1
                errors.append(f"Model {model_id} not found")
                continue

            new_id = str(uuid.uuid4())
            now = datetime.now(tz=UTC).isoformat()
            clone_name = f"{row[3]} (Copy)"

            await db.execute(
                "INSERT INTO models (id, model_type, current_version, "
                "created_at, created_by, updated_at, parent_model_id, set_id) "
                "VALUES (?, ?, 1, ?, ?, ?, ?, ?)",
                (new_id, row[0], now, cloned_by, now, row[1], row[2]),
            )
            await db.execute(
                "INSERT INTO model_versions (model_id, version, name, description, "
                "data, change_type, created_at, created_by) "
                "VALUES (?, 1, ?, ?, ?, 'create', ?, ?)",
                (new_id, clone_name, row[4], row[5], now, cloned_by),
            )

            # Copy tags
            tag_cursor = await db.execute(
                "SELECT tag FROM model_tags WHERE model_id = ?",
                (model_id,),
            )
            tag_rows = await tag_cursor.fetchall()
            for tr in tag_rows:
                await db.execute(
                    "INSERT OR IGNORE INTO model_tags (model_id, tag, created_at, created_by) "
                    "VALUES (?, ?, ?, ?)",
                    (new_id, tr[0], now, cloned_by),
                )

            # Index for search
            await _index_model(
                db, model_id=new_id, name=clone_name,
                model_type=row[0], description=row[4],
            )
            succeeded += 1
        except Exception as exc:
            failed += 1
            errors.append(f"Model {model_id}: {exc}")

    await db.commit()
    return {"succeeded": succeeded, "failed": failed, "errors": errors}


async def batch_set_models(
    db: aiosqlite.Connection,
    ids: list[str],
    set_id: str,
) -> dict[str, object]:
    """Reassign multiple models to a different set."""
    succeeded = 0
    failed = 0
    errors: list[str] = []

    # Verify set exists
    cursor = await db.execute(
        "SELECT id FROM sets WHERE id = ? AND is_deleted = 0",
        (set_id,),
    )
    if await cursor.fetchone() is None:
        return {"succeeded": 0, "failed": len(ids), "errors": [f"Set {set_id} not found"]}

    for model_id in ids:
        try:
            cursor = await db.execute(
                "SELECT id FROM models WHERE id = ? AND is_deleted = 0",
                (model_id,),
            )
            if await cursor.fetchone() is None:
                failed += 1
                errors.append(f"Model {model_id} not found")
                continue

            await db.execute(
                "UPDATE models SET set_id = ? WHERE id = ?",
                (set_id, model_id),
            )
            succeeded += 1
        except Exception as exc:
            failed += 1
            errors.append(f"Model {model_id}: {exc}")

    await db.commit()
    return {"succeeded": succeeded, "failed": failed, "errors": errors}


async def batch_tags_models(
    db: aiosqlite.Connection,
    ids: list[str],
    add_tags: list[str],
    remove_tags: list[str],
    modified_by: str,
) -> dict[str, object]:
    """Add/remove tags on multiple models."""
    succeeded = 0
    failed = 0
    errors: list[str] = []
    now = datetime.now(tz=UTC).isoformat()

    for model_id in ids:
        try:
            cursor = await db.execute(
                "SELECT id FROM models WHERE id = ? AND is_deleted = 0",
                (model_id,),
            )
            if await cursor.fetchone() is None:
                failed += 1
                errors.append(f"Model {model_id} not found")
                continue

            for tag in add_tags:
                await db.execute(
                    "INSERT OR IGNORE INTO model_tags (model_id, tag, created_at, created_by) "
                    "VALUES (?, ?, ?, ?)",
                    (model_id, tag, now, modified_by),
                )

            for tag in remove_tags:
                await db.execute(
                    "DELETE FROM model_tags WHERE model_id = ? AND tag = ?",
                    (model_id, tag),
                )

            succeeded += 1
        except Exception as exc:
            failed += 1
            errors.append(f"Model {model_id}: {exc}")

    await db.commit()
    return {"succeeded": succeeded, "failed": failed, "errors": errors}


async def batch_delete_entities(
    db: aiosqlite.Connection,
    ids: list[str],
    deleted_by: str,
) -> dict[str, object]:
    """Soft-delete multiple entities."""
    succeeded = 0
    failed = 0
    errors: list[str] = []

    for entity_id in ids:
        try:
            cursor = await db.execute(
                "SELECT current_version FROM entities WHERE id = ? AND is_deleted = 0",
                (entity_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                failed += 1
                errors.append(f"Entity {entity_id} not found or already deleted")
                continue

            new_version = row[0] + 1
            now = datetime.now(tz=UTC).isoformat()

            cursor = await db.execute(
                "SELECT name, description, data FROM entity_versions "
                "WHERE entity_id = ? AND version = ?",
                (entity_id, row[0]),
            )
            ver_row = await cursor.fetchone()
            if ver_row is None:
                failed += 1
                errors.append(f"Entity {entity_id} version data missing")
                continue

            await db.execute(
                "UPDATE entities SET current_version = ?, updated_at = ?, "
                "is_deleted = 1 WHERE id = ?",
                (new_version, now, entity_id),
            )
            await db.execute(
                "INSERT INTO entity_versions (entity_id, version, name, description, "
                "data, change_type, created_at, created_by) "
                "VALUES (?, ?, ?, ?, ?, 'delete', ?, ?)",
                (entity_id, new_version, ver_row[0], ver_row[1],
                 ver_row[2], now, deleted_by),
            )
            await _remove_entity_index(db, entity_id)
            succeeded += 1
        except Exception as exc:
            failed += 1
            errors.append(f"Entity {entity_id}: {exc}")

    await db.commit()
    return {"succeeded": succeeded, "failed": failed, "errors": errors}


async def batch_clone_entities(
    db: aiosqlite.Connection,
    ids: list[str],
    cloned_by: str,
) -> dict[str, object]:
    """Clone multiple entities (shallow copy)."""
    succeeded = 0
    failed = 0
    errors: list[str] = []

    for entity_id in ids:
        try:
            cursor = await db.execute(
                "SELECT e.entity_type, e.set_id, "
                "ev.name, ev.description, ev.data "
                "FROM entities e "
                "JOIN entity_versions ev ON e.id = ev.entity_id "
                "AND e.current_version = ev.version "
                "WHERE e.id = ? AND e.is_deleted = 0",
                (entity_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                failed += 1
                errors.append(f"Entity {entity_id} not found")
                continue

            new_id = str(uuid.uuid4())
            now = datetime.now(tz=UTC).isoformat()
            clone_name = f"{row[2]} (Copy)"
            data_json = row[4] if isinstance(row[4], str) else json.dumps(row[4]) if row[4] else "{}"

            await db.execute(
                "INSERT INTO entities (id, entity_type, current_version, "
                "created_at, created_by, updated_at, set_id) "
                "VALUES (?, ?, 1, ?, ?, ?, ?)",
                (new_id, row[0], now, cloned_by, now, row[1]),
            )
            await db.execute(
                "INSERT INTO entity_versions (entity_id, version, name, description, "
                "data, change_type, created_at, created_by) "
                "VALUES (?, 1, ?, ?, ?, 'create', ?, ?)",
                (new_id, clone_name, row[3], data_json, now, cloned_by),
            )

            # Copy tags
            tag_cursor = await db.execute(
                "SELECT tag FROM entity_tags WHERE entity_id = ?",
                (entity_id,),
            )
            tag_rows = await tag_cursor.fetchall()
            for tr in tag_rows:
                await db.execute(
                    "INSERT OR IGNORE INTO entity_tags (entity_id, tag, created_at, created_by) "
                    "VALUES (?, ?, ?, ?)",
                    (new_id, tr[0], now, cloned_by),
                )

            # Index for search
            await _index_entity(
                db, entity_id=new_id, name=clone_name,
                entity_type=row[0], description=row[3],
            )
            succeeded += 1
        except Exception as exc:
            failed += 1
            errors.append(f"Entity {entity_id}: {exc}")

    await db.commit()
    return {"succeeded": succeeded, "failed": failed, "errors": errors}


async def batch_set_entities(
    db: aiosqlite.Connection,
    ids: list[str],
    set_id: str,
) -> dict[str, object]:
    """Reassign multiple entities to a different set."""
    succeeded = 0
    failed = 0
    errors: list[str] = []

    # Verify set exists
    cursor = await db.execute(
        "SELECT id FROM sets WHERE id = ? AND is_deleted = 0",
        (set_id,),
    )
    if await cursor.fetchone() is None:
        return {"succeeded": 0, "failed": len(ids), "errors": [f"Set {set_id} not found"]}

    for entity_id in ids:
        try:
            cursor = await db.execute(
                "SELECT id FROM entities WHERE id = ? AND is_deleted = 0",
                (entity_id,),
            )
            if await cursor.fetchone() is None:
                failed += 1
                errors.append(f"Entity {entity_id} not found")
                continue

            await db.execute(
                "UPDATE entities SET set_id = ? WHERE id = ?",
                (set_id, entity_id),
            )
            succeeded += 1
        except Exception as exc:
            failed += 1
            errors.append(f"Entity {entity_id}: {exc}")

    await db.commit()
    return {"succeeded": succeeded, "failed": failed, "errors": errors}


async def batch_tags_entities(
    db: aiosqlite.Connection,
    ids: list[str],
    add_tags: list[str],
    remove_tags: list[str],
    modified_by: str,
) -> dict[str, object]:
    """Add/remove tags on multiple entities."""
    succeeded = 0
    failed = 0
    errors: list[str] = []
    now = datetime.now(tz=UTC).isoformat()

    for entity_id in ids:
        try:
            cursor = await db.execute(
                "SELECT id FROM entities WHERE id = ? AND is_deleted = 0",
                (entity_id,),
            )
            if await cursor.fetchone() is None:
                failed += 1
                errors.append(f"Entity {entity_id} not found")
                continue

            for tag in add_tags:
                await db.execute(
                    "INSERT OR IGNORE INTO entity_tags (entity_id, tag, created_at, created_by) "
                    "VALUES (?, ?, ?, ?)",
                    (entity_id, tag, now, modified_by),
                )

            for tag in remove_tags:
                await db.execute(
                    "DELETE FROM entity_tags WHERE entity_id = ? AND tag = ?",
                    (entity_id, tag),
                )

            succeeded += 1
        except Exception as exc:
            failed += 1
            errors.append(f"Entity {entity_id}: {exc}")

    await db.commit()
    return {"succeeded": succeeded, "failed": failed, "errors": errors}
