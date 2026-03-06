"""Tests for EA seed theme rendering config (ADR-086).

Verifies the ea-default-uml theme includes rendering flags for
faithful EA parity: hideTypeStereotypes and abstractBoldOverride.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
import aiosqlite

from app.themes.service import get_theme, seed_default_themes
from app.migrations.m024_themes import up as m024_up


@pytest_asyncio.fixture
async def db():
    """Create an in-memory database with themes table and seed defaults."""
    async with aiosqlite.connect(":memory:") as conn:
        await m024_up(conn)
        await seed_default_themes(conn)
        yield conn


@pytest.mark.asyncio
async def test_ea_theme_has_rendering_config(db):
    """The ea-default-uml theme must have a 'rendering' section in its config."""
    theme = await get_theme(db, "ea-default-uml")
    assert theme is not None, "ea-default-uml theme not found after seeding"
    config = theme["config"]
    assert "rendering" in config, "EA theme config missing 'rendering' key"


@pytest.mark.asyncio
async def test_ea_theme_hide_type_stereotypes(db):
    """EA theme rendering config must set hideTypeStereotypes to True.

    In EA, stereotypes like <<feature>>, <<DataType>> etc. are NOT shown
    in the type compartment -- they only affect colouring.
    """
    theme = await get_theme(db, "ea-default-uml")
    assert theme is not None
    rendering = theme["config"]["rendering"]
    assert rendering.get("hideTypeStereotypes") is True, (
        f"Expected hideTypeStereotypes=True, got {rendering.get('hideTypeStereotypes')}"
    )


@pytest.mark.asyncio
async def test_ea_theme_abstract_bold_override(db):
    """EA theme rendering config must set abstractBoldOverride to False.

    EA renders abstract class names in italic only, never bold-italic.
    """
    theme = await get_theme(db, "ea-default-uml")
    assert theme is not None
    rendering = theme["config"]["rendering"]
    assert rendering.get("abstractBoldOverride") is False, (
        f"Expected abstractBoldOverride=False, got {rendering.get('abstractBoldOverride')}"
    )
