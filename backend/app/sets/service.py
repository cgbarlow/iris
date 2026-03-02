"""Set CRUD service per ADR-060."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.migrations.m012_sets import DEFAULT_SET_ID

if TYPE_CHECKING:
    import aiosqlite


def _row_to_dict(row: tuple, *, has_thumbnail_image: bool = False) -> dict[str, object]:
    """Convert a sets row to a dict (without counts)."""
    return {
        "id": row[0],
        "name": row[1],
        "description": row[2],
        "created_at": row[3],
        "created_by": row[4],
        "updated_at": row[5],
        "is_deleted": bool(row[6]),
        "thumbnail_source": row[7],
        "thumbnail_model_id": row[8],
        "has_thumbnail_image": has_thumbnail_image,
    }


_SET_COLUMNS = (
    "s.id, s.name, s.description, s.created_at, s.created_by, "
    "s.updated_at, s.is_deleted, s.thumbnail_source, s.thumbnail_model_id, "
    "s.thumbnail_image IS NOT NULL"
)


async def create_set(
    db: aiosqlite.Connection,
    *,
    name: str,
    description: str | None,
    created_by: str,
) -> dict[str, object]:
    """Create a new set."""
    set_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()

    await db.execute(
        "INSERT INTO sets (id, name, description, created_at, created_by, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (set_id, name, description, now, created_by, now),
    )
    await db.commit()

    return {
        "id": set_id,
        "name": name,
        "description": description,
        "created_at": now,
        "created_by": created_by,
        "updated_at": now,
        "is_deleted": False,
        "model_count": 0,
        "entity_count": 0,
        "thumbnail_source": None,
        "thumbnail_model_id": None,
        "has_thumbnail_image": False,
    }


async def get_set(
    db: aiosqlite.Connection,
    set_id: str,
) -> dict[str, object] | None:
    """Get a set by ID with model/entity counts."""
    cursor = await db.execute(
        f"SELECT {_SET_COLUMNS} "  # noqa: S608
        "FROM sets s WHERE s.id = ? AND s.is_deleted = 0",
        (set_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None

    result = _row_to_dict(row, has_thumbnail_image=bool(row[9]))

    # Count models in this set
    mc = await db.execute(
        "SELECT COUNT(*) FROM models WHERE set_id = ? AND is_deleted = 0",
        (set_id,),
    )
    result["model_count"] = (await mc.fetchone())[0]

    # Count entities in this set
    ec = await db.execute(
        "SELECT COUNT(*) FROM entities WHERE set_id = ? AND is_deleted = 0",
        (set_id,),
    )
    result["entity_count"] = (await ec.fetchone())[0]

    return result


async def list_sets(
    db: aiosqlite.Connection,
) -> list[dict[str, object]]:
    """List all sets with model/entity counts."""
    cursor = await db.execute(
        f"SELECT {_SET_COLUMNS} "  # noqa: S608
        "FROM sets s WHERE s.is_deleted = 0 ORDER BY s.name",
    )
    rows = await cursor.fetchall()

    items = []
    for row in rows:
        item = _row_to_dict(row, has_thumbnail_image=bool(row[9]))
        set_id = row[0]

        mc = await db.execute(
            "SELECT COUNT(*) FROM models WHERE set_id = ? AND is_deleted = 0",
            (set_id,),
        )
        item["model_count"] = (await mc.fetchone())[0]

        ec = await db.execute(
            "SELECT COUNT(*) FROM entities WHERE set_id = ? AND is_deleted = 0",
            (set_id,),
        )
        item["entity_count"] = (await ec.fetchone())[0]

        items.append(item)

    return items


async def update_set(
    db: aiosqlite.Connection,
    set_id: str,
    *,
    name: str,
    description: str | None,
    thumbnail_source: str | None = None,
    thumbnail_model_id: str | None = None,
) -> dict[str, object] | None:
    """Update a set's name, description, and thumbnail settings.

    Returns None if not found.
    """
    cursor = await db.execute(
        "SELECT id FROM sets WHERE id = ? AND is_deleted = 0",
        (set_id,),
    )
    if await cursor.fetchone() is None:
        return None

    # Validate thumbnail_model_id belongs to this set when source is 'model'
    if thumbnail_source == "model" and thumbnail_model_id:
        mc = await db.execute(
            "SELECT id FROM models WHERE id = ? AND set_id = ? AND is_deleted = 0",
            (thumbnail_model_id, set_id),
        )
        if await mc.fetchone() is None:
            msg = "Thumbnail model does not belong to this set"
            raise ValueError(msg)

    now = datetime.now(tz=UTC).isoformat()

    # Clear thumbnail_image when switching away from 'image' source
    if thumbnail_source != "image":
        await db.execute(
            "UPDATE sets SET name = ?, description = ?, updated_at = ?, "
            "thumbnail_source = ?, thumbnail_model_id = ?, thumbnail_image = NULL "
            "WHERE id = ?",
            (name, description, now, thumbnail_source, thumbnail_model_id, set_id),
        )
    else:
        await db.execute(
            "UPDATE sets SET name = ?, description = ?, updated_at = ?, "
            "thumbnail_source = ?, thumbnail_model_id = ? "
            "WHERE id = ?",
            (name, description, now, thumbnail_source, thumbnail_model_id, set_id),
        )
    await db.commit()

    return await get_set(db, set_id)


async def soft_delete_set(
    db: aiosqlite.Connection,
    set_id: str,
) -> dict[str, object] | None:
    """Soft-delete a set. Returns error info or None on success.

    Returns {"error": "default"} if trying to delete Default set.
    Returns {"error": "non_empty"} if set has models or entities.
    Returns {"error": "not_found"} if set doesn't exist.
    Returns None on successful deletion.
    """
    if set_id == DEFAULT_SET_ID:
        return {"error": "default"}

    cursor = await db.execute(
        "SELECT id FROM sets WHERE id = ? AND is_deleted = 0",
        (set_id,),
    )
    if await cursor.fetchone() is None:
        return {"error": "not_found"}

    # Check if non-empty
    mc = await db.execute(
        "SELECT COUNT(*) FROM models WHERE set_id = ? AND is_deleted = 0",
        (set_id,),
    )
    model_count = (await mc.fetchone())[0]

    ec = await db.execute(
        "SELECT COUNT(*) FROM entities WHERE set_id = ? AND is_deleted = 0",
        (set_id,),
    )
    entity_count = (await ec.fetchone())[0]

    if model_count > 0 or entity_count > 0:
        return {"error": "non_empty"}

    now = datetime.now(tz=UTC).isoformat()
    await db.execute(
        "UPDATE sets SET is_deleted = 1, updated_at = ? WHERE id = ?",
        (now, set_id),
    )
    await db.commit()
    return None


async def force_delete_set(
    db: aiosqlite.Connection,
    set_id: str,
    deleted_by: str,
) -> dict[str, int] | dict[str, str]:
    """Force-delete a set and all its contents.

    Returns {"error": ...} on failure, or {"models_deleted": N, "entities_deleted": N} on success.
    """
    if set_id == DEFAULT_SET_ID:
        return {"error": "default"}

    cursor = await db.execute(
        "SELECT id FROM sets WHERE id = ? AND is_deleted = 0",
        (set_id,),
    )
    if await cursor.fetchone() is None:
        return {"error": "not_found"}

    now = datetime.now(tz=UTC).isoformat()

    # Count and soft-delete entities in this set
    ec = await db.execute(
        "SELECT COUNT(*) FROM entities WHERE set_id = ? AND is_deleted = 0",
        (set_id,),
    )
    entities_deleted = (await ec.fetchone())[0]
    await db.execute(
        "UPDATE entities SET is_deleted = 1, updated_at = ? WHERE set_id = ? AND is_deleted = 0",
        (now, set_id),
    )

    # Soft-delete relationships where source or target is in this set
    await db.execute(
        "UPDATE relationships SET is_deleted = 1, updated_at = ? "
        "WHERE is_deleted = 0 AND ("
        "  source_entity_id IN (SELECT id FROM entities WHERE set_id = ?) OR "
        "  target_entity_id IN (SELECT id FROM entities WHERE set_id = ?)"
        ")",
        (now, set_id, set_id),
    )

    # Remove search indexes for deleted entities
    await db.execute(
        "DELETE FROM entities_fts WHERE entity_id IN "
        "(SELECT id FROM entities WHERE set_id = ? AND is_deleted = 1)",
        (set_id,),
    )

    # Count and soft-delete models in this set
    mc = await db.execute(
        "SELECT COUNT(*) FROM models WHERE set_id = ? AND is_deleted = 0",
        (set_id,),
    )
    models_deleted = (await mc.fetchone())[0]
    await db.execute(
        "UPDATE models SET is_deleted = 1, updated_at = ? WHERE set_id = ? AND is_deleted = 0",
        (now, set_id),
    )

    # Remove search indexes for deleted models
    await db.execute(
        "DELETE FROM models_fts WHERE model_id IN "
        "(SELECT id FROM models WHERE set_id = ? AND is_deleted = 1)",
        (set_id,),
    )

    # Soft-delete the set itself
    await db.execute(
        "UPDATE sets SET is_deleted = 1, updated_at = ? WHERE id = ?",
        (now, set_id),
    )
    await db.commit()

    return {"models_deleted": models_deleted, "entities_deleted": entities_deleted}


async def store_set_thumbnail_image(
    db: aiosqlite.Connection,
    set_id: str,
    image_bytes: bytes,
) -> dict[str, object] | None:
    """Store a user-uploaded thumbnail image for a set.

    Returns updated set dict, or None if set not found.
    """
    cursor = await db.execute(
        "SELECT id FROM sets WHERE id = ? AND is_deleted = 0",
        (set_id,),
    )
    if await cursor.fetchone() is None:
        return None

    now = datetime.now(tz=UTC).isoformat()
    await db.execute(
        "UPDATE sets SET thumbnail_source = 'image', thumbnail_model_id = NULL, "
        "thumbnail_image = ?, updated_at = ? WHERE id = ?",
        (image_bytes, now, set_id),
    )
    await db.commit()

    return await get_set(db, set_id)


async def get_set_thumbnail(
    db: aiosqlite.Connection,
    set_id: str,
    *,
    theme: str = "dark",
) -> bytes | None:
    """Get the thumbnail bytes for a set.

    If source is 'model', respects the gallery_thumbnail_mode admin setting:
      - 'svg': generates SVG on the fly from model data
      - 'png': returns stored PNG from model_thumbnails
    If source is 'image', return the stored BLOB.
    Otherwise return None.
    """
    cursor = await db.execute(
        "SELECT thumbnail_source, thumbnail_model_id, thumbnail_image "
        "FROM sets WHERE id = ? AND is_deleted = 0",
        (set_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None

    source, model_id, image_blob = row

    if source == "model" and model_id:
        # Check admin thumbnail mode setting
        from app.settings.service import get_setting

        mode_setting = await get_setting(db, "gallery_thumbnail_mode")
        thumbnail_mode = mode_setting["value"] if mode_setting else "svg"

        if thumbnail_mode == "svg":
            # Generate SVG on the fly from model data
            from app.models_crud.thumbnail import generate_svg_from_model_data

            mc = await db.execute(
                "SELECT mv.data, m.model_type FROM model_versions mv "
                "JOIN models m ON m.id = mv.model_id "
                "WHERE mv.model_id = ? ORDER BY mv.version DESC LIMIT 1",
                (model_id,),
            )
            mrow = await mc.fetchone()
            if mrow is None:
                return None
            import json

            data = json.loads(mrow[0]) if isinstance(mrow[0], str) else mrow[0]
            svg_str = generate_svg_from_model_data(data, mrow[1], theme=theme)
            return svg_str.encode("utf-8")

        # PNG mode: fetch from model_thumbnails for the requested theme
        tc = await db.execute(
            "SELECT thumbnail FROM model_thumbnails WHERE model_id = ? AND theme = ?",
            (model_id, theme),
        )
        trow = await tc.fetchone()
        if trow is None and theme != "dark":
            tc = await db.execute(
                "SELECT thumbnail FROM model_thumbnails WHERE model_id = ? AND theme = 'dark'",
                (model_id,),
            )
            trow = await tc.fetchone()
        return trow[0] if trow else None

    if source == "image" and image_blob:
        return image_blob

    return None


async def get_set_tags(
    db: aiosqlite.Connection,
    set_id: str,
) -> list[str]:
    """Get all unique tags within a set (from both models and entities)."""
    cursor = await db.execute(
        "SELECT DISTINCT tag FROM ("
        "  SELECT mt.tag FROM model_tags mt"
        "  JOIN models m ON mt.model_id = m.id"
        "  WHERE m.set_id = ? AND m.is_deleted = 0"
        "  UNION"
        "  SELECT et.tag FROM entity_tags et"
        "  JOIN entities e ON et.entity_id = e.id"
        "  WHERE e.set_id = ? AND e.is_deleted = 0"
        ") ORDER BY tag",
        (set_id, set_id),
    )
    rows = await cursor.fetchall()
    return [row[0] for row in rows]
