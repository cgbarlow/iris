# ADR-184: Element → package optional membership

Status: Accepted (2026-05-16)
Extends: [ADR-178](ADR-178-MCP-Update-Move-Tools.md)

## Context

Issue [#149](https://github.com/cgbarlow/iris/issues/149) — "Enhancement:
Optionally allow elements to belong to a package, not just a set." Today
elements carry a nullable `set_id` (introduced in m016 when `entities`
was renamed to `elements`) but have no direct relationship to packages.
A package can be associated with a set, and diagrams within a set can be
parented to packages; elements transitively "belong to" a package only by
appearing on a diagram that does.

The user wants direct, first-class element → package membership exposed
on every surface (API, CLI, MCP, GUI), plus a third section under the
existing `/view` Relationships tab listing element → package memberships
for elements drawn on the current diagram.

Plan-time clarification fixed cardinality at **one package per element**.
Many-to-many membership and a relationship-row representation were
both considered and rejected (see "Why not…" sections below).

This decision also unlocks the package-elements source mode of the new
`dynamic_list` diagram type ([ADR-186](ADR-186-Dynamic-List-Diagram-Type.md)).

## Decision

Add a single nullable column to the `elements` table:

```sql
ALTER TABLE elements ADD COLUMN package_id TEXT REFERENCES packages(id);
CREATE INDEX idx_elements_package ON elements(package_id);
```

`package_id` is **additive and orthogonal** to `set_id`. An element may
have neither, just a `set_id`, just a `package_id`, or both. The column
lives on the `elements` table itself (alongside `set_id` and `notation`),
not on `element_versions` — package membership is identity, not content.

### Cross-field invariant

If both `element.set_id IS NOT NULL` AND `element.package_id IS NOT NULL`,
the referenced package's `set_id` must equal the element's `set_id`, or
the package's `set_id` must be NULL.

Enforced in the service layer (`create_element` / `update_element`) and
surfaced as **HTTP 422** with a concrete error message. No DB-level
CHECK constraint — keeping the migration SQLite-portable and avoiding
schema drift between adapters.

**Edge case** (cross-set move): when an `update_element` call changes
`set_id` to a set that does not contain the element's existing
`package_id`, the update also clears `package_id` in the same operation
(zero-friction set-moves; the caller can re-attach the element to a
package in the new set afterwards).

### Update verb, not a move verb

`ElementUpdate` is extended to accept `package_id: str | None`. Setting
to literal `None` clears the membership. No new endpoint, no
`move_element` tool — ADR-178's "elements travel with their parent
diagram" invariant remains intact (and is unrelated, since `package_id`
is an orthogonal pool-level membership, not a diagram parentage).

### Read model

`ElementResponse` gains `package_id: str | None` and
`package_name: str | None` mirroring the existing `set_id` / `set_name`
pair. Service joins extended once.

### List + filter

`list_elements` gains an optional `package_id` query parameter with the
three-valued semantics codified in [ADR-185](ADR-185-Nullable-Filter-Convention.md)
(`omitted` / `"null"` literal / exact match). The shared
`parse_nullable_id` helper extracted in ADR-185 is reused.

New endpoint `GET /api/packages/{id}/elements` (paginated) mirrors the
existing `GET /api/packages/{id}/diagrams`. Service helper
`list_package_elements(db, package_id, page, page_size)` is exposed for
reuse by the dynamic_list package-mode compute path.

### Relationships tab augmentation

`GET /api/diagrams/{id}/relationships` response gains a third array
`element_package_memberships`. Each entry: `{element_id, element_name,
package_id, package_name}`, restricted to elements drawn on the current
diagram whose `package_id` is non-null. Single round-trip — no extra
endpoint.

The frontend `/view` Relationships tab adds a new section *Element →
Package memberships* between the existing diagram-relationships and
element-relationships sections, following the same visual pattern. The
tab pill counter sums all three categories.

### Surface parity

| Verb | Backend | CLI | MCP |
|---|---|---|---|
| Set/clear `package_id` on an element | `PUT /api/elements/{id}` body `package_id` | `iris elements update <id> --package-id <pkg|null>` | `update_element(element_id, package_id?)` |
| Filter elements by package | `GET /api/elements?package_id=...` | `iris elements list --package-id <pkg|null>` | `list_elements(package_id?)` |
| List a package's elements | `GET /api/packages/{id}/elements` | `iris packages list-elements <pkg>` | `list_package_elements(package_id)` |

`scripts/check_surface_parity.py` requires no exception — `package_id`
is an enrichment of the existing `update_element` write verb, not a new
write verb; the new `list_*` is a read verb outside the script's scope.

## Why one package per element (not many-to-many)

- The user explicitly chose one-package-per-element when asked.
- A nullable column is the smallest possible schema delta. No join
  table, no membership lifecycle, no ordering questions.
- Mirrors how diagrams already nest under packages (`parent_package_id`
  on `diagrams`). Consistent mental model.

## Why not a row in the `relationships` table

- The existing `relationships` table strictly connects element ↔ element
  (`source_element_id`, `target_element_id`). Widening the schema to
  permit non-element endpoints would force every consumer to handle a
  union type and would muddle a clean cross-cutting concept.
- Membership is a different concept from relatedness. Conflating them
  would lose the semantic distinction.

## Why an additional column rather than reusing `set_id`

- `set_id` and `package_id` carry different meanings: `set_id` says
  "this element belongs to this set's pool"; `package_id` says "this
  element is grouped under this package within that pool". Packages and
  sets are siblings in the hierarchy, not aliases.
- Coupling the two would block packages from spanning multiple sets
  (today they can be set-free), and would require a back-fill step we
  do not need.

## Consequences

- New migration `backend/app/migrations/m064_element_package_membership.py`
  adds the column + index. No back-fill — every existing element has
  `package_id=NULL`.
- `backend/app/elements/models.py`: `ElementCreate`, `ElementUpdate`,
  `ElementResponse` extended.
- `backend/app/elements/service.py`: invariant enforcement in create +
  update; `package_name` join on read; `package_id` filter on list;
  cross-set move clearing logic on update.
- `backend/app/elements/router.py`: wire `package_id` through; add
  `package_id` to the list filter; use `parse_nullable_id`.
- `backend/app/packages/router.py` + `service.py`: new endpoint +
  helper.
- `backend/app/diagrams/router.py` (or `service.py`): extend
  `/relationships` response with `element_package_memberships`.
- `cli/src/iris_cli/main.py`: `--package-id` on `elements update` and
  `elements list`; new `packages list-elements`.
- `mcp/src/iris_mcp/tools.py`: extended `update_element` /
  `list_elements`; new `list_package_elements`.
- `frontend/src/routes/views/[id]/+page.svelte`: third section in the
  Relationships tab + pill counter update.
- Frontend element-edit form: `PackagePicker` integration.
- CHANGELOG `[6.7.0]`.

## Verification

- `pytest backend/tests/test_element_package_membership.py` — column
  added, invariant rejects mismatch, accepts match, update with
  `package_id=None` clears, `list_elements?package_id=null` filters,
  `GET /api/packages/{id}/elements` paginates, cross-set move clears
  `package_id`.
- `pytest backend/tests/test_nullable_filter.py` — shared helper unit
  tests (also exercised via `list_diagrams.parent_package_id`).
- `pytest cli/tests/test_elements_package.py` — CLI round-trip.
- `pytest mcp/tests/test_update_element_package.py` — MCP round-trip.
- `npx playwright test element-package-membership.spec.ts` — element
  form package picker; element-detail page; Relationships-tab third
  section.
- `python scripts/check_surface_parity.py` — passes.

## See also

- [SPEC-184-A](specs/SPEC-184-A-Element-Package-Membership.md) — schema
  delta, invariant pseudocode, API surface, GUI section, acceptance
  criteria.
- [ADR-185](ADR-185-Nullable-Filter-Convention.md) — three-valued
  nullable-filter convention used here and by `list_diagrams`.
- [ADR-178](ADR-178-MCP-Update-Move-Tools.md) — `move_element`
  forbidden invariant; this ADR is consistent with that.
- [ADR-186](ADR-186-Dynamic-List-Diagram-Type.md) — dynamic_list
  package-mode source depends on `package_id`.
- Issue [#149](https://github.com/cgbarlow/iris/issues/149).
