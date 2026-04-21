"""Collection CRUD service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.search.service import (
    index_collection as _index_collection,
    remove_collection_index as _remove_collection_index,
)

if TYPE_CHECKING:
    from app.db.adapter import DatabasePort


def _row_to_dict(row: tuple, *, has_thumbnail_image: bool = False) -> dict[str, object]:
    """Convert a collections row to a dict (without counts)."""
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


_COLLECTION_COLUMNS = (
    "c.id, c.name, c.description, c.created_at, c.created_by, "
    "c.updated_at, c.is_deleted, c.thumbnail_source, c.thumbnail_diagram_id, "
    "c.thumbnail_image IS NOT NULL"
)


async def create_collection(
    db: DatabasePort,
    *,
    name: str,
    description: str | None,
    created_by: str,
) -> dict[str, object]:
    """Create a new collection."""
    collection_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()

    await db.execute(
        "INSERT INTO collections (id, name, description, created_at, created_by, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (collection_id, name, description, now, created_by, now),
    )
    await db.commit()

    await _index_collection(
        db, collection_id=collection_id, name=name, description=description,
    )

    return {
        "id": collection_id,
        "name": name,
        "description": description,
        "created_at": now,
        "created_by": created_by,
        "updated_at": now,
        "is_deleted": False,
        "set_count": 0,
        "diagram_count": 0,
        "element_count": 0,
        "thumbnail_source": None,
        "thumbnail_diagram_id": None,
        "has_thumbnail_image": False,
    }


async def get_collection(
    db: DatabasePort,
    collection_id: str,
) -> dict[str, object] | None:
    """Get a collection by ID with set/diagram/element counts."""
    cursor = await db.execute(
        f"SELECT {_COLLECTION_COLUMNS} "  # noqa: S608
        "FROM collections c WHERE c.id = ? AND c.is_deleted = 0",
        (collection_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None

    result = _row_to_dict(row, has_thumbnail_image=bool(row[9]))

    # Count sets in this collection
    sc = await db.execute(
        "SELECT COUNT(*) FROM sets WHERE collection_id = ? AND is_deleted = 0",
        (collection_id,),
    )
    result["set_count"] = (await sc.fetchone())[0]

    # Count diagrams across sets in this collection
    dc = await db.execute(
        "SELECT COUNT(*) FROM diagrams d JOIN sets s ON d.set_id = s.id "
        "WHERE s.collection_id = ? AND d.is_deleted = 0 AND s.is_deleted = 0",
        (collection_id,),
    )
    result["diagram_count"] = (await dc.fetchone())[0]

    # Count elements across sets in this collection
    ec = await db.execute(
        "SELECT COUNT(*) FROM elements e JOIN sets s ON e.set_id = s.id "
        "WHERE s.collection_id = ? AND e.is_deleted = 0 AND s.is_deleted = 0",
        (collection_id,),
    )
    result["element_count"] = (await ec.fetchone())[0]

    return result


async def list_collections(
    db: DatabasePort,
) -> list[dict[str, object]]:
    """List all collections with set/diagram/element counts."""
    cursor = await db.execute(
        f"SELECT {_COLLECTION_COLUMNS} "  # noqa: S608
        "FROM collections c WHERE c.is_deleted = 0 ORDER BY c.name",
    )
    rows = await cursor.fetchall()

    items = []
    for row in rows:
        item = _row_to_dict(row, has_thumbnail_image=bool(row[9]))
        collection_id = row[0]

        sc = await db.execute(
            "SELECT COUNT(*) FROM sets WHERE collection_id = ? AND is_deleted = 0",
            (collection_id,),
        )
        item["set_count"] = (await sc.fetchone())[0]

        dc = await db.execute(
            "SELECT COUNT(*) FROM diagrams d JOIN sets s ON d.set_id = s.id "
            "WHERE s.collection_id = ? AND d.is_deleted = 0 AND s.is_deleted = 0",
            (collection_id,),
        )
        item["diagram_count"] = (await dc.fetchone())[0]

        ec = await db.execute(
            "SELECT COUNT(*) FROM elements e JOIN sets s ON e.set_id = s.id "
            "WHERE s.collection_id = ? AND e.is_deleted = 0 AND s.is_deleted = 0",
            (collection_id,),
        )
        item["element_count"] = (await ec.fetchone())[0]

        # Include thumbnail diagram data for client-side rendering (DRY)
        thumb_id = row[8]  # thumbnail_diagram_id
        if row[7] in ("model", "diagram") and thumb_id:
            tc = await db.execute(
                "SELECT dv.data, d.diagram_type "
                "FROM diagram_versions dv "
                "JOIN diagrams d ON d.id = dv.diagram_id "
                "WHERE dv.diagram_id = ? ORDER BY dv.version DESC LIMIT 1",
                (thumb_id,),
            )
            trow = await tc.fetchone()
            if trow:
                import json

                item["thumbnail_diagram_data"] = (
                    json.loads(trow[0]) if isinstance(trow[0], str) else trow[0]
                )
                item["thumbnail_diagram_type"] = trow[1]

        items.append(item)

    return items


async def update_collection(
    db: DatabasePort,
    collection_id: str,
    *,
    name: str,
    description: str | None,
    thumbnail_source: str | None = None,
    thumbnail_diagram_id: str | None = None,
) -> dict[str, object] | None:
    """Update a collection's name, description, and thumbnail settings.

    Returns None if not found.
    """
    cursor = await db.execute(
        "SELECT id FROM collections WHERE id = ? AND is_deleted = 0",
        (collection_id,),
    )
    if await cursor.fetchone() is None:
        return None

    # Validate thumbnail_diagram_id belongs to a set in this collection
    if thumbnail_source in ("model", "diagram") and thumbnail_diagram_id:
        mc = await db.execute(
            "SELECT d.id FROM diagrams d JOIN sets s ON d.set_id = s.id "
            "WHERE d.id = ? AND s.collection_id = ? AND d.is_deleted = 0 AND s.is_deleted = 0",
            (thumbnail_diagram_id, collection_id),
        )
        if await mc.fetchone() is None:
            msg = "Thumbnail diagram does not belong to a set in this collection"
            raise ValueError(msg)

    now = datetime.now(tz=UTC).isoformat()

    # Clear thumbnail_image when switching away from 'image' source
    if thumbnail_source != "image":
        await db.execute(
            "UPDATE collections SET name = ?, description = ?, updated_at = ?, "
            "thumbnail_source = ?, thumbnail_diagram_id = ?, thumbnail_image = NULL "
            "WHERE id = ?",
            (name, description, now, thumbnail_source, thumbnail_diagram_id, collection_id),
        )
    else:
        await db.execute(
            "UPDATE collections SET name = ?, description = ?, updated_at = ?, "
            "thumbnail_source = ?, thumbnail_diagram_id = ? "
            "WHERE id = ?",
            (name, description, now, thumbnail_source, thumbnail_diagram_id, collection_id),
        )
    await db.commit()

    await _index_collection(
        db, collection_id=collection_id, name=name, description=description,
    )

    return await get_collection(db, collection_id)


async def soft_delete_collection(
    db: DatabasePort,
    collection_id: str,
) -> dict[str, object] | None:
    """Soft-delete a collection. Unlinks all sets from this collection.

    Returns {"error": "not_found"} if collection doesn't exist.
    Returns None on successful deletion.
    """
    cursor = await db.execute(
        "SELECT id FROM collections WHERE id = ? AND is_deleted = 0",
        (collection_id,),
    )
    if await cursor.fetchone() is None:
        return {"error": "not_found"}

    now = datetime.now(tz=UTC).isoformat()

    # Unlink sets from this collection
    await db.execute(
        "UPDATE sets SET collection_id = NULL WHERE collection_id = ?",
        (collection_id,),
    )

    # Soft-delete the collection
    await db.execute(
        "UPDATE collections SET is_deleted = 1, updated_at = ? WHERE id = ?",
        (now, collection_id),
    )
    await db.commit()

    await _remove_collection_index(db, collection_id)

    return None


async def store_collection_thumbnail_image(
    db: DatabasePort,
    collection_id: str,
    image_bytes: bytes,
) -> dict[str, object] | None:
    """Store a user-uploaded thumbnail image for a collection.

    Returns updated collection dict, or None if collection not found.
    """
    cursor = await db.execute(
        "SELECT id FROM collections WHERE id = ? AND is_deleted = 0",
        (collection_id,),
    )
    if await cursor.fetchone() is None:
        return None

    now = datetime.now(tz=UTC).isoformat()
    await db.execute(
        "UPDATE collections SET thumbnail_source = 'image', thumbnail_diagram_id = NULL, "
        "thumbnail_image = ?, updated_at = ? WHERE id = ?",
        (image_bytes, now, collection_id),
    )
    await db.commit()

    return await get_collection(db, collection_id)


async def get_collection_thumbnail(
    db: DatabasePort,
    collection_id: str,
    *,
    theme: str = "dark",
) -> bytes | None:
    """Get the thumbnail bytes for a collection.

    If source is 'model', respects the gallery_thumbnail_mode admin setting:
      - 'svg': generates SVG on the fly from diagram data
      - 'png': returns stored PNG from diagram_thumbnails
    If source is 'image', return the stored BLOB.
    Otherwise return None.
    """
    cursor = await db.execute(
        "SELECT thumbnail_source, thumbnail_diagram_id, thumbnail_image "
        "FROM collections WHERE id = ? AND is_deleted = 0",
        (collection_id,),
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
