"""Migration 071: rename 'text' diagram type to 'Standard Markdown' (v6.14.1).

User feedback during the v6.14.0 smoke: the 'Text' label on the
markdown notation's default diagram type was ambiguous next to
'Dynamic List' and 'Smart Markdown'. Rename to 'Standard Markdown'
to read coherently as one of three markdown-notation flavours.

The diagram_type ``id`` stays ``text`` — only the display name and
description change, so existing diagrams keep working without
needing to be re-pointed.

Idempotent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m071_rename_text_to_standard_markdown"

_NEW_NAME = "Standard Markdown"
_NEW_DESC = "Plain markdown source rendered as a document with TOC drawer"


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up. Idempotent — UPDATE is naturally so."""
    await db.execute(
        "UPDATE diagram_types SET name = ?, description = ? WHERE id = 'text'",
        (_NEW_NAME, _NEW_DESC),
    )
    await db.commit()
