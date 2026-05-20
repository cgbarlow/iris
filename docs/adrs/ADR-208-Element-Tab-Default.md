# ADR-208: Per-set `element_tab_default` preference + element screen Relationships restructure

Status: Accepted (2026-05-20)

Builds on: [ADR-204](./ADR-204-Per-Set-Tab-Defaults.md) (per-set tab defaults pattern).

## Context

Two interrelated requests on issue [#192](https://github.com/cgbarlow/iris/issues/192):

1. **Element screen tabs need rework.** Today the element detail page has: Details · Used in Diagrams · Relationships · Version History (in that order). Users land on Details by default. The user wants:
   - Relationships moved to **first** position (matching the v6.14.0 package screen reorder under ADR-204).
   - **Used in Diagrams folded into Relationships** as a section (DRY of the package-screen pattern that shows contained elements under its Relationships tab).
   - **Element → package memberships** surfaced under Relationships (the inverse of the package screen, which shows contained elements).
2. **A new `element_tab_default` per-set preference**, sibling to the `package_tab_default` and `view_tab_default` columns shipped by ADR-204. Default value: `relationships`.

Both changes leverage existing patterns — no new infrastructure.

## Decision

### Schema (Protocol §15 paired)

Add a new column `element_tab_default TEXT NOT NULL DEFAULT 'relationships'` to the `sets` table.

- **SQLite**: `backend/app/migrations/m072_sets_element_tab_default.py`. Idempotent `PRAGMA table_info` guard then `ALTER TABLE`.
- **Supabase**: `backend/app/migrations/supabase/m077_sets_element_tab_default.sql`. `ADD COLUMN IF NOT EXISTS` with the same default and NOT NULL.

Header on the Supabase file: `-- Mirrors SQLite m072.` Both halves are idempotent and re-runnable.

### Pydantic

```python
# backend/app/sets/models.py
ElementTabDefault = Literal["details", "diagrams", "relationships", "versions"]
```

Added to `SetUpdate` (optional) and `SetResponse` (required, default `"relationships"`). Wide enum so the column can carry a deprecated `"diagrams"` value if some set has it before the Used-in-Diagrams tab is removed; the element page falls back to `"relationships"` if the persisted value is no longer a valid tab.

### Service-layer plumbing

`_SET_COLUMNS` grows to 18 fields; `_row_to_dict` gains a defensive fallback; `update_set` gets a per-field UPDATE block matching the `package_tab_default` / `view_tab_default` blocks (so PATCH semantics are preserved per ADR-204's correctness fix in v6.14.2).

### Element screen restructure (UI only)

`frontend/src/routes/elements/[id]/+page.svelte`:

- Tab order becomes: **Relationships · Details · Version History**. The `diagrams` tab is removed — its content folds into Relationships.
- Inside the Relationships tab, three sections render in order:
  1. **Package membership** — fetched from new `GET /api/elements/{id}/package-memberships`. Empty list hides the section.
  2. **Used in Views** — the existing `usedInModels` data, re-titled "Used in Views" inside the picker scope per ADR-207's narrowed rename. (Outside the picker, the rest of Iris still says "diagrams" — that's a separate ticket.)
  3. **Relationships** — the existing relationships table.
- `activeTab` seeding mirrors `frontend/src/routes/views/[id]/+page.svelte:60-90`: when `entity.set_id` is present, fetch the set, read `element_tab_default`, and use it unless `userSelectedTab` is true.

### Set edit screen UI

`frontend/src/routes/sets/[id]/+page.svelte` gains an `Element tab default` dropdown beneath the existing `View tab default` dropdown. Options: `Relationships` (default), `Details`, `Version History`. (The `diagrams` value is accepted by the model for forward compat but not offered in the UI — there is no top-level `diagrams` tab anymore.)

### New endpoint

`GET /api/elements/{id}/package-memberships` returns the package(s) this element belongs to. Reads `elements.package_id` (ADR-184) — no new schema. 404 on missing element. Anonymous-readable (matches sibling endpoints under `/api/elements/{id}/...`).

## Why this row in `sets` rather than per-user preference

Same rationale as ADR-204: tab default is a property of the *content shape* of a set (a Groceries set may benefit from defaulting to Relationships; a Documentation set may not), not a personal user preference. One value, scoped to the set, shared by all users viewing it.

## Why merge `Used in Diagrams` into `Relationships`

Per the user: "used in diagrams is a sub-set of 'relationships'". This is true — an element being referenced from a view is a relationship between the element and the view, expressible as a kind of edge. Surfacing them as separate tabs duplicates navigation for the same conceptual data.

## Why default `relationships`

Per user: "Default is 'relationships'." The package screen already defaults to Relationships (ADR-204). The element screen aligning with that is consistent and matches the user's stated preference.

## Surface parity (§14)

New endpoint is a GET. No write surface, no MCP/CLI parity required.

## Consequences

- `backend/app/migrations/m072_sets_element_tab_default.py` (new SQLite).
- `backend/app/migrations/supabase/m077_sets_element_tab_default.sql` (new Supabase mirror).
- `backend/app/startup.py` — register m072.
- `backend/app/sets/models.py` — `ElementTabDefault` Literal + fields.
- `backend/app/sets/service.py` — `_SET_COLUMNS`, `_row_to_dict`, `update_set`.
- `backend/app/elements/router.py` — `/{id}/package-memberships`.
- `frontend/src/routes/elements/[id]/+page.svelte` — tab order, merged Relationships content, activeTab seeding.
- `frontend/src/routes/sets/[id]/+page.svelte` — `elementTabDefault` dropdown + PUT body.

Tests: schema test for m072; `SetUpdate`/`SetResponse` round-trip; package-memberships endpoint coverage.

CHANGELOG `[6.16.0]` Added + Migration sections.

## Release ordering

Per memory and Protocol §15: schema-dependent code must not go live before its column exists.

1. Merge PR (code + paired migration).
2. Render auto-deploys; the `/api/elements/{id}/package-memberships` endpoint will 200 immediately (no schema dependency).
3. `PUT /api/sets/{id}` with `element_tab_default` in the body will 409 until the user runs `scripts/supabase-migrate.sh` (m077 not yet applied).
4. User runs supabase-migrate.sh → 200.

## Verification

Documented in SPEC-208-A.

## See also

- Issue [#192](https://github.com/cgbarlow/iris/issues/192).
- [ADR-204](./ADR-204-Per-Set-Tab-Defaults.md) (sibling pattern for package/view tab defaults).
- [ADR-184](./ADR-184-Element-Package-Membership.md) (existing `elements.package_id`).
- §13 DRY, §14 Surface parity, §15 Migration parity: `docs/protocols.md`.
