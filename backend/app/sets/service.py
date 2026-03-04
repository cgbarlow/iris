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
        "thumbnail_diagram_id": row[8],
        "has_thumbnail_image": has_thumbnail_image,
    }


_SET_COLUMNS = (
    "s.id, s.name, s.description, s.created_at, s.created_by, "
    "s.updated_at, s.is_deleted, s.thumbnail_source, s.thumbnail_diagram_id, "
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
        "diagram_count": 0,
        "element_count": 0,
        "thumbnail_source": None,
        "thumbnail_diagram_id": None,
        "has_thumbnail_image": False,
    }


async def get_set(
    db: aiosqlite.Connection,
    set_id: str,
) -> dict[str, object] | None:
    """Get a set by ID with diagram/element counts."""
    cursor = await db.execute(
        f"SELECT {_SET_COLUMNS} "  # noqa: S608
        "FROM sets s WHERE s.id = ? AND s.is_deleted = 0",
        (set_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None

    result = _row_to_dict(row, has_thumbnail_image=bool(row[9]))

    # Count diagrams in this set
    mc = await db.execute(
        "SELECT COUNT(*) FROM diagrams WHERE set_id = ? AND is_deleted = 0",
        (set_id,),
    )
    result["diagram_count"] = (await mc.fetchone())[0]

    # Count elements in this set
    ec = await db.execute(
        "SELECT COUNT(*) FROM elements WHERE set_id = ? AND is_deleted = 0",
        (set_id,),
    )
    result["element_count"] = (await ec.fetchone())[0]

    return result


async def list_sets(
    db: aiosqlite.Connection,
) -> list[dict[str, object]]:
    """List all sets with diagram/element counts."""
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
            "SELECT COUNT(*) FROM diagrams WHERE set_id = ? AND is_deleted = 0",
            (set_id,),
        )
        item["diagram_count"] = (await mc.fetchone())[0]

        ec = await db.execute(
            "SELECT COUNT(*) FROM elements WHERE set_id = ? AND is_deleted = 0",
            (set_id,),
        )
        item["element_count"] = (await ec.fetchone())[0]

        items.append(item)

    return items


async def update_set(
    db: aiosqlite.Connection,
    set_id: str,
    *,
    name: str,
    description: str | None,
    thumbnail_source: str | None = None,
    thumbnail_diagram_id: str | None = None,
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

    # Validate thumbnail_diagram_id belongs to this set when source is 'diagram'
    if thumbnail_source in ("model", "diagram") and thumbnail_diagram_id:
        mc = await db.execute(
            "SELECT id FROM diagrams WHERE id = ? AND set_id = ? AND is_deleted = 0",
            (thumbnail_diagram_id, set_id),
        )
        if await mc.fetchone() is None:
            msg = "Thumbnail diagram does not belong to this set"
            raise ValueError(msg)

    now = datetime.now(tz=UTC).isoformat()

    # Clear thumbnail_image when switching away from 'image' source
    if thumbnail_source != "image":
        await db.execute(
            "UPDATE sets SET name = ?, description = ?, updated_at = ?, "
            "thumbnail_source = ?, thumbnail_diagram_id = ?, thumbnail_image = NULL "
            "WHERE id = ?",
            (name, description, now, thumbnail_source, thumbnail_diagram_id, set_id),
        )
    else:
        await db.execute(
            "UPDATE sets SET name = ?, description = ?, updated_at = ?, "
            "thumbnail_source = ?, thumbnail_diagram_id = ? "
            "WHERE id = ?",
            (name, description, now, thumbnail_source, thumbnail_diagram_id, set_id),
        )
    await db.commit()

    return await get_set(db, set_id)


async def soft_delete_set(
    db: aiosqlite.Connection,
    set_id: str,
) -> dict[str, object] | None:
    """Soft-delete a set. Returns error info or None on success.

    Returns {"error": "default"} if trying to delete Default set.
    Returns {"error": "non_empty"} if set has diagrams or elements.
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
        "SELECT COUNT(*) FROM diagrams WHERE set_id = ? AND is_deleted = 0",
        (set_id,),
    )
    diagram_count = (await mc.fetchone())[0]

    ec = await db.execute(
        "SELECT COUNT(*) FROM elements WHERE set_id = ? AND is_deleted = 0",
        (set_id,),
    )
    element_count = (await ec.fetchone())[0]

    if diagram_count > 0 or element_count > 0:
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

    Returns {"error": ...} on failure, or {"diagrams_deleted": N, "elements_deleted": N} on success.
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

    # Count and soft-delete packages in this set
    pc = await db.execute(
        "SELECT COUNT(*) FROM packages WHERE set_id = ? AND is_deleted = 0",
        (set_id,),
    )
    packages_deleted = (await pc.fetchone())[0]
    await db.execute(
        "UPDATE packages SET is_deleted = 1, updated_at = ? WHERE set_id = ? AND is_deleted = 0",
        (now, set_id),
    )

    # Delete package_relationships for packages in this set
    await db.execute(
        "DELETE FROM package_relationships "
        "WHERE source_package_id IN (SELECT id FROM packages WHERE set_id = ?) "
        "OR target_package_id IN (SELECT id FROM packages WHERE set_id = ?)",
        (set_id, set_id),
    )

    # Count and soft-delete elements in this set
    ec = await db.execute(
        "SELECT COUNT(*) FROM elements WHERE set_id = ? AND is_deleted = 0",
        (set_id,),
    )
    elements_deleted = (await ec.fetchone())[0]
    await db.execute(
        "UPDATE elements SET is_deleted = 1, updated_at = ? WHERE set_id = ? AND is_deleted = 0",
        (now, set_id),
    )

    # Soft-delete relationships where source or target is in this set
    await db.execute(
        "UPDATE relationships SET is_deleted = 1, updated_at = ? "
        "WHERE is_deleted = 0 AND ("
        "  source_element_id IN (SELECT id FROM elements WHERE set_id = ?) OR "
        "  target_element_id IN (SELECT id FROM elements WHERE set_id = ?)"
        ")",
        (now, set_id, set_id),
    )

    # Remove search indexes for deleted elements
    await db.execute(
        "DELETE FROM elements_fts WHERE element_id IN "
        "(SELECT id FROM elements WHERE set_id = ? AND is_deleted = 1)",
        (set_id,),
    )

    # Count and soft-delete diagrams in this set
    mc = await db.execute(
        "SELECT COUNT(*) FROM diagrams WHERE set_id = ? AND is_deleted = 0",
        (set_id,),
    )
    diagrams_deleted = (await mc.fetchone())[0]
    await db.execute(
        "UPDATE diagrams SET is_deleted = 1, updated_at = ? WHERE set_id = ? AND is_deleted = 0",
        (now, set_id),
    )

    # Remove search indexes for deleted diagrams
    await db.execute(
        "DELETE FROM diagrams_fts WHERE diagram_id IN "
        "(SELECT id FROM diagrams WHERE set_id = ? AND is_deleted = 1)",
        (set_id,),
    )

    # Soft-delete the set itself
    await db.execute(
        "UPDATE sets SET is_deleted = 1, updated_at = ? WHERE id = ?",
        (now, set_id),
    )
    await db.commit()

    return {
        "packages_deleted": packages_deleted,
        "diagrams_deleted": diagrams_deleted,
        "elements_deleted": elements_deleted,
    }


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
        "UPDATE sets SET thumbnail_source = 'image', thumbnail_diagram_id = NULL, "
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
      - 'svg': generates SVG on the fly from diagram data
      - 'png': returns stored PNG from diagram_thumbnails
    If source is 'image', return the stored BLOB.
    Otherwise return None.
    """
    cursor = await db.execute(
        "SELECT thumbnail_source, thumbnail_diagram_id, thumbnail_image "
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
            # Generate SVG on the fly from diagram data
            from app.diagrams.thumbnail import generate_svg_from_diagram_data

            mc = await db.execute(
                "SELECT dv.data, d.diagram_type FROM diagram_versions dv "
                "JOIN diagrams d ON d.id = dv.diagram_id "
                "WHERE dv.diagram_id = ? ORDER BY dv.version DESC LIMIT 1",
                (model_id,),
            )
            mrow = await mc.fetchone()
            if mrow is None:
                return None
            import json

            data = json.loads(mrow[0]) if isinstance(mrow[0], str) else mrow[0]
            svg_str = generate_svg_from_diagram_data(data, mrow[1], theme=theme)
            return svg_str.encode("utf-8")

        # PNG mode: fetch from diagram_thumbnails for the requested theme
        tc = await db.execute(
            "SELECT thumbnail FROM diagram_thumbnails WHERE diagram_id = ? AND theme = ?",
            (model_id, theme),
        )
        trow = await tc.fetchone()
        if trow is None and theme != "dark":
            tc = await db.execute(
                "SELECT thumbnail FROM diagram_thumbnails WHERE diagram_id = ? AND theme = 'dark'",
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
    """Get all unique tags within a set (from both diagrams and elements)."""
    cursor = await db.execute(
        "SELECT DISTINCT tag FROM ("
        "  SELECT dt.tag FROM diagram_tags dt"
        "  JOIN diagrams d ON dt.diagram_id = d.id"
        "  WHERE d.set_id = ? AND d.is_deleted = 0"
        "  UNION"
        "  SELECT et.tag FROM element_tags et"
        "  JOIN elements e ON et.element_id = e.id"
        "  WHERE e.set_id = ? AND e.is_deleted = 0"
        ") ORDER BY tag",
        (set_id, set_id),
    )
    rows = await cursor.fetchall()
    return [row[0] for row in rows]
