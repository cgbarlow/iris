"""Integration tests: scope prompts flow into composed system_content.

ADR-150 / SPEC-150-A. Asks the question through the real service path
with a stub AI client so we can assert the exact `system_content` the
model receives.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import aiosqlite
import pytest
import pytest_asyncio

from app.ai import service as ai_service
from app.ai.client import AIClient
from app.ai.models import ProviderTestResult


_USER_ID = "test-user"


class RecordingClient(AIClient):
    """Captures the messages the service composes for the LLM."""

    last_messages: list[dict[str, str]] | None = None

    def __init__(self, provider_row: dict[str, object]) -> None:  # noqa: ARG002
        self.stream_usage: tuple[int | None, int | None] = (1, 2)

    async def chat(
        self, messages: list[dict[str, str]],
    ) -> tuple[str, int | None, int | None]:
        RecordingClient.last_messages = messages
        return ("stub answer", 1, 2)

    async def chat_stream(
        self, messages: list[dict[str, str]],
    ) -> AsyncIterator[str]:
        RecordingClient.last_messages = messages
        yield "stub answer"

    async def test_connection(self) -> ProviderTestResult:
        return ProviderTestResult(ok=True)


@pytest_asyncio.fixture
async def db():
    """Minimal direct schema (we bypass the full migration chain so the test
    doesn't depend on every upstream table)."""
    async with aiosqlite.connect(":memory:") as conn:
        await conn.executescript(
            """
            CREATE TABLE collections (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                is_deleted INTEGER NOT NULL DEFAULT 0,
                system_prompt TEXT
            );
            CREATE TABLE sets (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                is_deleted INTEGER NOT NULL DEFAULT 0,
                collection_id TEXT,
                system_prompt TEXT
            );
            CREATE TABLE ai_providers (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                provider_type TEXT NOT NULL,
                base_url TEXT,
                api_key TEXT,
                model TEXT NOT NULL,
                system_prompt TEXT,
                parameters TEXT,
                timeout_ms INTEGER NOT NULL DEFAULT 30000,
                retries INTEGER NOT NULL DEFAULT 3,
                is_default INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE ai_conversations (
                id TEXT PRIMARY KEY,
                set_id TEXT,
                user_id TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                context_summary TEXT,
                model_used TEXT NOT NULL,
                provider_id TEXT NOT NULL,
                tokens_in INTEGER,
                tokens_out INTEGER,
                duration_ms INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                mode TEXT,
                thread_id TEXT,
                collection_id TEXT
            );
            CREATE TABLE ai_usage_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider_id TEXT NOT NULL,
                user_id TEXT,
                endpoint TEXT NOT NULL,
                model TEXT NOT NULL,
                tokens_in INTEGER,
                tokens_out INTEGER,
                duration_ms INTEGER NOT NULL,
                status TEXT NOT NULL,
                error TEXT,
                created_at TEXT NOT NULL
            );
            -- minimal tables retrieval.py touches; we leave them empty so
            -- retrieve_context returns "".
            CREATE TABLE elements (
                id TEXT PRIMARY KEY,
                element_type TEXT NOT NULL,
                current_version INTEGER NOT NULL DEFAULT 1,
                set_id TEXT,
                is_deleted INTEGER NOT NULL DEFAULT 0,
                created_by TEXT, created_at TEXT, updated_at TEXT
            );
            CREATE TABLE element_versions (
                element_id TEXT NOT NULL, version INTEGER NOT NULL,
                name TEXT NOT NULL, description TEXT,
                data TEXT NOT NULL DEFAULT '{}',
                created_by TEXT, created_at TEXT,
                PRIMARY KEY (element_id, version)
            );
            CREATE TABLE relationships (
                id TEXT PRIMARY KEY,
                source_element_id TEXT NOT NULL,
                target_element_id TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                is_deleted INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE diagrams (
                id TEXT PRIMARY KEY,
                diagram_type TEXT NOT NULL,
                current_version INTEGER NOT NULL DEFAULT 1,
                set_id TEXT,
                is_deleted INTEGER NOT NULL DEFAULT 0,
                created_by TEXT, created_at TEXT, updated_at TEXT
            );
            CREATE TABLE diagram_versions (
                diagram_id TEXT NOT NULL, version INTEGER NOT NULL,
                name TEXT NOT NULL, description TEXT,
                data TEXT NOT NULL DEFAULT '{}',
                created_by TEXT, created_at TEXT,
                PRIMARY KEY (diagram_id, version)
            );
            CREATE TABLE settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            """
        )
        await conn.commit()
        yield conn


async def _make_provider(db: Any) -> str:
    p = await ai_service.create_provider(
        db, name="stub", provider_type="openai", model="stub-model",
        is_default=True, created_by=_USER_ID,
    )
    return str(p["id"])


async def _make_set(
    db: Any, *, set_id: str, name: str,
    collection_id: str | None = None, system_prompt: str | None = None,
) -> None:
    await db.execute(
        "INSERT INTO sets (id, name, description, created_at, created_by, "
        "updated_at, collection_id, system_prompt) "
        "VALUES (?, ?, NULL, '2026-01-01', ?, '2026-01-01', ?, ?)",
        (set_id, name, _USER_ID, collection_id, system_prompt),
    )
    await db.commit()


async def _make_collection(
    db: Any, *, collection_id: str, name: str, system_prompt: str | None = None,
) -> None:
    await db.execute(
        "INSERT INTO collections (id, name, description, created_at, created_by, "
        "updated_at, system_prompt) "
        "VALUES (?, ?, NULL, '2026-01-01', ?, '2026-01-01', ?)",
        (collection_id, name, _USER_ID, system_prompt),
    )
    await db.commit()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def stub_client(monkeypatch):
    monkeypatch.setattr(ai_service, "create_ai_client", RecordingClient)
    RecordingClient.last_messages = None


async def test_set_prompt_is_prepended(db):
    await _make_provider(db)
    await _make_set(db, set_id="s1", name="S1", system_prompt="USE FOO")
    await ai_service.ask_question(
        db, set_id="s1", question="hi", user_id=_USER_ID,
    )
    sys = RecordingClient.last_messages[0]["content"]
    assert sys.startswith("USE FOO\n\n")


async def test_collection_then_set_order(db):
    await _make_provider(db)
    await _make_collection(db, collection_id="c1", name="C1", system_prompt="COLL")
    await _make_set(
        db, set_id="s1", name="S1", collection_id="c1", system_prompt="SET",
    )
    await ai_service.ask_question(
        db, set_id="s1", question="hi", user_id=_USER_ID,
    )
    sys = RecordingClient.last_messages[0]["content"]
    assert sys.startswith("COLL\n\nSET\n\n")
    # Collection prompt must come strictly before set prompt.
    assert sys.index("COLL") < sys.index("SET")


async def test_no_prompts_leaves_legacy_system_content(db):
    await _make_provider(db)
    await _make_set(db, set_id="s1", name="S1")
    await ai_service.ask_question(
        db, set_id="s1", question="hi", user_id=_USER_ID,
    )
    sys = RecordingClient.last_messages[0]["content"]
    # Should fall through to the existing default boilerplate.
    assert sys.startswith("You are an AI assistant")


async def test_multi_set_dedups_collection_prompt(db):
    await _make_provider(db)
    await _make_collection(db, collection_id="c1", name="C1", system_prompt="COLL")
    await _make_set(
        db, set_id="s1", name="S1", collection_id="c1", system_prompt="SETA",
    )
    await _make_set(
        db, set_id="s2", name="S2", collection_id="c1", system_prompt="SETB",
    )
    await ai_service.ask_multi_set_question(
        db, set_ids=["s1", "s2"], question="hi", user_id=_USER_ID,
    )
    sys = RecordingClient.last_messages[0]["content"]
    # COLL exactly once; SETA before SETB.
    assert sys.count("COLL") == 1
    assert sys.index("SETA") < sys.index("SETB")
