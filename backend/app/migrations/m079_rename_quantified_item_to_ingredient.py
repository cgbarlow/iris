"""Migration 079: rename seeded 'Quantified item' element template → 'Ingredient'.

User reported (issue #211 comment, 2026-05-22) that with the workflow
now framed as Recipes / Weekly Meal Plan, the seeded "Quantified item"
template should be named "Ingredient" so the picker and the elements
list use a user-facing name that matches the domain.

The rename is purely cosmetic — same deterministic id, same stamp body,
same scope. m075 seeded the row originally with name='Quantified item';
this migration updates it in place. Idempotent: the WHERE clause guards
on the original name so re-running does nothing once the rename has
been applied.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m079_rename_quantified_item_to_ingredient"

# Deterministic UUIDv5 from m075's _STAMP_NAMESPACE for
# "global-stamp:Quantified item".
_QUANTIFIED_ITEM_ID = "ea8829e5-6e3f-5cf6-b1cc-a5ad92312dbf"
_NEW_DESCRIPTION = (
    "Element with a numeric quantity + unit (groceries, ingredients, "
    "parts, stock items, line items in a list with totals). Pairs with "
    "the 'Shopping list' / sum-by-unit aggregation profile."
)


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up. Idempotent — WHERE clause guards on the
    pre-rename name."""
    await db.execute(
        "UPDATE element_templates "
        "SET name = ?, description = ? "
        "WHERE id = ? AND name = 'Quantified item'",
        ("Ingredient", _NEW_DESCRIPTION, _QUANTIFIED_ITEM_ID),
    )
    await db.commit()
