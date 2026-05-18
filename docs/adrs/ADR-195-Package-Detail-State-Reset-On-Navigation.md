# ADR-195: Package detail page resets per-package state on navigation

Status: Accepted (2026-05-18)
Extends: [ADR-189](ADR-189-Package-Relationships-Tab.md)

## Context

Issue [#173](https://github.com/cgbarlow/iris/issues/173) item 3 —
when a user viewed package A's Relationships tab (hydrating the
elements list), then navigated to package B and opened its
Relationships tab, B's tab showed A's elements. A hard browser
refresh fixed it; in-app navigation did not.

ADR-189 introduced lazy hydration on the Relationships tab via a
`packageElementsLoaded` boolean — first activation fetches, later
activations short-circuit. The short-circuit was sound for repeat
opens of the same package's tab, but the page's navigation handler
(`$effect` keyed on `page.params.id`) only re-ran `loadPackage(id)`,
which reset `pkg`, `parentPackageName`, `error`, and `loading` but
left `packageElements*` untouched. When `activateRelationshipsTab`
then asked "is it loaded?" the answer was "yes — for the previous
package". The fetch never re-fired; the old data rendered against
the new package's heading.

The same latching pattern affected the inline edit state
(`editingDetails`, `detailsDirty`) — a user who left edit mode
active and navigated would see edit mode persist on the new
package, with the previous package's field values still in the
inputs.

## Decision

`loadPackage(id)` resets *all* per-package derived state at the top
of the function — before the network call returns. The bug pattern
is general (any cached `*Loaded` flag held against the page's
package identity), so the reset is general: every piece of state
whose meaning is "about package P" gets cleared.

Concretely, before the fetch:

```ts
packageElementsLoaded = false;
packageElementsLoading = false;
packageElements = [];
packageElementsTotal = 0;
packageElementsError = null;
editingDetails = false;
detailsDirty = false;
```

The activation-side guard
(`!packageElementsLoaded && !packageElementsLoading`) is unchanged —
opening the tab twice without navigation still skips the redundant
fetch. The reset moves the invalidation responsibility to the
identity-change boundary, which is where it should have lived from
the start.

## Why reset in `loadPackage` rather than in the `$effect`

`loadPackage` is the single chokepoint reached by every navigation,
the first mount, and every post-mutation refresh (`saveDetails`,
`handleSetParent`, `handleRemoveParent`). Resetting there means
every path that loads a new package identity benefits, including
the in-place "refresh after mutation" paths where the state has
intentionally not changed and the cached elements *should* be
re-fetched to reflect the mutation.

## Why not invalidate on `params.id` change directly

The `$effect` could compare previous and current `id`s and only
reset on a real navigation, leaving in-place refreshes alone.
Skipped: it would preserve a stale relationships list across edits
that don't touch package membership, but it would *also* preserve
stale data across edits that do. Always-reset is the safer default
for a tab that fetches in <100ms.

## Consequences

- `frontend/src/routes/packages/[id]/+page.svelte` — seven lines of
  resets inside `loadPackage` (lines ~132-141).
- `frontend/tests/unit/packageDetailStateReset.test.ts` — new
  static-parser test (8 assertions) asserts every reset is present
  and that the activation-side guard still works.
- No backend changes, no migration, no MCP / CLI changes.
- CHANGELOG `[6.8.4]`.

## Verification

- `npx vitest run tests/unit/packageDetailStateReset.test.ts
  tests/unit/packageRelationshipsTab.test.ts` — 21 green.
- Browser smoke: visit `/packages/{A}` → Relationships, open the
  tab to hydrate, navigate to `/packages/{B}` (where B's element
  set differs), open Relationships — B's elements render without
  a hard refresh.

## See also

- [ADR-189](ADR-189-Package-Relationships-Tab.md) — the lazy
  hydration mechanism whose invalidation gap this ADR closes.
- Issue [#173](https://github.com/cgbarlow/iris/issues/173) item 3.
