"""Batch operations service per ADR-060."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.search.service import index_element as _index_element
from app.search.service import index_diagram as _index_diagram
from app.search.service import remove_element_index as _remove_element_index
from app.search.service import remove_diagram_index as _remove_diagram_index

if TYPE_CHECKING:
    import aiosqlite
    from app.db.adapter import DatabasePort


async def batch_delete_diagrams(
    db: DatabasePort,
    ids: list[str],
    deleted_by: str,
) -> dict[str, object]:
    """Soft-delete multiple diagrams."""
    succeeded = 0
    failed = 0
    errors: list[str] = []

    for diagram_id in ids:
        try:
            cursor = await db.execute(
                "SELECT current_version FROM diagrams WHERE id = ? AND is_deleted = 0",
                (diagram_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                failed += 1
                errors.append(f"Diagram {diagram_id} not found or already deleted")
                continue

            new_version = row[0] + 1
            now = datetime.now(tz=UTC).isoformat()

            cursor = await db.execute(
                "SELECT name, description, data FROM diagram_versions "
                "WHERE diagram_id = ? AND version = ?",
                (diagram_id, row[0]),
            )
            ver_row = await cursor.fetchone()
            if ver_row is None:
                failed += 1
                errors.append(f"Diagram {diagram_id} version data missing")
                continue

            await db.execute(
                "UPDATE diagrams SET current_version = ?, updated_at = ?, "
                "is_deleted = 1 WHERE id = ?",
                (new_version, now, diagram_id),
            )
            await db.execute(
                "INSERT INTO diagram_versions (diagram_id, version, name, description, "
                "data, change_type, created_at, created_by) "
                "VALUES (?, ?, ?, ?, ?, 'delete', ?, ?)",
                (diagram_id, new_version, ver_row[0], ver_row[1],
                 ver_row[2], now, deleted_by),
            )
            await _remove_diagram_index(db, diagram_id)
            succeeded += 1
        except Exception as exc:
            failed += 1
            errors.append(f"Diagram {diagram_id}: {exc}")

    await db.commit()
    return {"succeeded": succeeded, "failed": failed, "errors": errors}


async def batch_clone_diagrams(
    db: DatabasePort,
    ids: list[str],
    cloned_by: str,
) -> dict[str, object]:
    """Clone multiple diagrams (shallow copy)."""
    succeeded = 0
    failed = 0
    errors: list[str] = []

    for diagram_id in ids:
        try:
            cursor = await db.execute(
                "SELECT m.diagram_type, m.parent_package_id, m.set_id, "
                "mv.name, mv.description, mv.data "
                "FROM diagrams m "
                "JOIN diagram_versions mv ON m.id = mv.diagram_id "
                "AND m.current_version = mv.version "
                "WHERE m.id = ? AND m.is_deleted = 0",
                (diagram_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                failed += 1
                errors.append(f"Diagram {diagram_id} not found")
                continue

            new_id = str(uuid.uuid4())
            now = datetime.now(tz=UTC).isoformat()
            clone_name = f"{row[3]} (Copy)"

            await db.execute(
                "INSERT INTO diagrams (id, diagram_type, current_version, "
                "created_at, created_by, updated_at, parent_package_id, set_id) "
                "VALUES (?, ?, 1, ?, ?, ?, ?, ?)",
                (new_id, row[0], now, cloned_by, now, row[1], row[2]),
            )
            await db.execute(
                "INSERT INTO diagram_versions (diagram_id, version, name, description, "
                "data, change_type, created_at, created_by) "
                "VALUES (?, 1, ?, ?, ?, 'create', ?, ?)",
                (new_id, clone_name, row[4], row[5], now, cloned_by),
            )

            # Copy tags
            tag_cursor = await db.execute(
                "SELECT tag FROM diagram_tags WHERE diagram_id = ?",
                (diagram_id,),
            )
            tag_rows = await tag_cursor.fetchall()
            for tr in tag_rows:
                await db.execute(
                    "INSERT OR IGNORE INTO diagram_tags (diagram_id, tag, created_at, created_by) "
                    "VALUES (?, ?, ?, ?)",
                    (new_id, tr[0], now, cloned_by),
                )

            # Index for search
            await _index_diagram(
                db, diagram_id=new_id, name=clone_name,
                diagram_type=row[0], description=row[4],
            )
            succeeded += 1
        except Exception as exc:
            failed += 1
            errors.append(f"Diagram {diagram_id}: {exc}")

    await db.commit()
    return {"succeeded": succeeded, "failed": failed, "errors": errors}


async def batch_set_diagrams(
    db: DatabasePort,
    ids: list[str],
    set_id: str,
) -> dict[str, object]:
    """Reassign multiple diagrams to a different set."""
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

    for diagram_id in ids:
        try:
            cursor = await db.execute(
                "SELECT id FROM diagrams WHERE id = ? AND is_deleted = 0",
                (diagram_id,),
            )
            if await cursor.fetchone() is None:
                failed += 1
                errors.append(f"Diagram {diagram_id} not found")
                continue

            await db.execute(
                "UPDATE diagrams SET set_id = ? WHERE id = ?",
                (set_id, diagram_id),
            )
            succeeded += 1
        except Exception as exc:
            failed += 1
            errors.append(f"Diagram {diagram_id}: {exc}")

    await db.commit()
    return {"succeeded": succeeded, "failed": failed, "errors": errors}


async def batch_tags_diagrams(
    db: DatabasePort,
    ids: list[str],
    add_tags: list[str],
    remove_tags: list[str],
    modified_by: str,
) -> dict[str, object]:
    """Add/remove tags on multiple diagrams."""
    succeeded = 0
    failed = 0
    errors: list[str] = []
    now = datetime.now(tz=UTC).isoformat()

    for diagram_id in ids:
        try:
            cursor = await db.execute(
                "SELECT id FROM diagrams WHERE id = ? AND is_deleted = 0",
                (diagram_id,),
            )
            if await cursor.fetchone() is None:
                failed += 1
                errors.append(f"Diagram {diagram_id} not found")
                continue

            for tag in add_tags:
                await db.execute(
                    "INSERT OR IGNORE INTO diagram_tags (diagram_id, tag, created_at, created_by) "
                    "VALUES (?, ?, ?, ?)",
                    (diagram_id, tag, now, modified_by),
                )

            for tag in remove_tags:
                await db.execute(
                    "DELETE FROM diagram_tags WHERE diagram_id = ? AND tag = ?",
                    (diagram_id, tag),
                )

            succeeded += 1
        except Exception as exc:
            failed += 1
            errors.append(f"Diagram {diagram_id}: {exc}")

    await db.commit()
    return {"succeeded": succeeded, "failed": failed, "errors": errors}


async def batch_delete_elements(
    db: DatabasePort,
    ids: list[str],
    deleted_by: str,
) -> dict[str, object]:
    """Soft-delete multiple elements."""
    succeeded = 0
    failed = 0
    errors: list[str] = []

    for element_id in ids:
        try:
            cursor = await db.execute(
                "SELECT current_version FROM elements WHERE id = ? AND is_deleted = 0",
                (element_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                failed += 1
                errors.append(f"Element {element_id} not found or already deleted")
                continue

            new_version = row[0] + 1
            now = datetime.now(tz=UTC).isoformat()

            cursor = await db.execute(
                "SELECT name, description, data FROM element_versions "
                "WHERE element_id = ? AND version = ?",
                (element_id, row[0]),
            )
            ver_row = await cursor.fetchone()
            if ver_row is None:
                failed += 1
                errors.append(f"Element {element_id} version data missing")
                continue

            await db.execute(
                "UPDATE elements SET current_version = ?, updated_at = ?, "
                "is_deleted = 1 WHERE id = ?",
                (new_version, now, element_id),
            )
            await db.execute(
                "INSERT INTO element_versions (element_id, version, name, description, "
                "data, change_type, created_at, created_by) "
                "VALUES (?, ?, ?, ?, ?, 'delete', ?, ?)",
                (element_id, new_version, ver_row[0], ver_row[1],
                 ver_row[2], now, deleted_by),
            )
            await _remove_element_index(db, element_id)
            succeeded += 1
        except Exception as exc:
            failed += 1
            errors.append(f"Element {element_id}: {exc}")

    await db.commit()
    return {"succeeded": succeeded, "failed": failed, "errors": errors}


async def batch_create_elements(
    db: DatabasePort,
    elements: list[dict[str, Any]],
    created_by: str,
) -> dict[str, Any]:
    """Bulk create elements with per-item failure isolation (ADR-200, #173)."""
    from app.elements.models import _UNSET
    from app.elements.service import create_element, ElementPackageInvariantError

    succeeded = 0
    failed = 0
    errors: list[str] = []
    created_ids: list[str] = []

    for idx, item in enumerate(elements):
        try:
            element_type = item.get("element_type") or ""
            name = item.get("name") or ""
            if not element_type:
                raise ValueError("element_type is required")
            if not name:
                raise ValueError("name is required")
            result = await create_element(
                db,
                element_type=element_type,
                name=name,
                description=item.get("description"),
                data=item.get("data") or {},
                created_by=created_by,
                set_id=item.get("set_id"),
                package_id=item.get("package_id"),
                metadata=item.get("metadata"),
                notation=item.get("notation") or "simple",
            )
            created_ids.append(str(result["id"]))
            succeeded += 1
        except ElementPackageInvariantError as exc:
            failed += 1
            errors.append(f"Element at index {idx}: {exc}")
        except Exception as exc:
            failed += 1
            errors.append(f"Element at index {idx}: {exc}")

    return {
        "succeeded": succeeded, "failed": failed,
        "errors": errors, "ids": created_ids,
    }


async def batch_update_elements(
    db: DatabasePort,
    updates: list[dict[str, Any]],
    updated_by: str,
) -> dict[str, Any]:
    """Bulk update elements (ADR-200, #173).

    Each item carries its own ``expected_version``; version conflicts
    surface as per-item failures (not a whole-batch 409).
    """
    from app.elements.models import _UNSET
    from app.elements.service import update_element, ElementPackageInvariantError

    succeeded = 0
    failed = 0
    errors: list[str] = []
    updated_ids: list[str] = []

    for idx, item in enumerate(updates):
        try:
            element_id = item.get("element_id")
            expected_version = item.get("expected_version")
            if not element_id:
                raise ValueError("element_id is required")
            if expected_version is None:
                raise ValueError("expected_version is required")

            update_kwargs: dict[str, Any] = {
                "name": item["name"],
                "description": item.get("description"),
                "data": item.get("data") or {},
                "change_summary": item.get("change_summary"),
                "updated_by": updated_by,
                "expected_version": int(expected_version),
                "metadata": item.get("metadata"),
            }
            # Tri-state package_id: only forward when the client
            # explicitly included the key (which exclude_unset captures).
            if "package_id" in item and item["package_id"] is not _UNSET:
                update_kwargs["package_id"] = item["package_id"]

            result = await update_element(db, element_id, **update_kwargs)
            if result is None:
                raise ValueError(
                    f"Version conflict (expected {expected_version})",
                )
            updated_ids.append(str(element_id))
            succeeded += 1
        except ElementPackageInvariantError as exc:
            failed += 1
            errors.append(f"Update at index {idx}: {exc}")
        except Exception as exc:
            failed += 1
            errors.append(f"Update at index {idx}: {exc}")

    return {
        "succeeded": succeeded, "failed": failed,
        "errors": errors, "ids": updated_ids,
    }


async def batch_clone_elements(
    db: DatabasePort,
    ids: list[str],
    cloned_by: str,
) -> dict[str, object]:
    """Clone multiple elements (shallow copy)."""
    succeeded = 0
    failed = 0
    errors: list[str] = []

    for element_id in ids:
        try:
            cursor = await db.execute(
                "SELECT e.element_type, e.set_id, "
                "ev.name, ev.description, ev.data "
                "FROM elements e "
                "JOIN element_versions ev ON e.id = ev.element_id "
                "AND e.current_version = ev.version "
                "WHERE e.id = ? AND e.is_deleted = 0",
                (element_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                failed += 1
                errors.append(f"Element {element_id} not found")
                continue

            new_id = str(uuid.uuid4())
            now = datetime.now(tz=UTC).isoformat()
            clone_name = f"{row[2]} (Copy)"
            data_json = row[4] if isinstance(row[4], str) else json.dumps(row[4]) if row[4] else "{}"

            await db.execute(
                "INSERT INTO elements (id, element_type, current_version, "
                "created_at, created_by, updated_at, set_id) "
                "VALUES (?, ?, 1, ?, ?, ?, ?)",
                (new_id, row[0], now, cloned_by, now, row[1]),
            )
            await db.execute(
                "INSERT INTO element_versions (element_id, version, name, description, "
                "data, change_type, created_at, created_by) "
                "VALUES (?, 1, ?, ?, ?, 'create', ?, ?)",
                (new_id, clone_name, row[3], data_json, now, cloned_by),
            )

            # Copy tags
            tag_cursor = await db.execute(
                "SELECT tag FROM element_tags WHERE element_id = ?",
                (element_id,),
            )
            tag_rows = await tag_cursor.fetchall()
            for tr in tag_rows:
                await db.execute(
                    "INSERT OR IGNORE INTO element_tags (element_id, tag, created_at, created_by) "
                    "VALUES (?, ?, ?, ?)",
                    (new_id, tr[0], now, cloned_by),
                )

            # Index for search
            await _index_element(
                db, element_id=new_id, name=clone_name,
                element_type=row[0], description=row[3],
            )
            succeeded += 1
        except Exception as exc:
            failed += 1
            errors.append(f"Element {element_id}: {exc}")

    await db.commit()
    return {"succeeded": succeeded, "failed": failed, "errors": errors}


async def batch_set_elements(
    db: DatabasePort,
    ids: list[str],
    set_id: str,
) -> dict[str, object]:
    """Reassign multiple elements to a different set."""
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

    for element_id in ids:
        try:
            cursor = await db.execute(
                "SELECT id FROM elements WHERE id = ? AND is_deleted = 0",
                (element_id,),
            )
            if await cursor.fetchone() is None:
                failed += 1
                errors.append(f"Element {element_id} not found")
                continue

            await db.execute(
                "UPDATE elements SET set_id = ? WHERE id = ?",
                (set_id, element_id),
            )
            succeeded += 1
        except Exception as exc:
            failed += 1
            errors.append(f"Element {element_id}: {exc}")

    await db.commit()
    return {"succeeded": succeeded, "failed": failed, "errors": errors}


async def batch_tags_elements(
    db: DatabasePort,
    ids: list[str],
    add_tags: list[str],
    remove_tags: list[str],
    modified_by: str,
) -> dict[str, object]:
    """Add/remove tags on multiple elements."""
    succeeded = 0
    failed = 0
    errors: list[str] = []
    now = datetime.now(tz=UTC).isoformat()

    for element_id in ids:
        try:
            cursor = await db.execute(
                "SELECT id FROM elements WHERE id = ? AND is_deleted = 0",
                (element_id,),
            )
            if await cursor.fetchone() is None:
                failed += 1
                errors.append(f"Element {element_id} not found")
                continue

            for tag in add_tags:
                await db.execute(
                    "INSERT OR IGNORE INTO element_tags (element_id, tag, created_at, created_by) "
                    "VALUES (?, ?, ?, ?)",
                    (element_id, tag, now, modified_by),
                )

            for tag in remove_tags:
                await db.execute(
                    "DELETE FROM element_tags WHERE element_id = ? AND tag = ?",
                    (element_id, tag),
                )

            succeeded += 1
        except Exception as exc:
            failed += 1
            errors.append(f"Element {element_id}: {exc}")

    await db.commit()
    return {"succeeded": succeeded, "failed": failed, "errors": errors}
