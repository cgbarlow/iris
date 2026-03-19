"""Tests for Set context builder (ADR-093)."""

import json
import uuid

import pytest
import pytest_asyncio
import aiosqlite

from app.ai.context import build_set_context


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
            CREATE TABLE set_elements (
                set_id TEXT NOT NULL REFERENCES sets(id),
                element_id TEXT NOT NULL REFERENCES elements(id),
                PRIMARY KEY (set_id, element_id)
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
        "INSERT INTO elements (id, element_type, current_version, created_by, created_at, updated_at) "
        "VALUES (?, ?, 1, 'user1', ?, ?)",
        (elem_id, etype, now, now),
    )
    await db.execute(
        "INSERT INTO element_versions (element_id, version, name, description, data, created_by, created_at) "
        "VALUES (?, 1, ?, ?, '{}', 'user1', ?)",
        (elem_id, name, description, now),
    )
    await db.execute(
        "INSERT INTO set_elements (set_id, element_id) VALUES (?, ?)",
        (set_id, elem_id),
    )
    await db.commit()
    return elem_id


@pytest.mark.asyncio
async def test_empty_set(db):
    set_id = await create_set(db, "Empty Set")
    context = await build_set_context(db, set_id)
    assert "Empty Set" in context
    assert "ELEMENTS (0)" in context
    assert "RELATIONSHIPS (0)" in context
    assert "DIAGRAMS (0)" in context


@pytest.mark.asyncio
async def test_set_not_found(db):
    context = await build_set_context(db, "nonexistent-id")
    assert "not found" in context.lower()


@pytest.mark.asyncio
async def test_with_elements(db):
    set_id = await create_set(db, "Arch Set", "My architecture")
    await create_element(db, set_id, name="UserService", etype="class", description="Handles users")
    await create_element(db, set_id, name="Database", etype="component")

    context = await build_set_context(db, set_id)
    assert "Arch Set" in context
    assert "UserService" in context
    assert "Handles users" in context
    assert "Database" in context
    assert "ELEMENTS (2)" in context


@pytest.mark.asyncio
async def test_truncation(db):
    set_id = await create_set(db, "Big Set")
    # Create many elements to trigger truncation
    for i in range(50):
        await create_element(
            db, set_id, name=f"Element{i}", description="x" * 200
        )
    context = await build_set_context(db, set_id, max_tokens=100)
    # Context should be truncated
    assert len(context) <= 100 * 4 + 200  # some leeway for header + truncation marker
    assert "Big Set" in context  # header always included


@pytest.mark.asyncio
async def test_set_description_included(db):
    set_id = await create_set(db, "Named Set", "This is the set description")
    context = await build_set_context(db, set_id)
    assert "This is the set description" in context
