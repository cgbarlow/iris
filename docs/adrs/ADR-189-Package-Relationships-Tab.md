# ADR-189: Package detail Relationships tab

Status: Accepted (2026-05-16)
Extends: [ADR-184](ADR-184-Element-Package-Membership.md)

## Context

Issue [#157](https://github.com/cgbarlow/iris/issues/157) — the
original plan for issue #133 (cascade UX polish) included a
"Relationships" tab on the package detail page that lists the
elements attached to the package, mirroring the relationship surface
already shown on the views/diagrams detail page. That tab was missed
during the v6.1.0 / v6.7.0 work and the package detail page shipped
with only **Details** and **Version History**.

Result: when a user lands on a package, they can read the package's
own metadata and version history but have no way to see what elements
sit beneath it. The data is there
(`GET /api/packages/{id}/elements`, paginated `ElementListResponse`,
introduced in v6.7.0 with ADR-184) but no UI surfaces it.

## Decision

Add a third tab to `frontend/src/routes/packages/[id]/+page.svelte`
called **Relationships**. Selecting the tab lazy-loads
`GET /api/packages/{id}/elements?page_size=200` once and renders a
plain table of `name | type | notation | updated`. Each name is a
link to `/elements/{id}`.

Scope is deliberately narrow: only elements-in-package. The views
page surfaces three sub-tables (memberships / element relationships /
diagram relationships) because views *aggregate* multiple relationship
kinds. Packages, by contrast, have a single hierarchical relationship
of interest at this stage: the elements that belong to them. If
follow-up issues want package-level views or diagrams listed here,
they can extend this tab — the structural pattern is the same.

The first 200 rows cover every package that has been observed in
production data. If a package grows past 200 elements, the table
becomes paginated as a follow-up; until then, a single fetch keeps
the UI simple and stateless.

## Why a new tab rather than an Accordion section under Details

Tabs are the established information-architecture for related-but-
distinct surfaces on entity pages (views/diagrams pages already use
this pattern). Putting elements into the Details accordion would mix
"metadata about this package" with "things contained in this
package", weakening both.

## Why lazy-load instead of eager

Most package visits are read-only and don't need the element list.
Lazy-loading on first tab activation keeps the initial page render
fast (especially for big sets) and matches the loading pattern used
by Version History on the same page.

## Consequences

- `frontend/src/routes/packages/[id]/+page.svelte` — new state
  (`packageElements`, `packageElementsLoading`, `packageElementsTotal`,
  `packageElementsLoaded`), new loader (`loadPackageElements`), new
  tab handler (`activateRelationshipsTab`), new tab button in the
  tablist, new tabpanel branch with the table.
- `frontend/tests/unit/packageRelationshipsTab.test.ts` — new
  static-parser test (9 assertions) covering state, API call, tab
  affordance, and accessibility attributes.
- No backend changes; no migration; no MCP / CLI changes.
- CHANGELOG `[6.7.4]`.

## Verification

- `npx vitest run tests/unit/packageRelationshipsTab.test.ts` — 9
  green.
- Browser smoke (dev.sh smoke step): create a package with a few
  elements in it, navigate to `/packages/{id}`, click the
  **Relationships** tab. Confirm element list renders, the total
  count is correct, and clicking through navigates to
  `/elements/{id}`. Verify empty state message on a package with no
  elements.

## See also

- [ADR-184](ADR-184-Element-Package-Membership.md) — the membership
  data model the tab reads.
- Issue [#157](https://github.com/cgbarlow/iris/issues/157).
- Reference pattern: `frontend/src/routes/views/[id]/+page.svelte`
  Relationships sections (≈ line 3247).
