"""Test for m079_rename_quantified_item_to_ingredient.

Verifies the migration:
  - Renames "Quantified item" → "Ingredient" on the deterministic row id.
  - Is idempotent (running twice doesn't double-rename / break).
  - Doesn't touch other rows.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import aiosqlite
import pytest

from app.migrations.m001_roles_users import up as m001
from app.migrations.m067_element_templates import up as m067
from app.migrations.m074_element_template_markdown_stamp import up as m074
from app.migrations.m075_seed_global_element_template_stamps import up as m075
from app.migrations.m079_rename_quantified_item_to_ingredient import (
    up as m079,
)

if TYPE_CHECKING:
    pass

_QUANTIFIED_ITEM_ID = "ea8829e5-6e3f-5cf6-b1cc-a5ad92312dbf"


@pytest.fixture
async def db() -> aiosqlite.Connection:
    conn = await aiosqlite.connect(":memory:")
    await m001(conn)
    await m067(conn)
    await m074(conn)
    await m075(conn)
    yield conn
    await conn.close()


@pytest.mark.asyncio
async def test_rename_renames_the_seeded_row(db: aiosqlite.Connection) -> None:
    # Pre: row is "Quantified item".
    cur = await db.execute(
        "SELECT name FROM element_templates WHERE id = ?",
        (_QUANTIFIED_ITEM_ID,),
    )
    row = await cur.fetchone()
    assert row is not None
    assert row[0] == "Quantified item"

    await m079(db)

    # Post: row is "Ingredient".
    cur = await db.execute(
        "SELECT name FROM element_templates WHERE id = ?",
        (_QUANTIFIED_ITEM_ID,),
    )
    row = await cur.fetchone()
    assert row[0] == "Ingredient"


@pytest.mark.asyncio
async def test_rename_is_idempotent(db: aiosqlite.Connection) -> None:
    await m079(db)
    # Re-running should be a no-op (WHERE guards on the old name).
    await m079(db)

    cur = await db.execute(
        "SELECT name FROM element_templates WHERE id = ?",
        (_QUANTIFIED_ITEM_ID,),
    )
    row = await cur.fetchone()
    assert row[0] == "Ingredient"


@pytest.mark.asyncio
async def test_rename_leaves_other_seeded_stamps_alone(
    db: aiosqlite.Connection,
) -> None:
    await m079(db)
    # The other four seeded stamps keep their names.
    cur = await db.execute(
        "SELECT name FROM element_templates "
        "WHERE is_global = 1 AND id != ? ORDER BY name",
        (_QUANTIFIED_ITEM_ID,),
    )
    rows = await cur.fetchall()
    names = sorted(r[0] for r in rows)
    assert "Line item" in names
    assert "Logged work" in names
    assert "Read entry" in names
    assert "Sized story" in names
    # The renamed row's old name doesn't reappear.
    assert "Quantified item" not in names


@pytest.mark.asyncio
async def test_rename_updates_description_too(
    db: aiosqlite.Connection,
) -> None:
    await m079(db)
    cur = await db.execute(
        "SELECT description FROM element_templates WHERE id = ?",
        (_QUANTIFIED_ITEM_ID,),
    )
    row = await cur.fetchone()
    # Description should mention "ingredients" in the new copy.
    assert row[0] is not None
    assert "ingredients" in row[0].lower()
