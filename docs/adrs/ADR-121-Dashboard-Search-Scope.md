# ADR-121: Dashboard Search Scope

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-121 |
| **Initiative** | Search |
| **Proposed By** | Engineering |
| **Date** | 2026-04-21 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** the dashboard page (`/`) which provides two
scoped affordances — a **counts panel** showing how many collections,
sets, packages, diagrams, and elements exist in the currently-focused
scope, and a **search bar** querying `/api/search` — where the focused
scope is derived as "URL param wins, else sessionStorage-persisted
last-active set/collection, else global" so that clicking an entity
link carries its scope and navigation preserves the user's last-used
filter,

**facing** GitHub issues #16 and #17: on the UAT deployment a user
typed "msd" in the dashboard search box with no visible filters and
got zero results, when an "NZ Ministry of Social Development (MSD)"
package demonstrably exists. Root cause — after the user had
previously viewed a set, sessionStorage held that set's id; on return
to `/` without URL params the search bar still filtered to that stale
set, silently excluding every other scope. The UI gave no indication
that a filter was active, so the bug presented as "search is broken",

**we decided for** **scope bifurcation** in `+page.svelte`: the
counts panel continues to use the URL-OR-sessionStorage scope (the
"remember last set" UX is correct — the panel visibly displays the
active set name in the dashboard header), but the search bar reads
scope from URL params **only**. Empty URL params = unscoped global
search. `handleSearch()` uses the new `searchSetId` / `searchCollectionId`
deriveds; `loadDashboard()` is unchanged,

**and neglected** (a) clearing sessionStorage on every visit to `/`
— loses the counts-remember-last-set UX users rely on; (b) adding a
visible "you are filtering by X" banner on the dashboard — more UI
surface, doesn't fix the root cause that the search scope is the wrong
one; (c) always searching unscoped regardless of URL params — loses
the scoped-search entry point when a user clicks a set and lands on
`/` with `?set_id=…`,

**to achieve** the user's mental model: "an empty-looking dashboard
should search everything". Counts can still reflect a remembered
scope because the scope is visible in the counts UI; search cannot
because the search UI does not display its scope,

**accepting that** the two affordances now diverge in one subtle way
(counts remember, search does not) — mitigated by the fact that the
divergence matches what users see: the counts header shows the active
set, the search bar does not; and accepting that a URL with
`?set_id=X` still scopes search, so deep-linked scoped search
continues to work for authenticated scripted flows.

---

## Summary

| Capability | Description | Specification |
|------------|-------------|---------------|
| Dashboard Search Scope | Separate `searchSetId` / `searchCollectionId` deriveds that read URL params only, used by `handleSearch()`. Existing `setId` / `collectionId` (URL + sessionStorage) continue to drive the counts panel via `loadDashboard()`. Playwright e2e test seeds two sets, visits the scoped dashboard once, navigates away, returns to `/`, searches for a term unique to the other set, asserts non-empty results. | _inline; single-file change, no SPEC needed_ |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Extends | ADR-116 | Knowledge Graph Visualization | Same dashboard page; unrelated capability. |

---

## References

None. Implementation is a single-file code change; the ADR captures the semantic decision.

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Engineering | 2026-04-21 |
| Approved | Engineering | 2026-04-21 |
