"""Tests for the geanz-default seed theme (ADR-230 / SPEC-230-A AC4).

The GEANZ Common Business Capabilities set must render faithfully to the
Sparx EA ground-truth: white capabilities with a royal-blue border, no
ArchiMate icon or description text, rounded corners, left-aligned labels.
The shared defaults live in the geanz-default theme; per-archetype
specifics ride on each node's data.visual at import time.
"""

from __future__ import annotations

import aiosqlite
import pytest
import pytest_asyncio

from app.migrations.m024_themes import up as m024_up
from app.themes.service import get_theme, seed_default_themes


@pytest_asyncio.fixture
async def db():
    async with aiosqlite.connect(":memory:") as conn:
        await m024_up(conn)
        await seed_default_themes(conn)
        yield conn


@pytest.mark.asyncio
async def test_geanz_theme_seeded(db):
    theme = await get_theme(db, "geanz-default")
    assert theme is not None, "geanz-default theme not found after seeding"
    assert theme["notation"] == "uml"
    assert theme["is_default"] is True


@pytest.mark.asyncio
async def test_geanz_theme_capability_default(db):
    theme = await get_theme(db, "geanz-default")
    cap = theme["config"]["element_defaults"]["capability"]
    assert cap["bgColor"] == "#ffffff"
    assert cap["borderColor"] == "#4169e1"
    assert cap["bold"] is True


@pytest.mark.asyncio
async def test_geanz_theme_rendering_hints(db):
    """Icons + descriptions hidden, modest radius, labels left-aligned."""
    theme = await get_theme(db, "geanz-default")
    rendering = theme["config"]["rendering"]
    assert rendering.get("hideIcons") is True
    assert rendering.get("hideDescription") is True
    assert rendering.get("borderRadius") == 10
    assert rendering.get("textAlign") == "left"


@pytest.mark.asyncio
async def test_geanz_theme_idempotent_reseed(db):
    """Re-seeding (startup upsert) must not duplicate or change the theme."""
    await seed_default_themes(db)
    cursor = await db.execute("SELECT COUNT(*) FROM themes WHERE id = 'geanz-default'")
    assert (await cursor.fetchone())[0] == 1
