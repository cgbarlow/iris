"""Tests for AI service CRUD and usage logging (ADR-093)."""

import pytest
import pytest_asyncio
import aiosqlite

from app.ai.service import (
    create_provider,
    delete_provider,
    get_default_provider,
    get_provider,
    list_providers,
    log_usage,
    set_default_provider,
    update_provider,
)
from app.migrations.m026_ai_providers import up as m026_up


@pytest_asyncio.fixture
async def db():
    async with aiosqlite.connect(":memory:") as conn:
        # Minimal sets table (m026 ai_conversations FKs sets)
        await conn.execute("""
            CREATE TABLE sets (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                is_deleted INTEGER NOT NULL DEFAULT 0
            )
        """)
        await m026_up(conn)
        yield conn


@pytest.mark.asyncio
async def test_create_provider(db):
    p = await create_provider(
        db,
        name="OpenAI Prod",
        provider_type="openai",
        model="gpt-4o",
        created_by="admin",
    )
    assert p["name"] == "OpenAI Prod"
    assert p["provider_type"] == "openai"
    assert p["model"] == "gpt-4o"
    assert p["is_default"] is False
    assert p["is_active"] is True


@pytest.mark.asyncio
async def test_get_provider(db):
    created = await create_provider(db, name="x", provider_type="ollama", model="llama3")
    fetched = await get_provider(db, created["id"])
    assert fetched is not None
    assert fetched["id"] == created["id"]
    assert fetched["name"] == "x"


@pytest.mark.asyncio
async def test_get_provider_not_found(db):
    result = await get_provider(db, "nonexistent-id")
    assert result is None


@pytest.mark.asyncio
async def test_list_providers(db):
    await create_provider(db, name="p1", provider_type="openai", model="gpt-4o")
    await create_provider(db, name="p2", provider_type="ollama", model="llama3")
    providers = await list_providers(db)
    assert len(providers) == 2


@pytest.mark.asyncio
async def test_list_providers_active_only(db):
    await create_provider(db, name="active", provider_type="openai", model="gpt-4o", is_active=True)
    await create_provider(db, name="inactive", provider_type="openai", model="gpt-4o", is_active=False)
    all_p = await list_providers(db)
    active_p = await list_providers(db, active_only=True)
    assert len(all_p) == 2
    assert len(active_p) == 1
    assert active_p[0]["name"] == "active"


@pytest.mark.asyncio
async def test_update_provider(db):
    p = await create_provider(db, name="original", provider_type="openai", model="gpt-3.5")
    updated = await update_provider(
        db, p["id"], name="updated", provider_type="openai", model="gpt-4o"
    )
    assert updated is not None
    assert updated["name"] == "updated"
    assert updated["model"] == "gpt-4o"


@pytest.mark.asyncio
async def test_update_provider_not_found(db):
    result = await update_provider(
        db, "no-such-id", name="x", provider_type="openai", model="m"
    )
    assert result is None


@pytest.mark.asyncio
async def test_delete_provider(db):
    p = await create_provider(db, name="deleteme", provider_type="openai", model="m")
    deleted = await delete_provider(db, p["id"])
    assert deleted is True
    assert await get_provider(db, p["id"]) is None


@pytest.mark.asyncio
async def test_delete_default_provider_refused(db):
    p = await create_provider(db, name="def", provider_type="openai", model="m", is_default=True)
    result = await delete_provider(db, p["id"])
    assert result is False


@pytest.mark.asyncio
async def test_set_default_provider(db):
    p1 = await create_provider(db, name="p1", provider_type="openai", model="m", is_default=True)
    p2 = await create_provider(db, name="p2", provider_type="ollama", model="llama3")
    await set_default_provider(db, p2["id"])
    updated_p1 = await get_provider(db, p1["id"])
    updated_p2 = await get_provider(db, p2["id"])
    assert updated_p1 is not None
    assert updated_p1["is_default"] is False
    assert updated_p2 is not None
    assert updated_p2["is_default"] is True


@pytest.mark.asyncio
async def test_get_default_provider(db):
    assert await get_default_provider(db) is None
    await create_provider(db, name="def", provider_type="openai", model="gpt-4o", is_default=True)
    result = await get_default_provider(db)
    assert result is not None
    assert result["name"] == "def"


@pytest.mark.asyncio
async def test_create_provider_sets_default_clears_previous(db):
    p1 = await create_provider(db, name="p1", provider_type="openai", model="m", is_default=True)
    assert p1["is_default"] is True
    p2 = await create_provider(db, name="p2", provider_type="openai", model="m2", is_default=True)
    p1_updated = await get_provider(db, p1["id"])
    assert p1_updated is not None
    assert p1_updated["is_default"] is False
    assert p2["is_default"] is True


@pytest.mark.asyncio
async def test_log_usage(db):
    p = await create_provider(db, name="p", provider_type="openai", model="gpt-4o")
    await log_usage(
        db,
        provider_id=str(p["id"]),
        user_id="user1",
        endpoint="ask",
        model="gpt-4o",
        tokens_in=100,
        tokens_out=200,
        duration_ms=1500,
        status="success",
    )
    cursor = await db.execute("SELECT COUNT(*) FROM ai_usage_log")
    count = (await cursor.fetchone())[0]
    assert count == 1
