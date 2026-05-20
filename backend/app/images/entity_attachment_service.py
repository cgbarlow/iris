"""Entity image attachment service (ADR-209, v6.17.0).

Junction-table layer between `entity_images` and the various entity
tables (collections / sets / packages / diagrams / elements). Reuses
the existing `images` table for byte storage.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from app.db.adapter import DatabasePort

EntityType = Literal["collection", "set", "package", "diagram", "element"]
ALLOWED_ENTITY_TYPES: frozenset[EntityType] = frozenset(
    ("collection", "set", "package", "diagram", "element"),
)


class EntityNotFoundError(Exception):
    """The entity_type/entity_id pair doesn't resolve."""


class ImageNotFoundError(Exception):
    """The image_id doesn't resolve."""


class AttachmentNotFoundError(Exception):
    """The attachment row doesn't exist."""


async def _entity_exists(
    db: DatabasePort, entity_type: EntityType, entity_id: str,
) -> bool:
    """Verify (entity_type, entity_id) resolves to a live row.

    Different tables use different soft-delete columns; collections
    don't have `is_deleted` at all, so we check existence only there.
    """
    if entity_type == "collection":
        cursor = await db.execute(
            "SELECT 1 FROM collections WHERE id = ?", (entity_id,),
        )
    elif entity_type == "set":
        cursor = await db.execute(
            "SELECT 1 FROM sets WHERE id = ? AND is_deleted = 0",
            (entity_id,),
        )
    elif entity_type == "package":
        cursor = await db.execute(
            "SELECT 1 FROM packages WHERE id = ? AND is_deleted = 0",
            (entity_id,),
        )
    elif entity_type == "diagram":
        cursor = await db.execute(
            "SELECT 1 FROM diagrams WHERE id = ? AND is_deleted = 0",
            (entity_id,),
        )
    else:  # element
        cursor = await db.execute(
            "SELECT 1 FROM elements WHERE id = ? AND is_deleted = 0",
            (entity_id,),
        )
    return (await cursor.fetchone()) is not None


async def _image_exists(db: DatabasePort, image_id: str) -> bool:
    cursor = await db.execute(
        "SELECT 1 FROM images WHERE id = ?", (image_id,),
    )
    return (await cursor.fetchone()) is not None


async def attach_image(
    db: DatabasePort,
    *,
    entity_type: EntityType,
    entity_id: str,
    image_id: str,
    created_by: str,
) -> dict[str, object]:
    """Attach an existing image to an entity. Idempotent — re-attaching
    the same image returns the existing row (UNIQUE constraint).

    Raises:
        EntityNotFoundError: entity_type/entity_id doesn't resolve.
        ImageNotFoundError:  image_id doesn't resolve.
    """
    if not await _entity_exists(db, entity_type, entity_id):
        raise EntityNotFoundError(f"{entity_type} {entity_id} not found")
    if not await _image_exists(db, image_id):
        raise ImageNotFoundError(f"Image {image_id} not found")

    # If already attached, return the existing row.
    cursor = await db.execute(
        "SELECT id FROM entity_images "
        "WHERE entity_type = ? AND entity_id = ? AND image_id = ?",
        (entity_type, entity_id, image_id),
    )
    existing = await cursor.fetchone()
    if existing is not None:
        rows = await list_entity_images(db, entity_type=entity_type, entity_id=entity_id)
        for row in rows:
            if row["id"] == existing[0]:
                return row

    attachment_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()
    # display_order = max + 1 (push to the end of the gallery)
    cursor = await db.execute(
        "SELECT COALESCE(MAX(display_order), -1) + 1 FROM entity_images "
        "WHERE entity_type = ? AND entity_id = ?",
        (entity_type, entity_id),
    )
    next_order = (await cursor.fetchone())[0]
    await db.execute(
        "INSERT INTO entity_images "
        "(id, entity_type, entity_id, image_id, display_order, created_at, created_by) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (attachment_id, entity_type, entity_id, image_id, next_order, now, created_by),
    )
    await db.commit()
    rows = await list_entity_images(db, entity_type=entity_type, entity_id=entity_id)
    for row in rows:
        if row["id"] == attachment_id:
            return row
    # Shouldn't happen — return a synthetic row as a last resort.
    return {
        "id": attachment_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "image_id": image_id,
        "display_order": next_order,
        "created_at": now,
        "created_by": created_by,
    }


async def detach_image(
    db: DatabasePort,
    *,
    entity_type: EntityType,
    entity_id: str,
    attachment_id: str,
) -> None:
    """Detach an image from an entity. Does NOT delete the underlying
    `images` row — other entities may still reference it.

    Raises:
        AttachmentNotFoundError: the (entity_type, entity_id, attachment_id)
            triple doesn't match a row.
    """
    cursor = await db.execute(
        "SELECT id FROM entity_images "
        "WHERE id = ? AND entity_type = ? AND entity_id = ?",
        (attachment_id, entity_type, entity_id),
    )
    if (await cursor.fetchone()) is None:
        raise AttachmentNotFoundError(
            f"Attachment {attachment_id} not found on {entity_type} {entity_id}",
        )
    await db.execute(
        "DELETE FROM entity_images WHERE id = ?", (attachment_id,),
    )
    await db.commit()


async def list_entity_images(
    db: DatabasePort,
    *,
    entity_type: EntityType,
    entity_id: str,
) -> list[dict[str, object]]:
    """List image attachments for an entity, joined with image metadata."""
    cursor = await db.execute(
        "SELECT ei.id, ei.entity_type, ei.entity_id, ei.image_id, "
        "       ei.display_order, ei.created_at, ei.created_by, "
        "       i.mime, i.size_bytes "
        "FROM entity_images ei "
        "JOIN images i ON ei.image_id = i.id "
        "WHERE ei.entity_type = ? AND ei.entity_id = ? "
        "ORDER BY ei.display_order, ei.created_at",
        (entity_type, entity_id),
    )
    rows = await cursor.fetchall()
    return [
        {
            "id": r[0],
            "entity_type": r[1],
            "entity_id": r[2],
            "image_id": r[3],
            "display_order": r[4],
            "created_at": r[5],
            "created_by": r[6],
            "image_mime": r[7],
            "image_size_bytes": r[8],
        }
        for r in rows
    ]
