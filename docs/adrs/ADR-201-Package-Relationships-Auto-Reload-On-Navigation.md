# ADR-201: Package detail Relationships tab auto-reloads on cross-package navigation

Status: Accepted (2026-05-18)
Extends: [ADR-195](ADR-195-Package-Detail-State-Reset-On-Navigation.md)

## Context

Follow-up to ADR-195 (v6.8.4). That ADR fixed the stale-data bug by
resetting the relationships state at the top of `loadPackage`, so
navigating from package A to package B no longer left A's elements
rendered against B's heading.

A residual half-bug remained: if the user was already on the
**Relationships** tab and navigated to a different package via the
hierarchy sidebar, the elements list went *empty* and stayed empty
until the user clicked the "Relationships" tab heading. The reset
worked; the auto-hydration was missing.

Mechanism: `loadPackage` clears `packageElementsLoaded` etc., but
the only call site that issues `loadPackageElements` is
`activateRelationshipsTab` (the tab-button click handler). A
navigation event that doesn't fire a tab click never triggers the
re-fetch.

## Decision

At the end of `loadPackage`, after `loading = false`, check whether
the user is sitting on the Relationships tab and kick off
`loadPackageElements(pkg.id)` if so:

```ts
if (pkg && activeTab === 'relationships' && !packageElementsLoading) {
    loadPackageElements(pkg.id);
}
```

The `!packageElementsLoading` guard prevents stomping a concurrent
fetch in the edge case where another code path raced ahead.

## Why not run from a `$effect` watching `activeTab`/`pkg`

Reactivity-driven solution considered:

```ts
$effect(() => {
    if (pkg && activeTab === 'relationships' && !packageElementsLoaded && !packageElementsLoading) {
        loadPackageElements(pkg.id);
    }
});
```

Equally correct and arguably more idiomatic, but it spreads the
"when does the tab hydrate" rule across two places (the original
`activateRelationshipsTab` handler and a new `$effect`). The
in-line follow-up keeps the rule in one place: `loadPackage` is
the single chokepoint for navigation, and the rehydration sits
right next to the reset that necessitated it.

## Why not unify with `activateRelationshipsTab`

Both call sites need the same body, but unifying them means the
tab-click path always re-fetches even when `packageElementsLoaded`
is already true (today's guard short-circuits that). Keeping the
two paths separate preserves the "no redundant fetch on tab
re-open" behaviour.

## Consequences

- `frontend/src/routes/packages/[id]/+page.svelte:loadPackage` —
  5-line trailing block that calls `loadPackageElements` when on
  the relationships tab.
- `frontend/tests/unit/packageRelationshipsAutoReload.test.ts` —
  new static-parser test (3 assertions) verifies the reset is
  preserved, the auto-hydrate fires only on the relationships
  tab, and the in-flight guard is present.
- No backend changes; no migration; no MCP / CLI changes.
- CHANGELOG `[6.10.1]`.

## Verification

```
npx vitest run \
  tests/unit/packageRelationshipsAutoReload.test.ts \
  tests/unit/packageDetailStateReset.test.ts \
  tests/unit/packageRelationshipsTab.test.ts
```

24 green.

Manual smoke: open package A → Relationships tab → click package
B in hierarchy sidebar → B's elements render without a tab-click
or hard refresh.

## See also

- [ADR-195](ADR-195-Package-Detail-State-Reset-On-Navigation.md)
  — the reset that this ADR completes.
- Issue [#173](https://github.com/cgbarlow/iris/issues/173) item 3
  — original feedback.
