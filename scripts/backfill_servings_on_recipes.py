#!/usr/bin/env python3
"""Set `data.servings` on smart_markdown diagrams in a target set.

Issue #211 — meal-plan → shopping-list workflow.

The Shopping list aggregation profile reads `data.servings` as the
divisor for the diner-count multiplier. This script sets the field on
every smart_markdown diagram in the target set, defaulting to a
uniform value passed via --servings (operator picks the value; the
seeded default is 4).

Idempotent — running twice is a no-op when `data.servings` is already
set to the target value.

Usage:
    python3 scripts/backfill_servings_on_recipes.py \\
        --db-url "<postgres-url>" \\
        --set-id "<uuid>" \\
        --servings 4 \\
        [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db-url", required=True)
    ap.add_argument("--set-id", required=True)
    ap.add_argument("--servings", type=int, default=4)
    ap.add_argument(
        "--created-by", default=None,
        help="User UUID to attribute version-bumps to.",
    )
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    try:
        import psycopg2
        import psycopg2.extras
    except ImportError:
        print(
            "psycopg2 not installed. `pip install psycopg2-binary` first.",
            file=sys.stderr,
        )
        return 2

    conn = psycopg2.connect(args.db_url)
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    created_by = args.created_by
    if created_by is None:
        cur.execute(
            "SELECT DISTINCT dv.created_by FROM diagram_versions dv "
            "JOIN diagrams d ON d.id = dv.diagram_id "
            "WHERE d.set_id = %s AND dv.created_by IS NOT NULL "
            "LIMIT 1",
            (args.set_id,),
        )
        row = cur.fetchone()
        if row:
            created_by = row["created_by"]
    if created_by is None:
        print(
            "Could not determine created_by; pass --created-by <uuid>.",
            file=sys.stderr,
        )
        return 2

    cur.execute(
        "SELECT d.id, d.current_version, dv.name, dv.description, "
        "dv.data, dv.metadata "
        "FROM diagrams d "
        "JOIN diagram_versions dv "
        "  ON d.id = dv.diagram_id AND d.current_version = dv.version "
        "WHERE d.set_id = %s AND d.is_deleted = FALSE "
        "AND d.diagram_type = 'smart_markdown'",
        (args.set_id,),
    )
    rows = cur.fetchall()
    print(f"Found {len(rows)} smart_markdown diagrams in set {args.set_id}.")

    changed = 0
    for row in rows:
        data = row["data"] if isinstance(row["data"], dict) else (
            json.loads(row["data"]) if row["data"] else {}
        )
        if data.get("servings") == args.servings:
            continue
        changed += 1
        data["servings"] = args.servings
        if args.dry_run:
            print(f"  would set servings={args.servings} on {row['name']}")
            continue
        new_version = row["current_version"] + 1
        now = datetime.now(tz=UTC)
        cur.execute(
            "INSERT INTO diagram_versions ("
            "  diagram_id, version, name, description, data, metadata, "
            "  change_type, change_summary, created_at, created_by"
            ") VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s)",
            (
                row["id"], new_version, row["name"], row["description"],
                json.dumps(data),
                json.dumps(row["metadata"]) if row["metadata"] else None,
                "update",
                f"Backfill data.servings={args.servings} (issue #211)",
                now,
                created_by,
            ),
        )
        cur.execute(
            "UPDATE diagrams SET current_version = %s, updated_at = %s "
            "WHERE id = %s",
            (new_version, now, row["id"]),
        )

    if args.dry_run:
        print(f"\nDRY RUN: would update {changed} of {len(rows)} diagrams.")
        conn.rollback()
    else:
        conn.commit()
        print(f"\nUpdated {changed} of {len(rows)} diagrams.")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
