#!/usr/bin/env python3
"""Add a blank `Quantity` attribute to every element in a target set.

Issue #211 — meal-plan → shopping-list workflow.

The aggregation engine reads per-use values from smart-markdown
`=value` overrides (ADR-210). For the workflow to be authorable
fluently, the *element* needs a Quantity attribute slot the author
can override per-use. This script adds that slot (blank value,
scope=Public) idempotently to every element in a given set.

Usage:
    python3 scripts/backfill_quantity_attribute.py \\
        --db-url "<postgres-url>" \\
        --set-id "<uuid>" \\
        [--dry-run]

Idempotent — re-running is a no-op when every element already has the
attribute. Operator action; not in the startup migration runner
because the target set is environment-specific.
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import UTC, datetime


def _add_quantity_attribute(data: dict | None) -> tuple[dict, bool]:
    """Return (updated_data, did_change). Idempotent."""
    if not isinstance(data, dict):
        data = {}
    attributes = data.get("attributes") or []
    if not isinstance(attributes, list):
        attributes = []
    for attr in attributes:
        if isinstance(attr, dict) and attr.get("name") == "Quantity":
            return data, False
    attributes.append({
        "name": "Quantity",
        "type": "",
        "scope": "Public",
        "notes": "",
        "lower_bound": "",
        "upper_bound": "",
    })
    data["attributes"] = attributes
    return data, True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db-url", required=True)
    ap.add_argument("--set-id", required=True)
    ap.add_argument(
        "--created-by", default=None,
        help=(
            "User UUID to attribute the new element versions to. "
            "Required when element_versions.created_by is NOT NULL "
            "(Supabase). If omitted, the script tries to use the "
            "existing created_by value from elements in this set."
        ),
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

    # Resolve created_by to attribute version-bumps to. Falls back to a
    # creator already present in the target set if the operator didn't
    # supply one.
    created_by = args.created_by
    if created_by is None:
        cur.execute(
            "SELECT DISTINCT ev.created_by FROM element_versions ev "
            "JOIN elements e ON e.id = ev.element_id "
            "WHERE e.set_id = %s AND ev.created_by IS NOT NULL "
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
        "SELECT e.id, e.current_version, ev.name, ev.data, ev.metadata, "
        "ev.description "
        "FROM elements e "
        "JOIN element_versions ev "
        "  ON e.id = ev.element_id AND e.current_version = ev.version "
        "WHERE e.set_id = %s AND e.is_deleted = FALSE",
        (args.set_id,),
    )
    rows = cur.fetchall()
    print(f"Found {len(rows)} elements in set {args.set_id}.")

    changed = 0
    for row in rows:
        data = row["data"] if isinstance(row["data"], dict) else (
            json.loads(row["data"]) if row["data"] else {}
        )
        new_data, did_change = _add_quantity_attribute(data)
        if not did_change:
            continue
        changed += 1
        if args.dry_run:
            print(f"  would add Quantity to {row['name']} ({row['id']})")
            continue
        new_version = row["current_version"] + 1
        now = datetime.now(tz=UTC)
        version_id = str(uuid.uuid4())  # noqa: F841 — unused, FYI
        cur.execute(
            "INSERT INTO element_versions ("
            "  element_id, version, name, description, data, metadata, "
            "  change_type, change_summary, created_at, created_by"
            ") VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s)",
            (
                row["id"], new_version, row["name"], row["description"],
                json.dumps(new_data),
                json.dumps(row["metadata"]) if row["metadata"] else None,
                "update",
                "Backfill Quantity attribute (issue #211)",
                now,
                created_by,
            ),
        )
        cur.execute(
            "UPDATE elements SET current_version = %s, updated_at = %s "
            "WHERE id = %s",
            (new_version, now, row["id"]),
        )

    if args.dry_run:
        print(f"\nDRY RUN: would update {changed} of {len(rows)} elements.")
        conn.rollback()
    else:
        conn.commit()
        print(f"\nUpdated {changed} of {len(rows)} elements.")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
