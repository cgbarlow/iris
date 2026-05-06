"""Migration 046: Track extension source method, source URL, and the
latest known release.

v5.5.0 (issue #48): extensions previously had only `version`. The
extension manager now tracks WHERE each extension comes from and the
latest available release so the UI can show an "update available"
indicator and the daily scanner workflow can compare against the
canonical manifest.

Columns added to `extensions`:
  - source_method TEXT NOT NULL DEFAULT 'local'
      'local'  — bundled / no remote source.
      'github' — clone-from-github (mnemos, future plugins).
      'npm'    — npm dependency pinned in package.json (scenia today).
  - source_url TEXT
      The canonical URL the extension was pulled from. NULL for local.
  - latest_version TEXT
      The latest release tag known to Iris (set by the daily scanner
      / the new POST /api/extensions/{id}/check-update endpoint).
  - latest_version_checked_at TEXT
      ISO timestamp of the most recent check.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite

MIGRATION_ID = "m046_extensions_source"


async def up(db: aiosqlite.Connection) -> None:
    """Run migration up — additive ALTER COLUMNs, idempotent."""
    cursor = await db.execute("PRAGMA table_info(extensions)")
    columns = {row[1] for row in await cursor.fetchall()}

    if "source_method" not in columns:
        await db.execute(
            "ALTER TABLE extensions ADD COLUMN source_method TEXT NOT NULL DEFAULT 'local'"
        )
    if "source_url" not in columns:
        await db.execute("ALTER TABLE extensions ADD COLUMN source_url TEXT")
    if "latest_version" not in columns:
        await db.execute("ALTER TABLE extensions ADD COLUMN latest_version TEXT")
    if "latest_version_checked_at" not in columns:
        await db.execute(
            "ALTER TABLE extensions ADD COLUMN latest_version_checked_at TEXT"
        )

    await db.commit()
