"""Tests for the scope-level system prompt builder (ADR-150)."""

from __future__ import annotations

import aiosqlite
import pytest_asyncio

from app.ai.scope_prompts import build_scope_prompts


@pytest_asyncio.fixture
async def db():
    """Minimal schema with collections + sets columns we need."""
    async with aiosqlite.connect(":memory:") as conn:
        await conn.executescript(
            """
            CREATE TABLE collections (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                is_deleted INTEGER NOT NULL DEFAULT 0,
                system_prompt TEXT
            );
            CREATE TABLE sets (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                is_deleted INTEGER NOT NULL DEFAULT 0,
                collection_id TEXT,
                system_prompt TEXT
            );
            """
        )
        await conn.commit()
        yield conn


async def _insert_collection(db, *, id_: str, name: str, prompt: str | None) -> None:
    await db.execute(
        "INSERT INTO collections (id, name, system_prompt) VALUES (?, ?, ?)",
        (id_, name, prompt),
    )
    await db.commit()


async def _insert_set(
    db,
    *,
    id_: str,
    name: str,
    collection_id: str | None,
    prompt: str | None,
) -> None:
    await db.execute(
        "INSERT INTO sets (id, name, collection_id, system_prompt) VALUES (?, ?, ?, ?)",
        (id_, name, collection_id, prompt),
    )
    await db.commit()


# ---------------------------------------------------------------------------
# Empty / trivial cases
# ---------------------------------------------------------------------------


async def test_empty_set_ids_returns_empty(db):
    assert await build_scope_prompts(db, set_ids=[], collection_id=None) == ""


async def test_set_without_prompt_or_collection_returns_empty(db):
    await _insert_set(db, id_="s1", name="S1", collection_id=None, prompt=None)
    assert (
        await build_scope_prompts(db, set_ids=["s1"], collection_id=None) == ""
    )


async def test_explicit_collection_id_with_no_prompt_returns_empty(db):
    await _insert_collection(db, id_="c1", name="C1", prompt=None)
    assert (
        await build_scope_prompts(db, set_ids=[], collection_id="c1") == ""
    )


# ---------------------------------------------------------------------------
# Composition order
# ---------------------------------------------------------------------------


async def test_set_prompt_only(db):
    await _insert_set(db, id_="s1", name="S1", collection_id=None, prompt="SET PROMPT")
    result = await build_scope_prompts(db, set_ids=["s1"], collection_id=None)
    assert result == "SET PROMPT"


async def test_collection_prompt_only(db):
    await _insert_collection(db, id_="c1", name="C1", prompt="COLL PROMPT")
    result = await build_scope_prompts(db, set_ids=[], collection_id="c1")
    assert result == "COLL PROMPT"


async def test_collection_then_set_order(db):
    await _insert_collection(db, id_="c1", name="C1", prompt="COLL")
    await _insert_set(db, id_="s1", name="S1", collection_id="c1", prompt="SET")
    result = await build_scope_prompts(db, set_ids=["s1"], collection_id=None)
    assert result == "COLL\n\nSET"


async def test_collection_derived_from_set_when_no_explicit_id(db):
    await _insert_collection(db, id_="c1", name="C1", prompt="DERIVED")
    await _insert_set(db, id_="s1", name="S1", collection_id="c1", prompt=None)
    result = await build_scope_prompts(db, set_ids=["s1"], collection_id=None)
    assert result == "DERIVED"


# ---------------------------------------------------------------------------
# Dedup + ordering
# ---------------------------------------------------------------------------


async def test_multi_set_same_collection_dedups_collection_prompt(db):
    await _insert_collection(db, id_="c1", name="C1", prompt="COLL")
    await _insert_set(db, id_="s1", name="S1", collection_id="c1", prompt="SET1")
    await _insert_set(db, id_="s2", name="S2", collection_id="c1", prompt="SET2")
    result = await build_scope_prompts(
        db, set_ids=["s1", "s2"], collection_id=None,
    )
    # Collection prompt appears once, then both set prompts in order.
    assert result == "COLL\n\nSET1\n\nSET2"


async def test_multi_set_multi_collection_concatenates_in_set_order(db):
    await _insert_collection(db, id_="c1", name="C1", prompt="COLL1")
    await _insert_collection(db, id_="c2", name="C2", prompt="COLL2")
    await _insert_set(db, id_="s1", name="S1", collection_id="c1", prompt="SET1")
    await _insert_set(db, id_="s2", name="S2", collection_id="c2", prompt="SET2")
    result = await build_scope_prompts(
        db, set_ids=["s1", "s2"], collection_id=None,
    )
    assert result == "COLL1\n\nCOLL2\n\nSET1\n\nSET2"


async def test_explicit_collection_id_placed_first_then_derived(db):
    # Caller supplied collection_id explicitly. It should appear first,
    # then any other collections derived from the sets.
    await _insert_collection(db, id_="c1", name="C1", prompt="EXPLICIT")
    await _insert_collection(db, id_="c2", name="C2", prompt="DERIVED")
    await _insert_set(db, id_="s1", name="S1", collection_id="c2", prompt=None)
    result = await build_scope_prompts(
        db, set_ids=["s1"], collection_id="c1",
    )
    assert result == "EXPLICIT\n\nDERIVED"


async def test_explicit_collection_id_dedups_against_derived(db):
    await _insert_collection(db, id_="c1", name="C1", prompt="ONLY")
    await _insert_set(db, id_="s1", name="S1", collection_id="c1", prompt=None)
    result = await build_scope_prompts(
        db, set_ids=["s1"], collection_id="c1",
    )
    assert result == "ONLY"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


async def test_missing_collection_in_db_is_silently_skipped(db):
    # A set points at a collection id that doesn't exist (orphan).
    # Should not error; behave as if there is no collection prompt.
    await _insert_set(
        db, id_="s1", name="S1", collection_id="ghost", prompt="SET",
    )
    result = await build_scope_prompts(db, set_ids=["s1"], collection_id=None)
    assert result == "SET"


async def test_whitespace_only_prompt_treated_as_empty(db):
    await _insert_collection(db, id_="c1", name="C1", prompt="   ")
    await _insert_set(db, id_="s1", name="S1", collection_id="c1", prompt="SET")
    result = await build_scope_prompts(db, set_ids=["s1"], collection_id=None)
    assert result == "SET"
