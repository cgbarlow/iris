# ADR-204: Per-set tab defaults

Status: Accepted (2026-05-18)

## Context

Two screens render set-scoped content in tabs:

- `/packages/{id}` — currently opens to **Details**; tab order is
  Details → Relationships → Version History.
- `/views/{id}` — currently opens to **Canvas**; tab order is
  Canvas → Details → Relationships → Version History.

User feedback (issue #186): the most useful tab for a given set is
not always the same as the hard-coded default. A catalogue set may
benefit from landing users on Relationships first; an editorial set
on Canvas; a reference set on Details. The defaults were a global
choice baked into the page components — no way to opt out.

Tab order itself is also off: in the Packages screen, Relationships
deserves prime position for relationship-heavy sets; in the Views
screen, Details was sandwiched between Canvas and Relationships,
making relationship browsing two clicks away.

## Decision

Add two columns to the `sets` table that each set owns:

- `package_tab_default TEXT NOT NULL DEFAULT 'relationships'`
- `view_tab_default TEXT NOT NULL DEFAULT 'canvas'`

Each column drives which tab is active on first render of the
corresponding screen. Reorder the DOM so the new defaults sit first
in their respective screens, with the secondary tabs flowing in a
predictable left-to-right order.

This is a direct mirror of the per-set hierarchy-sort preference
pattern in [ADR-202](./ADR-202-Per-Set-Hierarchy-Sort-Preference.md)
— same column shape, same Pydantic-Literal enforcement, same
SQLite↔Supabase migration parity, same MCP/CLI passthrough.

### Enum values

| Column | Values | Default |
|---|---|---|
| `package_tab_default` | `'relationships'`, `'details'` | `'relationships'` |
| `view_tab_default` | `'canvas'`, `'relationships'`, `'details'` | `'canvas'` |

Enforced at the Pydantic layer (`PackageTabDefault`, `ViewTabDefault`
`Literal`s), not via SQL CHECK constraints — keeps SQLite ↔ Supabase
migration syntax identical (Protocol §15).

### Tab order changes (DOM, not just default)

| Screen | Old order | New order |
|---|---|---|
| Packages | Details → Relationships → Versions | **Relationships → Details → Versions** |
| Views | Canvas → Details → Relationships → Versions | **Canvas → Relationships → Details → Versions** |

The DOM reorder is intentional — even with the per-set override, the
*natural* left-to-right scan should align with the typical use of
the screen.

### Migration (paired §15)

- SQLite: `m069_sets_default_tabs.py` — PRAGMA-based idempotency,
  separate `ALTER TABLE sets ADD COLUMN` per column.
- Supabase: `m073_sets_default_tabs.sql` — `ADD COLUMN IF NOT EXISTS …`
  per column. Header references the SQLite mirror.

Defaults on the columns mean existing rows automatically inherit the
new defaults. No back-fill required.

### API surface

- `SetUpdate.package_tab_default: PackageTabDefault | None = None`
- `SetUpdate.view_tab_default: ViewTabDefault | None = None`
  (`None` = leave alone, per the partial-update convention.)
- `SetResponse.package_tab_default: PackageTabDefault = "relationships"`
- `SetResponse.view_tab_default: ViewTabDefault = "canvas"`
  (Always returned.)
- No new endpoint; the existing `PUT /api/sets/{id}` carries both.

### MCP

`_SET_UPDATE_FIELDS` adds `package_tab_default` and
`view_tab_default`. The `update_set` tool's input schema documents
both. The GET-then-merge helper (`_put_merge_partial`) preserves
whichever value isn't being changed.

### CLI

`iris update set` already proxies all body fields through the JSON
helper — the two new fields ride through with no flag work. Surface
parity is preserved.

### Frontend

- `/sets/{id}` edit page gets two `<select>` controls immediately
  below the hierarchy_sort selector, mirroring the same layout +
  help-text pattern.
- `/packages/{id}` initialiser seeds the active tab from
  `set.package_tab_default`; DOM reordered to place Relationships
  first.
- `/views/{id}` initialiser seeds the active tab from
  `set.view_tab_default`; DOM reordered to move Details to between
  Relationships and Versions.

## Why per-set rather than global or per-user

Identical reasoning to ADR-202: per-set is the right grain. Different
sets serve different purposes, and the choice is owned by the set
owner once rather than re-asked at view time.

## Why mirror the existing column-per-preference pattern rather than a JSON blob

The same trade-off ADR-202 made: explicit columns are typed at the
DB and Pydantic layers, easier to validate and query, and have
predictable migration behaviour across SQLite + Supabase. A JSON blob
would consolidate but lose every one of those properties.

## Why no per-user override

Out of scope. Issue #186 asks for a per-set setting; per-user adds a
preferences table and reconciliation burden when multiple users
browse the same set. Future ADR if a use case emerges.

## Release ordering (Supabase)

Standing memory ("Render+Supabase release ordering") applies:

1. Merge PR (migration + code).
2. Run `scripts/supabase-migrate.sh` against the Supabase DB.
3. Render auto-deploys on the merge.

The service layer reads the new columns via the existing
`_row_to_dict` positional fallback (defaults to `'relationships'` /
`'canvas'` when the column is absent), so a brief deploy-before-
migrate window is degraded but never 500.

## Consequences

- `backend/app/migrations/m069_sets_default_tabs.py` — new SQLite migration.
- `backend/app/migrations/supabase/m073_sets_default_tabs.sql` — Supabase mirror.
- `backend/tests/test_migrations/test_sets_default_tabs_schema.py` — schema tests.
- `backend/app/startup.py` — m069 registered.
- `backend/app/sets/models.py` — `PackageTabDefault`, `ViewTabDefault`, fields on `SetUpdate` + `SetResponse`.
- `backend/app/sets/service.py` — `_SET_COLUMNS`, `_row_to_dict`, create_set, update_set extended.
- `backend/app/sets/router.py` — pass body fields through.
- `backend/tests/test_sets/test_default_tabs.py` — round-trip tests.
- `mcp/src/iris_mcp/tools.py` — `_SET_UPDATE_FIELDS` extended.
- `frontend/src/lib/types/api.ts` — types exported, `IrisSet` fields.
- `frontend/src/routes/sets/[id]/+page.svelte` — two new `<select>`s.
- `frontend/src/routes/packages/[id]/+page.svelte` — initialiser + DOM reorder.
- `frontend/src/routes/views/[id]/+page.svelte` — initialiser + DOM reorder.
- CHANGELOG `[6.14.0]`.

## Verification

```
.venv/bin/python -m pytest \
  backend/tests/test_migrations/test_sets_default_tabs_schema.py \
  backend/tests/test_sets/test_default_tabs.py
.venv/bin/python scripts/check_surface_parity.py
```

Manual smoke: open `/sets/{id}`, change Package tab default to
`Details`, Save, visit a `/packages/{x}` whose package belongs to
the set, confirm Details opens. Repeat for View tab default.

## See also

- Issue [#186](https://github.com/cgbarlow/iris/issues/186).
- Pattern source: [ADR-202](./ADR-202-Per-Set-Hierarchy-Sort-Preference.md).
- §15 Migration parity: `docs/protocols.md`.
