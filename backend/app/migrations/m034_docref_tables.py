"""Migration 034: Create DocRef legislation tables and make ai_conversations.set_id nullable."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


async def up(db: aiosqlite.Connection) -> None:
    """Create DocRef tables for document metadata and content chunks."""
    # Create docref tables (guarded — skip if already exist)
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='docref_documents'"
    )
    if not await cursor.fetchone():
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

    # Make ai_conversations.set_id nullable for docref-only queries.
    # SQLite doesn't support ALTER COLUMN, so recreate the table.
    cursor = await db.execute("PRAGMA table_info(ai_conversations)")
    cols = await cursor.fetchall()
    set_id_col = next((c for c in cols if c[1] == "set_id"), None)
    if set_id_col and set_id_col[3] == 1:  # notnull == 1
        col_names = [c[1] for c in cols]
        col_list = ", ".join(col_names)
        await db.executescript(f"""
            CREATE TABLE ai_conversations_new (
                id TEXT PRIMARY KEY,
                set_id TEXT REFERENCES sets(id),
                user_id TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                context_summary TEXT,
                model_used TEXT NOT NULL,
                provider_id TEXT REFERENCES ai_providers(id),
                tokens_in INTEGER,
                tokens_out INTEGER,
                duration_ms INTEGER,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                collection_id TEXT,
                mode TEXT DEFAULT 'discuss',
                thread_id TEXT
            );
            INSERT INTO ai_conversations_new ({col_list})
                SELECT {col_list} FROM ai_conversations;
            DROP TABLE ai_conversations;
            ALTER TABLE ai_conversations_new RENAME TO ai_conversations;
        """)

    await db.commit()
