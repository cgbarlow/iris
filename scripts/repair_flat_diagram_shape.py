#!/usr/bin/env python3
"""Repair diagrams persisted with the flat AI/MCP node shape (issue #238).

Some diagrams created via the MCP `create_diagram` tool were stored with
the *flat* AI node shape (`{id, type, label, position, size, visual}`)
instead of the Svelte-Flow canvas shape the frontend requires
(`{id, type, position, width, height, data: {label, entityType, ...}}`).
With no per-node `data` object, `UnifiedCanvas.svelte` crashed reading
`n.data.entityType` and the diagram "failed to load".

ADR-218 fixes the cause (write- and read-time normalization in the
diagram service). This script repairs the *already-persisted* rows: it
rewrites every version of the EXPLICITLY-NAMED diagrams in place using
the same `normalize_canvas_data` authority, then regenerates their
thumbnails so list/preview surfaces reflect the corrected shape.

SAFETY: operates ONLY on the diagram ids passed via `--diagram-id`
(repeatable). It never scans or rewrites any other diagram. Idempotent:
a diagram already in canvas shape is left untouched. Use `--dry-run`
first to preview.

Works against both deployment modes (reads `IRIS_DB_BACKEND` and the
Supabase env vars via `app.config.get_config`).

Usage (local SQLite):
    cd backend && IRIS_DATA_DIR=./data \\
      .venv/bin/python ../scripts/repair_flat_diagram_shape.py \\
        --diagram-id <uuid> [--diagram-id <uuid> ...] [--dry-run]

Usage (Supabase/UAT — creds from .env):
    cd backend && set -a && source ../.env && set +a && \\
      IRIS_DB_BACKEND=supabase \\
      .venv/bin/python ../scripts/repair_flat_diagram_shape.py \\
        --diagram-id 13024153-b328-41a4-bd37-0cbc6d2fbedc \\
        --diagram-id 330fe369-0b03-457c-8692-62e67f9fcdb0 \\
        --diagram-id 6b9917d7-f7c9-4dfc-a769-49fa571f28e5
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

# Make the backend `app` package importable when run from the repo root.
_BACKEND = Path(__file__).resolve().parents[1] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.diagrams.canvas_normalize import (  # noqa: E402
    needs_normalization,
    normalize_canvas_data,
)


def _parse_data(raw: Any) -> dict:
    """Decode a diagram_versions.data cell (TEXT on SQLite, str on
    Supabase via the adapter) into a dict."""
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    return json.loads(raw)


async def repair_diagram(db: Any, diagram_id: str, *, dry_run: bool = False) -> dict:
    """Normalize every version of one diagram in place.

    Returns a summary dict. Does not commit — the caller commits once all
    diagrams are processed (so a dry-run touches nothing).
    """
    cursor = await db.execute(
        "SELECT diagram_type, current_version FROM diagrams "
        "WHERE id = ? AND is_deleted = 0",
        (diagram_id,),
    )
    head = await cursor.fetchone()
    if head is None:
        return {"id": diagram_id, "found": False}

    diagram_type = head[0]
    current_version = head[1]

    cursor = await db.execute(
        "SELECT version, data FROM diagram_versions WHERE diagram_id = ? "
        "ORDER BY version",
        (diagram_id,),
    )
    rows = await cursor.fetchall()

    versions_changed: list[int] = []
    current_data: dict = {}
    for row in rows:
        version = row[0]
        data = _parse_data(row[1])
        if version == current_version:
            current_data = data
        if not needs_normalization(data):
            continue
        normalized = normalize_canvas_data(data)
        if version == current_version:
            current_data = normalized
        versions_changed.append(version)
        if not dry_run:
            await db.execute(
                "UPDATE diagram_versions SET data = ? "
                "WHERE diagram_id = ? AND version = ?",
                (json.dumps(normalized), diagram_id, version),
            )

    return {
        "id": diagram_id,
        "found": True,
        "diagram_type": diagram_type,
        "current_version": current_version,
        "total_versions": len(rows),
        "versions_changed": versions_changed,
        "current_data": current_data,
    }


async def regenerate_thumbnails(
    db: Any, diagram_id: str, diagram_type: str, data: dict
) -> None:
    """Regenerate all-theme thumbnails for one diagram from its
    (already-normalized) current-version data."""
    from app.diagrams.thumbnail import (  # noqa: PLC0415
        VALID_THEMES,
        generate_and_store_thumbnail,
    )

    for theme in VALID_THEMES:
        await generate_and_store_thumbnail(db, diagram_id, data, diagram_type, theme=theme)


async def _run(diagram_ids: list[str], *, dry_run: bool, skip_thumbnails: bool) -> int:
    from app.config import get_config  # noqa: PLC0415
    from app.database import DatabaseManager  # noqa: PLC0415

    manager = DatabaseManager(get_config())
    await manager.connect()
    mode = "supabase" if manager.is_supabase else "sqlite"
    print(f"Connected ({mode}). Repairing {len(diagram_ids)} diagram(s). "
          f"dry_run={dry_run}")

    repaired = 0
    try:
        db = manager.main_db
        for diagram_id in diagram_ids:
            summary = await repair_diagram(db, diagram_id, dry_run=dry_run)
            if not summary["found"]:
                print(f"  ! {diagram_id}: NOT FOUND (skipped)")
                continue
            changed = summary["versions_changed"]
            if not changed:
                print(f"  = {diagram_id} ({summary['diagram_type']}): "
                      f"already canvas-shaped, no change")
                continue
            repaired += 1
            print(f"  + {diagram_id} ({summary['diagram_type']}): normalized "
                  f"version(s) {changed} of {summary['total_versions']}")
            if not dry_run and not skip_thumbnails:
                await regenerate_thumbnails(
                    db, diagram_id, summary["diagram_type"], summary["current_data"]
                )
                print(f"    └ thumbnails regenerated")
        if not dry_run:
            await db.commit()
    finally:
        await manager.close()

    if dry_run:
        print(f"\nDRY RUN: would repair {repaired} diagram(s). Nothing written.")
    else:
        print(f"\nDone. Repaired {repaired} diagram(s).")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--diagram-id",
        action="append",
        dest="diagram_ids",
        metavar="UUID",
        help="Diagram id to repair (repeatable). At least one required.",
    )
    ap.add_argument("--dry-run", action="store_true", help="Preview only; write nothing.")
    ap.add_argument(
        "--skip-thumbnails",
        action="store_true",
        help="Repair data only; do not regenerate thumbnails.",
    )
    args = ap.parse_args()

    if not args.diagram_ids:
        ap.error("at least one --diagram-id is required (this script never scans all diagrams)")

    return asyncio.run(
        _run(args.diagram_ids, dry_run=args.dry_run, skip_thumbnails=args.skip_thumbnails)
    )


if __name__ == "__main__":
    sys.exit(main())
