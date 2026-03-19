"""Migration 026: Create AI provider registry and conversation tables (ADR-093)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


async def up(db: aiosqlite.Connection) -> None:
    """Create ai_providers, ai_conversations, and ai_usage_log tables."""
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='ai_providers'"
    )
    if await cursor.fetchone():
        return

    await db.execute("""
        CREATE TABLE ai_providers (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            provider_type TEXT NOT NULL,
            base_url TEXT,
            api_key TEXT,
            model TEXT NOT NULL,
            parameters TEXT NOT NULL DEFAULT '{}',
            system_prompt TEXT,
            timeout_ms INTEGER NOT NULL DEFAULT 30000,
            retries INTEGER NOT NULL DEFAULT 3,
            is_default INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_by TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    await db.execute("""
        CREATE TABLE ai_conversations (
            id TEXT PRIMARY KEY,
            set_id TEXT NOT NULL REFERENCES sets(id),
            user_id TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            context_summary TEXT,
            model_used TEXT NOT NULL,
            provider_id TEXT REFERENCES ai_providers(id),
            tokens_in INTEGER,
            tokens_out INTEGER,
            duration_ms INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    await db.execute("""
        CREATE TABLE ai_usage_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider_id TEXT REFERENCES ai_providers(id),
            user_id TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            model TEXT NOT NULL,
            tokens_in INTEGER,
            tokens_out INTEGER,
            duration_ms INTEGER,
            status TEXT NOT NULL,
            error TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    await db.commit()
