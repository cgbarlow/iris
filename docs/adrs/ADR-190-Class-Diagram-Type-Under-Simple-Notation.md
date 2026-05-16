# ADR-190: Allow `class` diagram type under `simple` notation

Status: Accepted (2026-05-16)
Extends: ADR-079 (diagram_type ↔ notation registry; seeded in m020)

## Context

Issue [#160](https://github.com/cgbarlow/iris/issues/160) — "diagram
type 'class' beneath simple notation is not available on drop down
when creating a new element." The user provided a UAT element as
evidence:
`https://iris-uat.chrisbarlow.nz/elements/09158b60-94cd-46db-9211-a4d50c9c1550`.

Investigation against the live iris-api (`GET
/api/elements/09158b60-…`) returned:

```json
{
  "id": "09158b60-94cd-46db-9211-a4d50c9c1550",
  "name": "Arrival",
  "element_type": "class",
  "notation": "simple",
  "set_id": "c7da64c9-…",
  "set_name": "FIXM US Extension v4.1.1",
  …
}
```

That is: production data already has elements with
`notation='simple'` and `element_type='class'`, but the registry
seeded in m020 only declared `('class', 'uml', 1)`. The new-element
dropdown — driven by the `diagram_type_notations` join via
`/api/registry/diagram-types` — therefore hides `class` whenever the
user picks Simple, even though the codebase serves those elements
back. The hard-coded frontend fallback in `DiagramDialog.svelte`
agreed with the registry, so the gap was symmetric.

The data is the source of truth. The registry was out of step.

## Decision

Register the missing pair in the `diagram_type_notations` table with
`is_default=0` (the Simple notation's default diagram type stays
`component`):

- SQLite: new migration
  `backend/app/migrations/m066_class_for_simple_notation.py` —
  `INSERT OR IGNORE INTO diagram_type_notations (diagram_type_id,
  notation_id, is_default) VALUES ('class', 'simple', 0)`.
- Supabase: paired mirror
  `backend/app/migrations/supabase/m070_class_for_simple_notation.sql`
  — same insert with `FALSE` (boolean literal per Protocol §15) and
  `ON CONFLICT … DO NOTHING`.

Update the frontend hard-coded fallback list in
`frontend/src/lib/components/DiagramDialog.svelte:54-65` to include
`{ value: 'class', label: 'Class' }` so the offline/registry-fetch-
failed path matches the registry.

## Why not the opposite (rewrite element_type='class' → some other type)

That would require migrating live data based on a registry decision
made *after* the data was created. The registry hadn't been intended
as a strict constraint — it was a UI helper — so the data is not
malformed; it's the UI surface that was incomplete. Adding the pair
is the cheaper, lossless fix.

## Why is_default=0

Simple notation's default diagram type is `component` (m020,
`is_default=1`). Class is a less common choice for simple-notation
elements (the FIXM data is an outlier rather than a typical pattern),
so making it the default would change the new-element flow for
existing users. is_default=0 surfaces class in the dropdown without
promoting it.

## Consequences

- `backend/app/migrations/m066_class_for_simple_notation.py` — new
  idempotent SQLite migration.
- `backend/app/migrations/supabase/m070_class_for_simple_notation.sql`
  — paired Supabase mirror.
- `backend/app/startup.py` — m066 wired into the SQLite migration
  runner; Supabase mirror runs via `scripts/supabase-migrate.sh`.
- `frontend/src/lib/components/DiagramDialog.svelte` — fallback
  SIMPLE list gains `class`.
- `backend/tests/test_migrations/test_class_for_simple_notation_schema.py`
  — 7-test schema test covering both halves: SQL shape, idempotency
  markers, boolean-literal convention on Supabase, pairing header
  comment.
- CHANGELOG `[6.7.4]`.

## Verification

- `pytest backend/tests/test_migrations/test_class_for_simple_notation_schema.py`
  — 7 green.
- Browser smoke (dev.sh smoke step): open the new-element dialog,
  pick Simple notation, confirm **Class** appears in the diagram-type
  dropdown.
- Supabase migrate: run `scripts/supabase-migrate.sh` against the
  target DB before the v6.7.4 code deploy.

## See also

- ADR-079 — the original registry decision (m020 seed).
- Protocol §15 — paired SQLite/Supabase migrations, boolean-literal
  convention.
- Issue [#160](https://github.com/cgbarlow/iris/issues/160).
