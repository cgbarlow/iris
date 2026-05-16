"""Service layer for the artefacts module (ADR-179, v6.2.0).

Stores rendered markdown / docx / pdf artefacts produced by the
renderer endpoints. Sibling to the images store — this one accepts
documents (text/markdown, docx, pdf) and uses its own mime allowlist
and per-row cap.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.adapter import DatabasePort


# 25 MB per-artefact cap — generous enough for full DoView books in
# docx/pdf form, tight enough that a runaway render can't flood the DB.
MAX_ARTEFACT_BYTES = 25 * 1024 * 1024

ALLOWED_ARTEFACT_MIMES: frozenset[str] = frozenset(
    {
        "text/markdown",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/pdf",
    },
)


def _validate_bytes(data: bytes, mime: str) -> None:
    """Raise ValueError if data fails size / mime checks.

    Magic-byte sniffing is mime-specific and lighter than the image
    store's because text/markdown has no magic. We do byte-header
    checks for pdf and docx (zip signature) since they're easy.
    """
    if not data:
        raise ValueError("Empty artefact upload.")
    if len(data) > MAX_ARTEFACT_BYTES:
        raise ValueError(
            f"Artefact exceeds {MAX_ARTEFACT_BYTES // (1024 * 1024)} MB cap.",
        )
    if mime not in ALLOWED_ARTEFACT_MIMES:
        raise ValueError(
            f"Artefact MIME {mime!r} not allowed. Allowed: "
            f"{sorted(ALLOWED_ARTEFACT_MIMES)}.",
        )

    if mime == "application/pdf" and not data.startswith(b"%PDF"):
        raise ValueError(
            "PDF artefact missing %PDF header — renderer produced invalid output.",
        )
    if mime == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ) and not data.startswith(b"PK\x03\x04"):
        # docx is a ZIP archive; sniff the local-file-header magic.
        raise ValueError(
            "DOCX artefact missing ZIP signature — renderer produced invalid output.",
        )


async def create_artefact(
    db: DatabasePort,
    *,
    data: bytes,
    mime: str,
    filename: str,
    source_kind: str,
    source_ref: str | None = None,
    created_by: str | None = None,
) -> dict[str, object]:
    """Validate + persist an artefact. Returns the row metadata."""
    _validate_bytes(data, mime)
    artefact_id = str(uuid.uuid4())
    now = datetime.now(tz=UTC).isoformat()
    await db.execute(
        "INSERT INTO artefacts (id, filename, mime, bytes, size_bytes, "
        "source_kind, source_ref, created_by, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (artefact_id, filename, mime, data, len(data),
         source_kind, source_ref, created_by, now),
    )
    await db.commit()
    return {
        "id": artefact_id,
        "filename": filename,
        "mime_type": mime,
        "size_bytes": len(data),
        "source_kind": source_kind,
        "source_ref": source_ref,
        "created_at": now,
    }


async def get_artefact(
    db: DatabasePort, artefact_id: str,
) -> dict[str, object] | None:
    """Fetch an artefact by id. Returns None if not found."""
    cursor = await db.execute(
        "SELECT id, filename, mime, bytes, size_bytes, source_kind, "
        "source_ref, created_at FROM artefacts WHERE id = ?",
        (artefact_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    return {
        "id": row[0],
        "filename": row[1],
        "mime": row[2],
        "bytes": bytes(row[3]) if not isinstance(row[3], bytes) else row[3],
        "size_bytes": row[4],
        "source_kind": row[5],
        "source_ref": row[6],
        "created_at": row[7],
    }
