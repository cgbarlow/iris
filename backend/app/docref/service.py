"""Service layer for DocRef legislation extension (ADR-112).

Index scraping, CSV import, chunk storage, and context building.
"""

from __future__ import annotations

import csv
import io
import logging
import re
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from app.db.adapter import DatabasePort

log = logging.getLogger("app.docref")

DOCREF_BASE_URL = "https://legislation.docref.nz/"
_CHARS_PER_TOKEN = 4


def _row_to_dict(row: tuple[object, ...]) -> dict[str, object]:
    """Map a docref_documents row to a dict."""
    return {
        "id": row[0],
        "slug": row[1],
        "title": row[2],
        "latest_version": row[3],
        "source_url": row[4],
        "csv_url": row[5],
        "chunk_count": row[6],
        "status": row[7],
        "error_message": row[8],
        "imported_at": row[9],
        "imported_by": row[10],
        "created_at": row[11],
        "updated_at": row[12],
    }


_SELECT = (
    "SELECT id, slug, title, latest_version, source_url, csv_url, "
    "chunk_count, status, error_message, imported_at, imported_by, "
    "created_at, updated_at FROM docref_documents"
)


def _slug_to_title(slug: str) -> str:
    """Convert URL slug to human-readable title. e.g. 'social-security-act-2018' -> 'Social Security Act 2018'."""
    return " ".join(word.capitalize() if not word.isdigit() else word for word in slug.split("-"))


def _parse_index_html(html: str) -> list[dict[str, str]]:
    """Parse the DocRef index page HTML to extract document slugs, titles, and versions.

    The index page has a table with rows like:
      <td><a href="/social-security-act-2018/2025-07-01/en/">Social Security Act 2018</a> ...
      <td>2025-07-01</td>
    We extract slug, title, and version from the href and link text.
    """
    documents: list[dict[str, str]] = []

    # Actual hrefs include the version: href="/slug/YYYY-MM-DD/en/"
    link_pattern = re.compile(
        r'href="/([a-z0-9-]+)/(\d{4}-\d{2}-\d{2})/en/"[^>]*>([^<]+)</a>',
        re.IGNORECASE,
    )

    # Split HTML into table rows for context
    rows = re.split(r'<tr[^>]*>', html)
    for row_html in rows:
        links = link_pattern.findall(row_html)
        if not links:
            continue
        slug, version, title_text = links[0]
        # Skip non-legislation links
        if slug in ("about", "api", "docs", "search", "login", "register"):
            continue
        title = title_text.strip()
        if not title:
            title = _slug_to_title(slug)

        documents.append({
            "slug": slug,
            "title": title,
            "latest_version": version,
        })

    return documents


async def refresh_document_index(
    db: DatabasePort,
    *,
    base_url: str = DOCREF_BASE_URL,
) -> dict[str, int]:
    """Fetch the DocRef index page and upsert document metadata.

    Returns counts: documents_found, new_documents, updated_documents.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(base_url)
        resp.raise_for_status()

    documents = _parse_index_html(resp.text)
    now = datetime.now(tz=UTC).isoformat()

    new_count = 0
    updated_count = 0

    for doc in documents:
        slug = doc["slug"]
        title = doc["title"]
        version = doc["latest_version"]
        source_url = f"{base_url.rstrip('/')}/{slug}/{version}/en/"
        csv_url = f"{base_url.rstrip('/')}/{slug}/{version}/en/{slug}-{version}-en-chunked.csv"

        # Check if document exists
        cursor = await db.execute(
            "SELECT id, latest_version FROM docref_documents WHERE slug = ?",
            (slug,),
        )
        existing = await cursor.fetchone()

        if existing is None:
            # New document
            doc_id = str(uuid.uuid4())
            await db.execute(
                "INSERT INTO docref_documents "
                "(id, slug, title, latest_version, source_url, csv_url, "
                "chunk_count, status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, 0, 'available', ?, ?)",
                (doc_id, slug, title, version, source_url, csv_url, now, now),
            )
            new_count += 1
        else:
            existing_id, existing_version = existing
            if existing_version != version:
                # Version changed -- update metadata, reset import status
                await db.execute(
                    "UPDATE docref_documents SET title = ?, latest_version = ?, "
                    "source_url = ?, csv_url = ?, status = 'available', "
                    "chunk_count = 0, error_message = NULL, "
                    "imported_at = NULL, imported_by = NULL, updated_at = ? "
                    "WHERE id = ?",
                    (title, version, source_url, csv_url, now, existing_id),
                )
                # Delete old chunks
                await db.execute(
                    "DELETE FROM docref_chunks WHERE document_id = ?",
                    (existing_id,),
                )
                updated_count += 1
            else:
                # Same version -- just update timestamp
                await db.execute(
                    "UPDATE docref_documents SET updated_at = ? WHERE id = ?",
                    (now, existing_id),
                )

    await db.commit()

    return {
        "documents_found": len(documents),
        "new_documents": new_count,
        "updated_documents": updated_count,
    }


async def list_documents(db: DatabasePort) -> list[dict[str, object]]:
    """List all DocRef documents ordered by title."""
    cursor = await db.execute(f"{_SELECT} ORDER BY title ASC")
    rows = await cursor.fetchall()
    return [_row_to_dict(r) for r in rows]


async def get_document(
    db: DatabasePort, document_id: str
) -> dict[str, object] | None:
    """Get a single DocRef document by ID."""
    cursor = await db.execute(
        f"{_SELECT} WHERE id = ?", (document_id,)
    )
    row = await cursor.fetchone()
    return _row_to_dict(row) if row else None


async def import_document(
    db: DatabasePort,
    document_id: str,
    imported_by: str,
) -> dict[str, object]:
    """Download and import a document's chunked CSV.

    Sets status to 'importing', downloads CSV, parses and inserts chunks,
    then sets status to 'imported'. On error, sets status to 'error'.
    """
    now = datetime.now(tz=UTC).isoformat()

    # Fetch document
    doc = await get_document(db, document_id)
    if doc is None:
        msg = f"Document {document_id} not found"
        raise ValueError(msg)

    csv_url = str(doc["csv_url"])

    # Set status to importing
    await db.execute(
        "UPDATE docref_documents SET status = 'importing', "
        "error_message = NULL, updated_at = ? WHERE id = ?",
        (now, document_id),
    )
    await db.commit()

    try:
        # Download CSV
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(csv_url)
            resp.raise_for_status()

        # Delete any existing chunks
        await db.execute(
            "DELETE FROM docref_chunks WHERE document_id = ?",
            (document_id,),
        )

        # Parse CSV
        reader = csv.reader(io.StringIO(resp.text))
        header = next(reader, None)
        if header is None:
            msg = "Empty CSV file"
            raise ValueError(msg)

        chunk_count = 0
        for sort_order, row in enumerate(reader):
            if len(row) < 3:  # noqa: PLR2004
                continue
            chunk_id_val, url_val, content_val = row[0], row[1], row[2]
            if not content_val.strip():
                continue
            await db.execute(
                "INSERT INTO docref_chunks "
                "(id, document_id, chunk_id, url, content, sort_order) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), document_id, chunk_id_val, url_val, content_val, sort_order),
            )
            chunk_count += 1

        # Update document status
        now = datetime.now(tz=UTC).isoformat()
        await db.execute(
            "UPDATE docref_documents SET status = 'imported', "
            "chunk_count = ?, imported_at = ?, imported_by = ?, "
            "error_message = NULL, updated_at = ? WHERE id = ?",
            (chunk_count, now, imported_by, now, document_id),
        )
        await db.commit()

        return {
            "document_id": document_id,
            "status": "imported",
            "chunk_count": chunk_count,
        }

    except Exception as exc:
        now = datetime.now(tz=UTC).isoformat()
        await db.execute(
            "UPDATE docref_documents SET status = 'error', "
            "error_message = ?, updated_at = ? WHERE id = ?",
            (str(exc)[:500], now, document_id),
        )
        await db.commit()
        raise


async def delete_document_chunks(
    db: DatabasePort, document_id: str
) -> bool:
    """Remove imported chunks and reset document status to 'available'."""
    doc = await get_document(db, document_id)
    if doc is None:
        return False

    await db.execute(
        "DELETE FROM docref_chunks WHERE document_id = ?",
        (document_id,),
    )
    now = datetime.now(tz=UTC).isoformat()
    await db.execute(
        "UPDATE docref_documents SET status = 'available', "
        "chunk_count = 0, imported_at = NULL, imported_by = NULL, "
        "error_message = NULL, updated_at = ? WHERE id = ?",
        (now, document_id),
    )
    await db.commit()
    return True


def _truncate_to_budget(text: str, max_chars: int) -> str:
    """Truncate text to fit within character budget."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars - 3] + "..."


async def build_docref_context(
    db: DatabasePort,
    document_ids: list[str],
    *,
    max_tokens: int = 4000,
) -> str:
    """Build structured text context from imported DocRef chunks.

    Returns a string suitable for appending to the LLM system prompt context.
    Each document gets an equal share of the token budget.
    """
    if not document_ids:
        return ""

    max_chars = max_tokens * _CHARS_PER_TOKEN

    sections: list[str] = []
    per_doc_chars = max_chars // len(document_ids)

    for doc_id in document_ids:
        doc = await get_document(db, doc_id)
        if doc is None or doc["status"] != "imported":
            continue

        title = str(doc["title"])
        version = str(doc["latest_version"])
        source_url = str(doc["source_url"])

        header = f"LEGISLATION: {title} ({version})\nSource: {source_url}\n\n"

        cursor = await db.execute(
            "SELECT chunk_id, content FROM docref_chunks "
            "WHERE document_id = ? ORDER BY sort_order ASC",
            (doc_id,),
        )
        rows = await cursor.fetchall()

        lines: list[str] = []
        for cid, content in rows:
            lines.append(f"[{cid}] {content}")

        body = "\n".join(lines)
        section = header + body
        sections.append(_truncate_to_budget(section, per_doc_chars))

    return "\n\n---\n\n".join(sections)
