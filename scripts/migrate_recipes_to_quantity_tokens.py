#!/usr/bin/env python3
"""Rewrite legacy free-text quantity prefixes in smart_markdown
diagrams into ADR-210 structured `=value` overrides.

Issue #211 — meal-plan → shopping-list workflow.

Pre-migration pattern (free text):
    - NNN {{element:UUID:attr:attributes/Unit/type}} {{element:UUID:name}}

Post-migration pattern (structured override on a Quantity attribute):
    - {{element:UUID:attr:attributes/Quantity/type=NNN}} {{element:UUID:attr:attributes/Unit/type}} {{element:UUID:name}}

Renders identically for humans (same string output via the smart_markdown
resolver). Now also machine-parseable by the v6.20.0 aggregation engine.

Usage:
    python3 scripts/migrate_recipes_to_quantity_tokens.py \\
        --db-url "<postgres-url>" \\
        --set-id "<uuid-of-the-recipe-set>" \\
        [--dry-run]

Idempotent — running twice is a no-op (the regex won't match the
already-rewritten form).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime


# Matches: `[whitespace]NNN [whitespace] {{element:UUID:attr:.../Unit/type}}`
# with at least one space between the number and the token.
# Captures (1) the leading whitespace, (2) the number, (3) the element id.
_LEGACY_PATTERN = re.compile(
    r"(^|\s)(\d+(?:\.\d+)?)"          # leading WS + numeric quantity
    r"\s+"                             # whitespace
    r"\{\{element:"                    # token start
    r"([0-9a-fA-F-]+)"                # element UUID
    r":attr:attributes/Unit/type\}\}", # the Unit attribute token
    re.MULTILINE,
)


def _rewrite(markdown: str) -> tuple[str, int]:
    """Return (new_markdown, n_rewrites)."""
    count = 0

    def repl(m: re.Match) -> str:
        nonlocal count
        count += 1
        leading_ws, qty, elem_id = m.group(1), m.group(2), m.group(3)
        # Strip trailing .0 from whole numbers.
        try:
            if float(qty) == int(float(qty)):
                qty = str(int(float(qty)))
        except ValueError:
            pass
        return (
            f"{leading_ws}"
            f"{{{{element:{elem_id}:attr:attributes/Quantity/type={qty}}}}} "
            f"{{{{element:{elem_id}:attr:attributes/Unit/type}}}}"
        )

    return _LEGACY_PATTERN.sub(repl, markdown), count


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db-url", required=True)
    ap.add_argument("--set-id", required=True)
    ap.add_argument(
        "--created-by", default=None,
        help="User UUID to attribute version-bumps to. Falls back to a "
        "creator already present in the target set.",
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
    total_rewrites = 0
    for row in rows:
        data = row["data"] if isinstance(row["data"], dict) else (
            json.loads(row["data"]) if row["data"] else {}
        )
        src = data.get("markdown_source") or ""
        new_src, count = _rewrite(src)
        if count == 0:
            continue
        changed += 1
        total_rewrites += count
        print(f"  {row['name']}: {count} rewrite(s)")
        if args.dry_run:
            continue
        data["markdown_source"] = new_src
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
                "Migrate free-text quantity to Quantity-attr override (issue #211)",
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
        print(
            f"\nDRY RUN: would rewrite {total_rewrites} occurrence(s) "
            f"across {changed} diagrams.",
        )
        conn.rollback()
    else:
        conn.commit()
        print(
            f"\nRewrote {total_rewrites} occurrence(s) across {changed} "
            "diagrams.",
        )

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
