# ADR-191: Element Templates

Status: Accepted (2026-05-17)
Extends: [ADR-184](ADR-184-Element-Package-Membership.md) (element→package membership), [ADR-182](ADR-182-Surface-Parity-Discipline.md) (surface parity)
Implements: Issue [#153](https://github.com/cgbarlow/iris/issues/153)
Spec: [SPEC-191-A](specs/SPEC-191-A-Element-Templates.md)

## Context

Issue [#153](https://github.com/cgbarlow/iris/issues/153) — "Feature:
element templates." Users repeatedly create elements that follow the
same shape (FIXM Arrival/Departure pairs, DoView outcome boxes,
ArchiMate stakeholder profiles…). Each one is a manual recreation
of the same attributes, metadata, and notation. The user asked for:

1. A "create template" action on the element screen that captures a
   user-chosen subset of fields from an existing element.
2. A "templates" button on the elements list that opens a browser.
3. From the template browser, a "use this template" affordance that
   creates a new element with the captured fields pre-filled.
4. An optional "use template" dropdown on the regular new-element
   flow.
5. Coverage on REST, MCP, and CLI surfaces (Protocol §14 / ADR-182).

Plan-time clarifications (recorded in `docs/plans/humming-marinating-dusk.md`):

- **Scope** — set-scoped by default with an optional `is_global` flag.
  Most templates belong to a workspace; some (FIXM, DoView base
  shapes) should be reusable across sets.
- **Lifecycle** — full CRUD: editable + deletable. No versioning.
- **Field whitelist** — the user picks which of `name`, `description`,
  `element_type`, `notation`, `data`, `metadata`, `package_id`, `tags`
  are captured. Anything else is dropped at write time.
- **Surface coverage** — REST + MCP + CLI all gain the five
  CRUD endpoints plus a `template_id` parameter on `create_element`.

## Decision

### Data model

New table `element_templates` (migration m067 SQLite, m071 Supabase):

```sql
CREATE TABLE element_templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    set_id TEXT REFERENCES sets(id),
    is_global INTEGER NOT NULL DEFAULT 0,     -- BOOLEAN on Postgres (Protocol §15)
    source_element_id TEXT REFERENCES elements(id),
    included_fields TEXT NOT NULL,            -- JSON array
    template_data TEXT NOT NULL,              -- JSON snapshot
    created_by TEXT REFERENCES users(id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_deleted INTEGER NOT NULL DEFAULT 0,
    CHECK (
        (is_global = 1 AND set_id IS NULL) OR
        (is_global = 0 AND set_id IS NOT NULL)
    )
)
```

Two partial indexes (`idx_element_templates_set` on `set_id WHERE
is_deleted=0`, `idx_element_templates_global` on `is_global WHERE
is_global=1 AND is_deleted=0`). The CHECK constraint guarantees
exactly one of "scoped to a set" or "global" is true at any time.

### Field whitelist

```python
INCLUDED_FIELD_WHITELIST = frozenset({
    "name", "description", "element_type", "notation",
    "data", "metadata", "package_id", "tags",
})
```

Enforced at create time in `element_templates/service.py`. Anything
outside this list is silently dropped from `included_fields` / not
captured into `template_data`. Prevents callers from smuggling
arbitrary keys (e.g. `is_deleted`, `created_by`) into the snapshot.

### Surface coverage

| Surface | Tools / endpoints |
|---|---|
| REST | `POST /api/element-templates`, `GET /api/element-templates`, `GET /api/element-templates/{id}`, `PUT /api/element-templates/{id}`, `DELETE /api/element-templates/{id}` |
| REST (existing) | `POST /api/elements` gains optional `template_id` param |
| MCP | `create_element_template`, `list_element_templates`, `get_element_template`, `update_element_template`, `delete_element_template` |
| MCP (existing) | `create_element` gains optional `template_id` |
| CLI | `iris create element-template …`, `iris list element-template …`, `iris get element-template …`, `iris update element-template …`, `iris delete element-template …` |
| CLI (existing) | `iris create element … --template-id` |

`scripts/check_surface_parity.py` learns the new entity:

- `_KNOWN_ENTITIES` adds `"element_template"`.
- CLI parser accepts kebab-case (`"element-template"`) and normalises
  to underscore for the cross-surface comparison.

Delete is exempted from MCP/CLI parity under the existing "deferred
delete needs ADR (audit, undo)" exception. The script lists
`delete_element_template` alongside the other delete asymmetries.

### `template_id` on `create_element`

When `template_id` is supplied, `apply_template_to_create_body` reads
the named template and merges its `template_data` into the request
body field-by-field for every key in `included_fields ∩ INCLUDED_FIELD_WHITELIST`.
Explicit request fields always win — the template fills only what the
caller didn't provide. After merge, required fields (`element_type`,
`name`) are re-validated; if neither the request nor the template
supplies them, the API returns 422.

### Frontend UX

Three new surfaces in the Svelte app:

1. **Elements list** (`/elements`): a new **Templates** button next
   to **New Element**. Opens `TemplatesListDialog.svelte`, which
   lists set-scoped + global templates and provides a per-row "Use"
   button. On Use, the dialog asks for the new element's name, then
   POSTs to `/api/elements` with `{ template_id, name, set_id }`.
2. **Element detail** (`/elements/[id]`): a new **Save as template**
   button next to Clone/Delete. Opens
   `CreateTemplateDialog.svelte` with name, description, eight field
   checkboxes (matching the backend whitelist), and a
   "Make global" toggle. Posts to `/api/element-templates`.
3. **Template detail** (`/element-templates/[id]`): renders scope
   badge, source element link, captured fields table (`field` →
   pretty-printed `template_data[field]`), "Create element from
   template" form, and Delete affordance.

The new-element dialog (`EntityDialog.svelte`) is intentionally
**not** modified for v1 — adding a template dropdown there would
require pre-filling its internal state across five notations and
their per-diagram-type sub-filters. The same outcome is reachable
today via the **Templates** button: it lives next to **New
Element** in the same toolbar. A follow-up issue may merge the two
flows once the basic UX has been validated.

## Why no versioning

Templates are user-authored shortcuts, not authoritative records.
Editing in place matches how users think about saved configurations
(closer to a browser bookmark than to an element). Versioning would
introduce a table doubling, a versions endpoint per surface, and a
rollback story that nobody has asked for. If demand surfaces later,
the existing `element_versions`-style table is the obvious add.

## Why set-scoped + global, not "global only" or "set-only"

Set-only would force every project to re-author the same baseline
templates. Global-only would mix workspace-specific shapes (FIXM
extension X for set A) into every set's pool. The two-level model
mirrors how tags are scoped in Iris (per-set) but adds an explicit
opt-in for shared shapes via `is_global`.

## Why the field whitelist

Without a whitelist, a malicious or buggy caller could snapshot
`created_by`, `id`, `is_deleted` or similar fields into `template_data`
and have them write back during `apply_template_to_create_body`. The
whitelist makes the captured surface a small, audited set and
documents (in code) the public element schema.

## Why no template dropdown on EntityDialog in v1

`EntityDialog.svelte` carries five notation-specific sub-filters
(`SIMPLE_DIAGRAM_TYPE_FILTER`, `UML_DIAGRAM_TYPE_FILTER`,
`ARCHIMATE_DIAGRAM_TYPE_LAYERS`, `C4_DIAGRAM_TYPE_LEVELS`,
`BPMN_DIAGRAM_TYPE_FILTER`) plus a C4 picker, a layer reset on
notation change, and a `showAllTypes` toggle. Pre-filling its state
from a template's `template_data` would require mapping every
notation's `element_type` representation into the dialog's
`SimpleEntityType` union and stabilising the cross-notation reset
logic. The Templates button on the same toolbar is a clean separate
flow that covers the user's stated need without touching that
codepath. v2 of templates can merge the two flows once the baseline
ships.

## Consequences

- New module `backend/app/element_templates/` (models, service,
  router).
- Migrations: SQLite `m067_element_templates.py`, Supabase mirror
  `m071_element_templates.sql` (`m067_*.sql` was already taken by
  the doview_analysis pointer fix, so the Supabase numbering jumps
  to `m071`).
- `backend/app/elements/{models,router}.py` gain `template_id` on
  `ElementCreate` and apply-template logic on `POST /api/elements`.
- `mcp/src/iris_mcp/tools.py` gains five `*_element_template` tools
  and a `template_id` parameter on `create_element`.
- `cli/src/iris_cli/main.py` gains the matching subcommands and the
  `--template-id` flag.
- `scripts/check_surface_parity.py` learns the entity and kebab-case
  CLI normalisation.
- New Svelte components `TemplatesListDialog.svelte`,
  `CreateTemplateDialog.svelte`; new route
  `frontend/src/routes/element-templates/[id]/+page.svelte`.
- Existing elements-list and element-detail routes gain the two new
  buttons.
- Tests: backend (27 + 7 schema), MCP (12), CLI (8), frontend (20).
  56 new tests.
- CHANGELOG `[6.8.0]`; README gains a short Templates subsection;
  version bumps to `6.8.0` in `frontend/package.json` and
  `mcp/pyproject.toml`.

## Verification

- `pytest backend/tests/test_element_templates/ backend/tests/test_migrations/test_element_templates_schema.py` — 34 green.
- `pytest mcp/tests/test_element_templates.py` — 12 green.
- `pytest cli/tests/test_element_templates.py` — 8 green.
- `npx vitest run tests/unit/elementTemplates.test.ts` — 20 green.
- `python scripts/check_surface_parity.py` — green; `element_template`
  is a known entity with all three create/update surfaces present
  and `delete_element_template` listed under the deferred-delete
  exception.
- Browser smoke: create a template from an existing element via
  Save as template; open the Templates dialog from the elements
  list; use a template to create a new element; verify pre-fill via
  the detail page.
- Supabase migrate: apply `m071_element_templates.sql` before the
  v6.8.0 code deploy (Protocol §15 release ordering).

## See also

- [SPEC-191-A](specs/SPEC-191-A-Element-Templates.md) — implementation spec.
- [ADR-184](ADR-184-Element-Package-Membership.md) — package_id
  is one of the eight whitelisted fields.
- [ADR-182](ADR-182-Surface-Parity-Discipline.md) — parity rules.
- Protocol §14 (Surface Parity) and §15 (SQLite ↔ Supabase parity).
- Issue [#153](https://github.com/cgbarlow/iris/issues/153).
