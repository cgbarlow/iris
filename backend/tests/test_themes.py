"""Tests for theme API and service (ADR-084)."""

import json

import pytest
import pytest_asyncio
import aiosqlite

from app.themes.service import (
    create_theme,
    delete_theme,
    get_theme,
    list_themes,
    seed_default_themes,
    update_theme,
)
from app.migrations.m024_themes import up as m024_up


@pytest_asyncio.fixture
async def db():
    """Create an in-memory database with themes table."""
    async with aiosqlite.connect(":memory:") as conn:
        await m024_up(conn)
        yield conn


@pytest.mark.asyncio
async def test_create_theme(db):
    result = await create_theme(
        db,
        name="Test Theme",
        description="A test theme",
        notation="uml",
        config={"global": {"defaultBgColor": "#fff"}},
        created_by="user1",
    )
    assert result["name"] == "Test Theme"
    assert result["notation"] == "uml"
    assert result["config"]["global"]["defaultBgColor"] == "#fff"
    assert result["is_default"] is False


@pytest.mark.asyncio
async def test_list_themes(db):
    await create_theme(db, name="T1", notation="uml", created_by="u")
    await create_theme(db, name="T2", notation="simple", created_by="u")
    all_themes = await list_themes(db)
    assert len(all_themes) == 2

    uml_themes = await list_themes(db, notation="uml")
    assert len(uml_themes) == 1
    assert uml_themes[0]["name"] == "T1"


@pytest.mark.asyncio
async def test_get_theme(db):
    created = await create_theme(db, name="Get Me", notation="c4", created_by="u")
    result = await get_theme(db, created["id"])
    assert result is not None
    assert result["name"] == "Get Me"


@pytest.mark.asyncio
async def test_get_theme_not_found(db):
    assert await get_theme(db, "nonexistent") is None


@pytest.mark.asyncio
async def test_update_theme(db):
    created = await create_theme(db, name="Old Name", notation="uml", created_by="u")
    updated = await update_theme(
        db, created["id"],
        name="New Name",
        notation="uml",
        config={"global": {"defaultBgColor": "#000"}},
    )
    assert updated is not None
    assert updated["name"] == "New Name"
    assert updated["config"]["global"]["defaultBgColor"] == "#000"


@pytest.mark.asyncio
async def test_update_theme_not_found(db):
    assert await update_theme(db, "nope", name="X", notation="uml") is None


@pytest.mark.asyncio
async def test_delete_theme(db):
    created = await create_theme(db, name="Delete Me", notation="uml", created_by="u")
    assert await delete_theme(db, created["id"]) is True
    assert await get_theme(db, created["id"]) is None


@pytest.mark.asyncio
async def test_delete_default_theme_fails(db):
    created = await create_theme(
        db, name="Default", notation="uml", is_default=True, created_by="u"
    )
    assert await delete_theme(db, created["id"]) is False


@pytest.mark.asyncio
async def test_seed_default_themes(db):
    await seed_default_themes(db)
    all_themes = await list_themes(db)
    assert len(all_themes) >= 3  # iris-default-uml, ea-default-uml, iris-default-simple

    # Verify EA theme has correct structure
    ea_themes = [t for t in all_themes if "EA" in str(t["name"])]
    assert len(ea_themes) == 1
    ea = ea_themes[0]
    assert ea["notation"] == "uml"
    assert "stereotype_overrides" in ea["config"]
    assert "feature" in ea["config"]["stereotype_overrides"]


@pytest.mark.asyncio
async def test_seed_idempotent(db):
    await seed_default_themes(db)
    count1 = len(await list_themes(db))
    await seed_default_themes(db)
    count2 = len(await list_themes(db))
    assert count1 == count2


@pytest.mark.asyncio
async def test_migration_idempotent(db):
    """Running migration twice should not fail."""
    await m024_up(db)
    # Should not raise
