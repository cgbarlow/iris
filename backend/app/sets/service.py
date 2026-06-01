"""Set CRUD service per ADR-060."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.migrations.m012_sets import DEFAULT_SET_ID
from app.search.service import (
    index_set as _index_set,
    remove_set_index as _remove_set_index,
)

if TYPE_CHECKING:
    import aiosqlite
    from app.db.adapter import DatabasePort


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
        "collection_id": row[10] if len(row) > 10 else None,
        "collection_name": row[11] if len(row) > 11 else None,
        "system_prompt": row[12] if len(row) > 12 else None,
        "mcp_system_context": row[13] if len(row) > 13 else None,
        # ADR-202: NULL fallback for pre-migration rows (shouldn't
        # happen because the column has a DEFAULT, but belt-and-braces).
        "hierarchy_sort": (row[14] if len(row) > 14 and row[14] else "manual"),
        # ADR-204: same belt-and-braces for the new tab-default columns.
        "package_tab_default": (
            row[15] if len(row) > 15 and row[15] else "relationships"
        ),
        "view_tab_default": (
            row[16] if len(row) > 16 and row[16] else "canvas"
        ),
        # ADR-208 (v6.16.0): sibling to the v6.14.0 columns above.
        "element_tab_default": (
            row[17] if len(row) > 17 and row[17] else "relationships"
        ),
    }


async def _grouped_counts(db: DatabasePort, sql: str) -> dict[object, int]:
    """Run a ``SELECT key, COUNT(*) ... GROUP BY key`` and return ``{key: count}``.

    Used by :func:`list_sets` (ADR-236) to fetch per-set counts in a single
    query instead of one COUNT(*) per set. Positional row access (§15).
    """
    cursor = await db.execute(sql)
    return {row[0]: row[1] for row in await cursor.fetchall()}


_SET_COLUMNS = (
    "s.id, s.name, s.description, s.created_at, s.created_by, "
    "s.updated_at, s.is_deleted, s.thumbnail_source, s.thumbnail_diagram_id, "
    # ADR-209 (v6.17.4): has_thumbnail_image is true when EITHER the
    # legacy thumbnail_image BLOB column has bytes OR there's at least
    # one entity_images attachment. The thumbnail GET endpoint resolves
    # in the right priority (model → image → attachment).
    "(s.thumbnail_image IS NOT NULL "
    " OR EXISTS (SELECT 1 FROM entity_images ei "
    "            WHERE ei.entity_type = 'set' AND ei.entity_id = s.id)), "
    "s.collection_id, col.name, s.system_prompt, "
    "s.mcp_system_context, s.hierarchy_sort, s.package_tab_default, "
    "s.view_tab_default, s.element_tab_default"
)


async def create_set(
    db: DatabasePort,
    *,
    name: str,
    description: str | None,
    created_by: str,
    collection_id: str | None = None,
) -> dict[str, object]:
    """Create a new set."""
    set_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()

    await db.execute(
        "INSERT INTO sets (id, name, description, created_at, created_by, updated_at, collection_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (set_id, name, description, now, created_by, now, collection_id),
    )
    await db.commit()

    await _index_set(db, set_id=set_id, name=name, description=description)

    return {
        "id": set_id,
        "name": name,
        "description": description,
        "created_at": now,
        "created_by": created_by,
        "updated_at": now,
        "is_deleted": False,
        "collection_id": collection_id,
        "collection_name": None,
        "diagram_count": 0,
        "element_count": 0,
        "package_count": 0,
        "package_count_root": 0,
        "thumbnail_source": None,
        "thumbnail_diagram_id": None,
        "has_thumbnail_image": False,
        "system_prompt": None,
        "mcp_system_context": None,
        "hierarchy_sort": "manual",  # ADR-202 default for new sets
        "package_tab_default": "relationships",  # ADR-204 defaults
        "view_tab_default": "canvas",
        "element_tab_default": "relationships",  # ADR-208 default
    }


async def get_set(
    db: DatabasePort,
    set_id: str,
) -> dict[str, object] | None:
    """Get a set by ID with diagram/element counts."""
    cursor = await db.execute(
        f"SELECT {_SET_COLUMNS} "  # noqa: S608
        "FROM sets s LEFT JOIN collections col ON s.collection_id = col.id "
        "WHERE s.id = ? AND s.is_deleted = 0",
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

    # Count packages in this set (ADR-158, v5.13.0): give MCP clients
    # an upfront signal that pagination matters when calling list_packages
    # on big sets, and a quick hint of structural breadth.
    pc = await db.execute(
        "SELECT COUNT(*) FROM packages WHERE set_id = ? AND is_deleted = 0",
        (set_id,),
    )
    result["package_count"] = (await pc.fetchone())[0]

    pcr = await db.execute(
        "SELECT COUNT(*) FROM packages "
        "WHERE set_id = ? AND is_deleted = 0 AND parent_package_id IS NULL",
        (set_id,),
    )
    result["package_count_root"] = (await pcr.fetchone())[0]

    return result


async def list_sets(
    db: DatabasePort,
    *,
    collection_id: str | None = None,
) -> list[dict[str, object]]:
    """List all sets with diagram/element counts, optionally filtered by collection."""
    if collection_id is not None:
        cursor = await db.execute(
            f"SELECT {_SET_COLUMNS} "  # noqa: S608
            "FROM sets s LEFT JOIN collections col ON s.collection_id = col.id "
            "WHERE s.is_deleted = 0 AND s.collection_id = ? ORDER BY s.name",
            (collection_id,),
        )
    else:
        cursor = await db.execute(
            f"SELECT {_SET_COLUMNS} "  # noqa: S608
            "FROM sets s LEFT JOIN collections col ON s.collection_id = col.id "
            "WHERE s.is_deleted = 0 ORDER BY s.name",
        )
    rows = await cursor.fetchall()

    # ADR-236: compute per-set counts with grouped aggregates (one query each)
    # instead of four COUNT(*) queries per set. The old per-set loop was O(4N)
    # round-trips — pathologically slow on Supabase, where each await is a
    # network hop. One global GROUP BY per metric, mapped by set_id, is correct
    # for both the filtered and unfiltered branches.
    diagram_counts = await _grouped_counts(
        db, "SELECT set_id, COUNT(*) FROM diagrams WHERE is_deleted = 0 GROUP BY set_id"
    )
    element_counts = await _grouped_counts(
        db, "SELECT set_id, COUNT(*) FROM elements WHERE is_deleted = 0 GROUP BY set_id"
    )
    # Package counts (ADR-158, v5.13.0)
    package_counts = await _grouped_counts(
        db, "SELECT set_id, COUNT(*) FROM packages WHERE is_deleted = 0 GROUP BY set_id"
    )
    package_root_counts = await _grouped_counts(
        db,
        "SELECT set_id, COUNT(*) FROM packages "
        "WHERE is_deleted = 0 AND parent_package_id IS NULL GROUP BY set_id",
    )

    items = []
    for row in rows:
        item = _row_to_dict(row, has_thumbnail_image=bool(row[9]))
        set_id = row[0]

        item["diagram_count"] = diagram_counts.get(set_id, 0)
        item["element_count"] = element_counts.get(set_id, 0)
        item["package_count"] = package_counts.get(set_id, 0)
        item["package_count_root"] = package_root_counts.get(set_id, 0)

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


async def update_set(
    db: DatabasePort,
    set_id: str,
    *,
    name: str,
    description: str | None,
    thumbnail_source: str | None = None,
    thumbnail_diagram_id: str | None = None,
    collection_id: str | None = None,
    system_prompt: str | None = None,
    mcp_system_context: str | None = None,
    hierarchy_sort: str | None = None,
    package_tab_default: str | None = None,
    view_tab_default: str | None = None,
    element_tab_default: str | None = None,
) -> dict[str, object] | None:
    """Update a set's metadata.

    ADR-202 adds ``hierarchy_sort``; ADR-204 adds ``package_tab_default``
    and ``view_tab_default``; ADR-208 adds ``element_tab_default``. All
    are tri-stateish: None means "leave alone". The Pydantic Literals on
    SetUpdate constrain the value space upstream so we accept whatever
    the caller gave us.

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
            "thumbnail_source = ?, thumbnail_diagram_id = ?, thumbnail_image = NULL, "
            "collection_id = ?, system_prompt = ?, mcp_system_context = ? "
            "WHERE id = ?",
            (name, description, now, thumbnail_source, thumbnail_diagram_id,
             collection_id, system_prompt, mcp_system_context, set_id),
        )
    else:
        await db.execute(
            "UPDATE sets SET name = ?, description = ?, updated_at = ?, "
            "thumbnail_source = ?, thumbnail_diagram_id = ?, "
            "collection_id = ?, system_prompt = ?, mcp_system_context = ? "
            "WHERE id = ?",
            (name, description, now, thumbnail_source, thumbnail_diagram_id,
             collection_id, system_prompt, mcp_system_context, set_id),
        )

    # ADR-202: hierarchy_sort updated separately so the main UPDATE
    # stays unchanged for callers that don't touch it.
    if hierarchy_sort is not None:
        await db.execute(
            "UPDATE sets SET hierarchy_sort = ?, updated_at = ? WHERE id = ?",
            (hierarchy_sort, now, set_id),
        )

    # ADR-204: same per-field separate UPDATE pattern for tab defaults.
    if package_tab_default is not None:
        await db.execute(
            "UPDATE sets SET package_tab_default = ?, updated_at = ? WHERE id = ?",
            (package_tab_default, now, set_id),
        )
    if view_tab_default is not None:
        await db.execute(
            "UPDATE sets SET view_tab_default = ?, updated_at = ? WHERE id = ?",
            (view_tab_default, now, set_id),
        )
    # ADR-208 (v6.16.0): sibling per-field update.
    if element_tab_default is not None:
        await db.execute(
            "UPDATE sets SET element_tab_default = ?, updated_at = ? WHERE id = ?",
            (element_tab_default, now, set_id),
        )

    await db.commit()

    await _index_set(db, set_id=set_id, name=name, description=description)

    return await get_set(db, set_id)


async def soft_delete_set(
    db: DatabasePort,
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

    await _remove_set_index(db, set_id)

    return None


async def force_delete_set(
    db: DatabasePort,
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
    db: DatabasePort,
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
    db: DatabasePort,
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

    # ADR-209 (v6.17.4): if no thumbnail is configured, fall back to the
    # first attachment from entity_images. Lets the new attach-an-image
    # UI on the set details page double as the gallery tile thumbnail.
    cursor = await db.execute(
        "SELECT i.bytes FROM entity_images ei "
        "JOIN images i ON ei.image_id = i.id "
        "WHERE ei.entity_type = 'set' AND ei.entity_id = ? "
        "ORDER BY ei.display_order, ei.created_at LIMIT 1",
        (set_id,),
    )
    arow = await cursor.fetchone()
    if arow is not None and arow[0]:
        raw = arow[0]
        return bytes(raw) if not isinstance(raw, bytes) else raw

    return None


async def get_set_tags(
    db: DatabasePort,
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
