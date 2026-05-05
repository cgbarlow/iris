"""Service layer for the images module (ADR-145, v5.4.0).

Provides byte-validated upload + retrieval. Validates MIME via magic
bytes (not just the Content-Type header) so a text file with a fake
`image/png` content-type is still rejected.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.adapter import DatabasePort

# 5 MB upload cap — generous enough for screenshots, tight enough that
# we don't ship multi-MB blobs through the markdown payload by accident.
MAX_IMAGE_BYTES = 5 * 1024 * 1024

ALLOWED_MIMES: frozenset[str] = frozenset(
    {"image/png", "image/jpeg", "image/gif", "image/webp"}
)


def _detect_mime_from_magic(data: bytes) -> str | None:
    """Sniff the file's magic bytes — defence in depth above Content-Type."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return "image/gif"
    if (
        len(data) >= 12
        and data[0:4] == b"RIFF"
        and data[8:12] == b"WEBP"
    ):
        return "image/webp"
    return None


def validate_image(data: bytes, declared_mime: str) -> str:
    """Validate the upload and return the resolved MIME.

    Raises ValueError on size/type violations. The caller maps to HTTP.
    """
    if len(data) == 0:
        raise ValueError("Empty image upload.")
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError(
            f"Image exceeds {MAX_IMAGE_BYTES // (1024 * 1024)} MB cap."
        )
    actual = _detect_mime_from_magic(data)
    if actual is None:
        raise ValueError("Unrecognised image format (PNG/JPEG/GIF/WebP only).")
    if actual not in ALLOWED_MIMES:
        raise ValueError(f"Image MIME {actual!r} is not allowed.")
    # If the declared type contradicts the detected one, prefer the
    # detected one — but reject obvious lies (declared png, actual gif).
    if declared_mime in ALLOWED_MIMES and declared_mime != actual:
        raise ValueError(
            f"Declared MIME {declared_mime!r} doesn't match content {actual!r}."
        )
    return actual


async def create_image(
    db: DatabasePort,
    *,
    data: bytes,
    declared_mime: str,
    uploaded_by: str | None,
) -> dict[str, object]:
    """Validate + persist an image. Returns the row metadata (no bytes)."""
    mime = validate_image(data, declared_mime)
    image_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()
    await db.execute(
        "INSERT INTO images (id, mime, bytes, size_bytes, uploaded_by, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (image_id, mime, data, len(data), uploaded_by, now),
    )
    await db.commit()
    return {
        "id": image_id,
        "mime": mime,
        "size_bytes": len(data),
        "created_at": now,
    }


async def get_image(db: DatabasePort, image_id: str) -> dict[str, object] | None:
    """Fetch an image by id. Returns None if not found."""
    cursor = await db.execute(
        "SELECT id, mime, bytes, size_bytes, created_at FROM images WHERE id = ?",
        (image_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    return {
        "id": row[0],
        "mime": row[1],
        "bytes": bytes(row[2]) if not isinstance(row[2], bytes) else row[2],
        "size_bytes": row[3],
        "created_at": row[4],
    }
