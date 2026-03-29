"""Migration 034: Create DocRef legislation tables."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


async def up(db: aiosqlite.Connection) -> None:
    """Create DocRef tables for document metadata and content chunks."""
    # Guard: skip if docref_documents already exists
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='docref_documents'"
    )
    if await cursor.fetchone():
        return

    await db.execute(
        "CREATE TABLE IF NOT EXISTS docref_documents ("
        "  id TEXT PRIMARY KEY,"
        "  slug TEXT NOT NULL,"
        "  title TEXT NOT NULL,"
        "  latest_version TEXT NOT NULL,"
        "  source_url TEXT NOT NULL,"
        "  csv_url TEXT NOT NULL,"
        "  chunk_count INTEGER NOT NULL DEFAULT 0,"
        "  status TEXT NOT NULL DEFAULT 'available',"
        "  error_message TEXT,"
        "  imported_at TEXT,"
        "  imported_by TEXT,"
        "  created_at TEXT NOT NULL,"
        "  updated_at TEXT NOT NULL,"
        "  UNIQUE(slug, latest_version)"
        ")"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_docref_documents_slug "
        "ON docref_documents(slug)"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_docref_documents_status "
        "ON docref_documents(status)"
    )

    await db.execute(
        "CREATE TABLE IF NOT EXISTS docref_chunks ("
        "  id TEXT PRIMARY KEY,"
        "  document_id TEXT NOT NULL REFERENCES docref_documents(id) ON DELETE CASCADE,"
        "  chunk_id TEXT NOT NULL,"
        "  url TEXT NOT NULL,"
        "  content TEXT NOT NULL,"
        "  sort_order INTEGER NOT NULL DEFAULT 0,"
        "  UNIQUE(document_id, chunk_id)"
        ")"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_docref_chunks_document_id "
        "ON docref_chunks(document_id)"
    )

    await db.commit()
