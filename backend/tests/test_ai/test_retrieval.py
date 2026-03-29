"""Tests for RetrievalPort and DirectRetrieval (ADR-111)."""

import uuid

import pytest
import pytest_asyncio
import aiosqlite

from app.ai.retrieval import DirectRetrieval, RetrievalPort


@pytest_asyncio.fixture
async def db():
    async with aiosqlite.connect(":memory:") as conn:
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
                updated_at TEXT,
                parent_package_id TEXT
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


async def _create_set(db, name="Test Set", description="A test set"):
    set_id = str(uuid.uuid4())
    now = "2026-01-01T00:00:00"
    await db.execute(
        "INSERT INTO sets (id, name, description, created_by, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (set_id, name, description, "user1", now, now),
    )
    await db.commit()
    return set_id


async def _create_element(db, set_id, name="Element", etype="class", description=None):
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


class TestDirectRetrieval:
    """DirectRetrieval wraps existing context.py with zero behavior change."""

    @pytest.mark.asyncio
    async def test_implements_protocol(self):
        assert isinstance(DirectRetrieval(), RetrievalPort)

    @pytest.mark.asyncio
    async def test_single_set(self, db):
        set_id = await _create_set(db, "My Set", "Architecture models")
        await _create_element(db, set_id, "UserService", "class", "Handles users")

        retrieval = DirectRetrieval()
        context = await retrieval.retrieve_context(
            db, "What does UserService do?", [set_id],
        )
        assert "My Set" in context
        assert "UserService" in context
        assert "Handles users" in context

    @pytest.mark.asyncio
    async def test_multi_set(self, db):
        set_a = await _create_set(db, "Set A", "First set")
        set_b = await _create_set(db, "Set B", "Second set")
        await _create_element(db, set_a, "ServiceA", "class")
        await _create_element(db, set_b, "ServiceB", "class")

        retrieval = DirectRetrieval()
        context = await retrieval.retrieve_context(
            db, "Compare the services", [set_a, set_b],
        )
        assert "Set A" in context
        assert "Set B" in context
        assert "ServiceA" in context
        assert "ServiceB" in context

    @pytest.mark.asyncio
    async def test_set_not_found(self, db):
        retrieval = DirectRetrieval()
        context = await retrieval.retrieve_context(
            db, "anything", ["nonexistent-id"],
        )
        assert "not found" in context.lower()

    @pytest.mark.asyncio
    async def test_empty_set(self, db):
        set_id = await _create_set(db, "Empty")
        retrieval = DirectRetrieval()
        context = await retrieval.retrieve_context(db, "question", [set_id])
        assert "ELEMENTS (0)" in context

    @pytest.mark.asyncio
    async def test_max_tokens_passed_through(self, db):
        set_id = await _create_set(db, "Big Set")
        for i in range(30):
            await _create_element(db, set_id, f"Elem{i}", description="x" * 200)

        retrieval = DirectRetrieval()
        context = await retrieval.retrieve_context(
            db, "question", [set_id], max_tokens=100,
        )
        # Should be truncated
        assert len(context) <= 100 * 4 + 200
