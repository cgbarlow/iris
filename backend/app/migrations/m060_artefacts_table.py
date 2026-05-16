"""Migration 060: artefacts table (ADR-179, SPEC-179-A, v6.2.0).

Issue #133 Phase 2. Generic artefact store for rendered markdown /
docx / pdf documents produced by the cascade destination chooser's
"Chat with downloadable artefacts" branch and by the new
`POST /api/export/diagram/{id}` endpoint.

Sibling to (not graft onto) `images` — the image store has tight
PNG/JPEG/GIF/WebP magic-byte validation; artefacts have their own
mime allowlist (text/markdown, docx, pdf) and a higher per-row cap
(25 MB). Sibling modules keep each contract honest.

source_kind identifies the origin so downstream tooling can filter:
  'render_markdown' — ad-hoc render of cascade content, source_ref NULL
  'export_diagram'  — diagram export, source_ref = diagram_id
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m060_artefacts_table"


_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS artefacts (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    mime TEXT NOT NULL,
    bytes BLOB NOT NULL,
    size_bytes INTEGER NOT NULL,
    source_kind TEXT NOT NULL,
    source_ref TEXT,
    created_by TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
)
"""

_CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_artefacts_source_ref
ON artefacts(source_ref)
"""


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up."""
    await db.execute(_CREATE_TABLE)
    await db.execute(_CREATE_INDEX)
    await db.commit()
