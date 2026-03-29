"""Tests for MNEMOS engram mapping (ADR-111)."""

import uuid

import pytest
import pytest_asyncio
import aiosqlite

from app.mnemos.engram_mapper import (
    build_all_engrams,
    diagram_to_engram,
    element_to_engram,
    relationship_to_engram,
)


class TestElementToEngram:
    def test_basic_element(self):
        engram = element_to_engram(
            "e1", "class", "UserService", "Handles user accounts", None, "s1",
        )
        assert engram["content"] == "[class] UserService: Handles user accounts"
        assert engram["source"] == "iris://elements/e1"
        assert "element" in engram["neuro_tags"]
        assert "type:class" in engram["neuro_tags"]
        assert "set:s1" in engram["neuro_tags"]
        assert engram["metadata"]["iris_id"] == "e1"

    def test_element_with_stereotypes(self):
        engram = element_to_engram(
            "e2", "component", "API Gateway", None,
            {"technology": "Kong", "stereotype": "gateway"},
            "s1",
        )
        assert "technology=Kong" in engram["content"]
        assert "stereotype=gateway" in engram["content"]

    def test_element_without_set(self):
        engram = element_to_engram("e3", "interface", "IAuth", None, None, None)
        assert "set:" not in " ".join(engram["neuro_tags"])


class TestRelationshipToEngram:
    def test_basic_relationship(self):
        engram = relationship_to_engram(
            "r1", "depends_on", "ServiceA", "ServiceB", None, "s1",
        )
        assert engram["content"] == "ServiceA --[depends_on]--> ServiceB"
        assert engram["source"] == "iris://relationships/r1"
        assert "relationship" in engram["neuro_tags"]

    def test_relationship_with_label(self):
        engram = relationship_to_engram(
            "r2", "calls", "Frontend", "API", "REST calls", "s1",
        )
        assert "REST calls" in engram["content"]


class TestDiagramToEngram:
    def test_basic_diagram(self):
        engram = diagram_to_engram(
            "d1", "architecture", "System Overview", "High-level view", "s1", "p1",
        )
        assert engram["content"] == "[architecture] System Overview: High-level view"
        assert engram["source"] == "iris://diagrams/d1"
        assert "diagram" in engram["neuro_tags"]
        assert "pkg:p1" in engram["neuro_tags"]

    def test_diagram_without_package(self):
        engram = diagram_to_engram("d2", "uml", "Classes", None, "s1", None)
        assert "pkg:" not in " ".join(engram["neuro_tags"])


@pytest_asyncio.fixture
async def db():
    async with aiosqlite.connect(":memory:") as conn:
        await conn.executescript("""
            CREATE TABLE sets (
                id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE,
                description TEXT, created_at TEXT NOT NULL,
                created_by TEXT NOT NULL, updated_at TEXT NOT NULL,
                is_deleted INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE elements (
                id TEXT PRIMARY KEY, element_type TEXT NOT NULL,
                current_version INTEGER NOT NULL DEFAULT 1,
                set_id TEXT, is_deleted INTEGER NOT NULL DEFAULT 0,
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
            CREATE TABLE relationship_versions (
                relationship_id TEXT NOT NULL, version INTEGER NOT NULL,
                label TEXT, description TEXT,
                data TEXT NOT NULL DEFAULT '{}',
                created_by TEXT, created_at TEXT,
                PRIMARY KEY (relationship_id, version)
            );
            CREATE TABLE diagrams (
                id TEXT PRIMARY KEY, diagram_type TEXT NOT NULL,
                current_version INTEGER NOT NULL DEFAULT 1,
                set_id TEXT, is_deleted INTEGER NOT NULL DEFAULT 0,
                parent_package_id TEXT,
                created_by TEXT, created_at TEXT, updated_at TEXT
            );
            CREATE TABLE diagram_versions (
                diagram_id TEXT NOT NULL, version INTEGER NOT NULL,
                name TEXT NOT NULL, description TEXT,
                data TEXT NOT NULL DEFAULT '{}',
                created_by TEXT, created_at TEXT,
                PRIMARY KEY (diagram_id, version)
            );
        """)
        await conn.commit()
        yield conn


@pytest.mark.asyncio
async def test_build_all_engrams_empty(db):
    engrams = await build_all_engrams(db)
    assert engrams == []


@pytest.mark.asyncio
async def test_build_all_engrams_with_data(db):
    now = "2026-01-01T00:00:00"
    sid = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO sets VALUES (?, 'Test', 'desc', ?, 'user', ?, 0)",
        (sid, now, now),
    )
    eid = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO elements VALUES (?, 'class', 1, ?, 0, 'user', ?, ?)",
        (eid, sid, now, now),
    )
    await db.execute(
        "INSERT INTO element_versions VALUES (?, 1, 'MyClass', 'A class', '{}', 'user', ?)",
        (eid, now),
    )
    did = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO diagrams VALUES (?, 'uml', 1, ?, 0, NULL, 'user', ?, ?)",
        (did, sid, now, now),
    )
    await db.execute(
        "INSERT INTO diagram_versions VALUES (?, 1, 'ClassDiagram', 'UML classes', '{}', 'user', ?)",
        (did, now),
    )
    await db.commit()

    engrams = await build_all_engrams(db)
    assert len(engrams) == 2
    sources = [e["source"] for e in engrams]
    assert f"iris://elements/{eid}" in sources
    assert f"iris://diagrams/{did}" in sources
