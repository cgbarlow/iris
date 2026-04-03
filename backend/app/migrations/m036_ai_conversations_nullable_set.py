"""Migration 036: Make ai_conversations.set_id nullable for file-only context."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


async def up(db: aiosqlite.Connection) -> None:
    """Recreate ai_conversations with nullable set_id.

    SQLite does not support ALTER COLUMN, so we recreate the table.
    """
    cursor = await db.execute("PRAGMA table_info(ai_conversations)")
    columns = await cursor.fetchall()
    # Check if set_id is already nullable (notnull == 0)
    for col in columns:
        if col[1] == "set_id" and col[3] == 0:
            return  # Already nullable

    await db.execute("ALTER TABLE ai_conversations RENAME TO _ai_conversations_old")

    await db.execute("""
        CREATE TABLE ai_conversations (
            id              TEXT PRIMARY KEY,
            set_id          TEXT REFERENCES sets(id),
            user_id         TEXT NOT NULL,
            question        TEXT NOT NULL,
            answer          TEXT NOT NULL,
            context_summary TEXT,
            model_used      TEXT NOT NULL,
            provider_id     TEXT REFERENCES ai_providers(id),
            tokens_in       INTEGER,
            tokens_out      INTEGER,
            duration_ms     INTEGER,
            created_at      TEXT NOT NULL,
            mode            TEXT,
            thread_id       TEXT,
            collection_id   TEXT REFERENCES collections(id)
        )
    """)

    await db.execute("""
        INSERT INTO ai_conversations
        SELECT id, set_id, user_id, question, answer, context_summary,
               model_used, provider_id, tokens_in, tokens_out, duration_ms,
               created_at, mode, thread_id, collection_id
        FROM _ai_conversations_old
    """)

    await db.execute("DROP TABLE _ai_conversations_old")
    await db.commit()
