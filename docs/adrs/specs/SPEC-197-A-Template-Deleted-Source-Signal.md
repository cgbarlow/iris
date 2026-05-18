# SPEC-197-A: Template deleted-source signal

Implements: [ADR-197](../ADR-197-Template-Deleted-Source-Signal.md)
Resolves: Issue [#173](https://github.com/cgbarlow/iris/issues/173) item 2
Status: Living

## Backend invariant

After this change, `GET /api/element-templates/{id}` and
`GET /api/element-templates` both return:

| Source element state | `source_element_id` | `source_element_name` |
|---|---|---|
| Alive | the id | the current name |
| Soft-deleted | the id (dangling FK) | **`null`** |
| Never existed | impossible (FK enforced at create time per `_load_source_element`) | n/a |

`source_element_name = null` is the canonical "source is gone"
signal for the frontend.

## SQL shape

Both `get_element_template` (single) and `list_element_templates`
(paginated) compute the name via:

```sql
(SELECT ev.name FROM element_versions ev
   JOIN elements e ON e.id = ev.element_id
  WHERE e.id = t.source_element_id
    AND e.current_version = ev.version
    AND e.is_deleted = 0) AS source_name
```

Protocol §15 note: the `e.is_deleted = 0` literal is rewritten by
`backend/app/db/adapter.py` to `e.is_deleted = FALSE` for Supabase
(regex match on `is_xxx = 0` / `is_xxx = 1`). Boolean column;
PostgreSQL safe.

## Frontend shape

`frontend/src/routes/element-templates/[id]/+page.svelte`:

```svelte
{#if tpl.source_element_name}
  <a href="/elements/{tpl.source_element_id}" style="color: var(--color-primary)">
    {tpl.source_element_name}
  </a>
{:else}
  <span style="color: var(--color-muted)">(source element deleted)</span>
{/if}
```

The href continues to point at `source_element_id` for navigation
(only reached when the source is alive). The label uses the name
directly; the previous `?? tpl.source_element_id` fallback is
removed.

## Acceptance criteria

1. Backend GET on a template whose source has been soft-deleted
   returns `source_element_name: null` (and the id unchanged).
2. Backend LIST returns the same nullability for any item in the
   page.
3. Frontend renders "(source element deleted)" copy with no
   anchor when the source is gone.
4. Frontend renders the element's current name as a working link
   when the source is alive.
5. No template behaviour beyond the source-name display changes —
   `template_data`, `included_fields`, `set_id`, `is_global` etc.
   are untouched.

## Tests

Backend — `backend/tests/test_element_templates/test_deleted_source.py`:

1. `test_source_element_name_is_null_after_source_deletion` —
   create source, create template, soft-delete source, GET
   template, assert `source_element_name is None` and id
   unchanged.
2. `test_list_endpoint_also_nulls_source_element_name` — same
   precondition, list templates in the set, assert the lone item
   has `source_element_name: None`.
3. `test_source_element_name_present_when_source_visible` —
   sanity: alive source still produces "Source" as the name.

Frontend — `frontend/tests/unit/templateDeletedSource.test.ts`:

1-5. `{#if}` uses `source_element_name`; no `{#if tpl.source_element_id}`;
   anchor href still `source_element_id`; "(source element deleted)"
   copy present; no `?? tpl.source_element_id` label fallback.

## Verification

```
.venv/bin/python -m pytest backend/tests/test_element_templates/test_deleted_source.py backend/tests/test_element_templates/test_crud_and_apply.py
cd frontend && npx vitest run tests/unit/templateDeletedSource.test.ts
```

Both green. Manual smoke per ADR-197 verification section.
