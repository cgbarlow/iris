"""Tests for multi-set context builder (ADR-102)."""

import uuid

import aiosqlite
import pytest_asyncio

from app.ai.context import build_multi_set_context, build_set_context


@pytest_asyncio.fixture
async def db():
    async with aiosqlite.connect(":memory:") as conn:
        # Minimal schema for context builder
        await conn.executescript("""
            CREATE TABLE sets (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                is_deleted INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE elements (
                id TEXT PRIMARY KEY,
                element_type TEXT NOT NULL,
                current_version INTEGER NOT NULL DEFAULT 1,
                set_id TEXT REFERENCES sets(id),
                is_deleted INTEGER NOT NULL DEFAULT 0,
                created_by TEXT,
                created_at TEXT,
                updated_at TEXT
            );
            CREATE TABLE element_versions (
                element_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                data TEXT NOT NULL DEFAULT '{}',
                created_by TEXT,
                created_at TEXT,
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
                set_id TEXT REFERENCES sets(id),
                is_deleted INTEGER NOT NULL DEFAULT 0,
                created_by TEXT,
                created_at TEXT,
                updated_at TEXT
            );
            CREATE TABLE diagram_versions (
                diagram_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                data TEXT NOT NULL DEFAULT '{}',
                created_by TEXT,
                created_at TEXT,
                PRIMARY KEY (diagram_id, version)
            );
        """)
        await conn.commit()
        yield conn


async def create_set(db, name="Test Set", description="A test set"):
    set_id = str(uuid.uuid4())
    now = "2026-01-01T00:00:00"
    await db.execute(
        "INSERT INTO sets (id, name, description, created_by, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (set_id, name, description, "user1", now, now),
    )
    await db.commit()
    return set_id


async def create_element(db, set_id, name="Element", etype="class", description=None):
    elem_id = str(uuid.uuid4())
    now = "2026-01-01T00:00:00"
    await db.execute(
        "INSERT INTO elements (id, element_type, current_version, set_id, created_by, created_at, updated_at) "
        "VALUES (?, ?, 1, ?, 'user1', ?, ?)",
        (elem_id, etype, set_id, now, now),
    )
    await db.execute(
        "INSERT INTO element_versions (element_id, version, name, description, data, created_by, created_at) "
        "VALUES (?, 1, ?, ?, '{}', 'user1', ?)",
        (elem_id, name, description, now),
    )
    await db.commit()
    return elem_id


async def test_single_set(db):
    """build_multi_set_context with 1 set_id should produce same result as build_set_context."""
    set_id = await create_set(db, "Solo Set", "Only set")
    await create_element(db, set_id, name="Widget", etype="component")

    single_ctx = await build_set_context(db, set_id)
    multi_ctx = await build_multi_set_context(db, [set_id])

    assert single_ctx == multi_ctx


async def test_multiple_sets(db):
    """build_multi_set_context with 2 set IDs should contain both set names."""
    set_id_a = await create_set(db, "Set Alpha", "First set")
    set_id_b = await create_set(db, "Set Beta", "Second set")
    await create_element(db, set_id_a, name="AlphaElement", etype="class")
    await create_element(db, set_id_b, name="BetaElement", etype="class")

    context = await build_multi_set_context(db, [set_id_a, set_id_b])

    assert "MULTI-SET CONTEXT (2 sets)" in context
    assert "Set Alpha" in context
    assert "Set Beta" in context
    assert "AlphaElement" in context
    assert "BetaElement" in context
    assert "---" in context  # divider between sets


async def test_empty_set_ids(db):
    """build_multi_set_context with no set IDs returns 'No sets selected.'."""
    context = await build_multi_set_context(db, [])
    assert context == "No sets selected."
