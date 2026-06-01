#!/usr/bin/env python
"""Repair GEANZ diagram rendering on an existing set (ADR-230 F5).

Enriches every capability diagram in ONE explicitly-named set so it
renders faithfully to the Sparx EA ground-truth: rounded corners, dashed
theme pills + redirects, pill + italic theme pills, the zone behind its
children, and `metadata.theme_id = 'geanz-default'`. The per-node colours
(EA fill/border) are already present and are preserved untouched.

This is a TARGETED, IDEMPOTENT, DRY-RUN-FIRST data repair (per the
prod-data-repair-scoping discipline): it touches only the set you name on
the command line, prints exactly what it would change, and writes nothing
unless you pass --apply. The archetype/enrichment rule is imported from
app.import_sparx.geanz so it stays identical to the importer.

Examples:
  # dry-run against the local dev backend (default)
  uv run python scripts/repair_geanz_render.py \
      --set-id 7f2521de-d7c8-41ba-982c-d1246ba81428 \
      --username admin --password TestPassword12345

  # apply against UAT with an externally-minted PAT
  uv run python scripts/repair_geanz_render.py \
      --api-base https://iris-api-... --token "$IRIS_PAT" \
      --set-id 7f2521de-d7c8-41ba-982c-d1246ba81428 --apply
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import urllib.error
import urllib.request

sys.path.insert(0, "backend")
from app.import_sparx.geanz import apply_geanz_styling  # noqa: E402


def _req(method: str, url: str, token: str | None, body: dict | None = None,
         extra_headers: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{method} {url} -> {e.code} {e.read().decode()[:300]}") from e


def _login(api_base: str, username: str, password: str) -> str:
    out = _req("POST", f"{api_base}/api/auth/login", None,
               {"username": username, "password": password})
    return out["access_token"]


def main() -> int:
    ap = argparse.ArgumentParser(description="Repair GEANZ diagram rendering for one set.")
    ap.add_argument("--api-base", default="http://localhost:8000")
    ap.add_argument("--set-id", required=True, help="The ONLY set that will be touched.")
    ap.add_argument("--token", help="Bearer token / PAT (preferred for Supabase deployments).")
    ap.add_argument("--username")
    ap.add_argument("--password")
    ap.add_argument("--apply", action="store_true", help="Write changes (default: dry-run).")
    args = ap.parse_args()

    token = args.token
    if not token and args.username and args.password:
        token = _login(args.api_base, args.username, args.password)
    if not token:
        ap.error("provide --token, or --username and --password")

    # List all diagrams in the named set (paginated).
    diagrams: list[dict] = []
    page = 1
    while True:
        out = _req("GET", f"{args.api_base}/api/diagrams?set_id={args.set_id}&page={page}&page_size=100", token)
        items = out.get("items", out if isinstance(out, list) else [])
        diagrams.extend(items)
        if len(items) < 100:
            break
        page += 1

    print(f"Set {args.set_id}: {len(diagrams)} diagram(s). Mode: {'APPLY' if args.apply else 'DRY-RUN'}\n")
    changed = 0
    for d in diagrams:
        full = _req("GET", f"{args.api_base}/api/diagrams/{d['id']}", token)
        data = full.get("data") or {}
        nodes = data.get("nodes") or []
        before = copy.deepcopy(nodes)
        is_geanz = apply_geanz_styling(nodes)
        meta = dict(full.get("metadata") or {})
        theme_before = meta.get("theme_id")
        if is_geanz:
            meta["theme_id"] = "geanz-default"
        node_changed = nodes != before
        theme_changed = meta.get("theme_id") != theme_before
        if not is_geanz or (not node_changed and not theme_changed):
            print(f"  - {full.get('name','?')[:60]:60}  (no change)")
            continue
        changed += 1
        n_enriched = sum(1 for a, b in zip(nodes, before) if a != b)
        print(f"  ✓ {full.get('name','?')[:60]:60}  nodes_enriched={n_enriched}  theme_id={theme_before}->{meta['theme_id']}")
        if args.apply:
            _req("PUT", f"{args.api_base}/api/diagrams/{d['id']}", token, {
                "name": full["name"],
                "description": full.get("description") or "",
                "data": {**data, "nodes": nodes},
                "metadata": meta,
                "change_summary": "GEANZ render fidelity (ADR-230): enrich node visuals + geanz-default theme",
            }, extra_headers={"If-Match": str(full.get("current_version", 1))})

    print(f"\n{'Applied' if args.apply else 'Would change'} {changed} diagram(s).")
    if not args.apply and changed:
        print("Re-run with --apply to write these changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
