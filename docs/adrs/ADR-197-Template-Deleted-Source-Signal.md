# ADR-197: Template viewer uses `source_element_name` as the source-existence signal

Status: Accepted (2026-05-18)
Extends: [ADR-191](ADR-191-Element-Templates.md)

## Context

Issue [#173](https://github.com/cgbarlow/iris/issues/173) item 2 —
on the element template viewer, when the source element no longer
exists, the page should show "(source element deleted)" instead of
a broken link. The page *had* such a fallback, but it never fired:
the user kept seeing a clickable link whose label was a UUID,
which 404'd on click.

### Two-half root cause

**Backend (half 1).** The `source_element_id` column on
`element_templates` has no `ON DELETE` clause (m067 SQLite / m071
Supabase). When an element is soft-deleted (`is_deleted = TRUE`),
the FK stays pointing at the now-hidden row. The template row
itself is unaffected.

**Backend (half 2).** `get_element_template` (and
`list_element_templates`) computed `source_element_name` via a
subquery that joined `element_versions` and `elements` on `id`
and `current_version` — but did **not** filter on
`elements.is_deleted = 0`. A soft-deleted source still produced a
name, so the response said "your source is alive and called
'X'" even though the source page returned 404.

**Frontend.** The template viewer's `{#if}` was keyed on
`tpl.source_element_id`. That id was always truthy (dangling FK),
so the `{:else}` branch ("source element deleted") was unreachable.
The label rendered `tpl.source_element_name ?? tpl.source_element_id`
— so when source was alive, you saw the name; when source was
soft-deleted, you saw the raw UUID label inside a broken link.

## Decision

Two coordinated changes:

1. **Backend.** Add `AND e.is_deleted = 0` to the subquery in both
   `get_element_template` and `list_element_templates`. The
   db-adapter regex rewrites `is_xxx = 0` to `is_xxx = FALSE` on
   Supabase (Protocol §15), so the SQLite literal works on both
   backends.
2. **Frontend.** Change the conditional from `{#if tpl.source_element_id}`
   to `{#if tpl.source_element_name}`. Drop the `??
   tpl.source_element_id` label fallback — when name is present
   we have a real label; when it isn't, we render the deleted
   placeholder.

The dangling FK itself is left alone. Templates that capture
fields from a now-deleted element are still meaningful documents
(they hold the captured `template_data` snapshot), so we don't
cascade-delete templates when their source element is removed.
The id is preserved for forensic / audit value.

## Why not nullify `source_element_id` on source deletion

Considered. Rejected because the id is the only audit trail that
ties a template back to its origin — useful when a source has
been deleted-by-accident and an admin needs to restore it (the
existing `deleted_group_id` machinery in `elements` lets a soft-
delete be reversed; the template still wants to remember which
group it came from). Surfacing the deleted state at read time
costs nothing; mutating historical data does.

## Why not ON DELETE CASCADE the template

Same reason — templates are independent artefacts after capture.
Cascading would destroy a user's work whenever they tidy up the
element catalogue.

## Consequences

- `backend/app/element_templates/service.py:159-162,234-237` —
  subquery in both reads filters `AND e.is_deleted = 0`.
- `backend/tests/test_element_templates/test_deleted_source.py` —
  new pytest module, 3 cases (GET nulls name, LIST nulls name,
  sanity that alive source still produces a name).
- `frontend/src/routes/element-templates/[id]/+page.svelte:186-193`
  — conditional uses `source_element_name`, label uses the name
  directly (no id fallback).
- `frontend/tests/unit/templateDeletedSource.test.ts` — new
  static-parser test (5 assertions).
- No migration, no MCP / CLI changes.
- CHANGELOG `[6.8.6]`.

## Verification

```
.venv/bin/python -m pytest backend/tests/test_element_templates/
npx vitest run tests/unit/templateDeletedSource.test.ts
```

Both green. Manual smoke: create a template from an element,
delete the source element, navigate to the template page,
confirm the "Source element" row reads "(source element
deleted)" and is not a link.

## See also

- [ADR-191](ADR-191-Element-Templates.md) — original template
  decision.
- Issue [#173](https://github.com/cgbarlow/iris/issues/173) item 2.
