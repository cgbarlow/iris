# SPEC-195-A: Package detail state reset on navigation

Implements: [ADR-195](../ADR-195-Package-Detail-State-Reset-On-Navigation.md)
Resolves: Issue [#173](https://github.com/cgbarlow/iris/issues/173) item 3
Status: Living

## Per-package state inventory

State declared in `frontend/src/routes/packages/[id]/+page.svelte`
whose meaning is "about the currently-viewed package". Every entry
in the **Reset** column is cleared at the top of `loadPackage(id)`.

| State | Meaning | Reset |
|---|---|---|
| `pkg` | The package record itself | implicit (overwritten by fetch) |
| `parentPackageName` | Parent package's display name | yes (set to `null`) |
| `versions` | Version history list | implicit (`loadVersions` overwrites) |
| `loading` / `error` | Page-level fetch state | yes |
| `packageElements` | Relationships tab — elements list | **yes** (was the bug) |
| `packageElementsLoaded` | Relationships tab — hydration flag | **yes** (was the bug) |
| `packageElementsLoading` | Relationships tab — in-flight flag | **yes** |
| `packageElementsTotal` | Relationships tab — total count | **yes** |
| `packageElementsError` | Relationships tab — fetch error | **yes** |
| `editingDetails` | Inline edit mode flag | **yes** |
| `detailsDirty` | Inline edit unsaved-changes flag | **yes** |
| `editName` / `editDescription` | Edit-mode field buffers | implicit (re-seeded by `enterDetailsEdit`) |
| `isBookmarked` | Bookmark indicator | reset by `loadBookmarkStatus` |
| `hierarchyTree` | Sidebar hierarchy (keyed on `set_id`) | not reset — sidebar lives across packages within a set; refresh handled by `loadHierarchyTree` calls in mutation handlers |
| `showDeleteDialog` / `showParentPicker` / `showCreateChild*Dialog` | Transient modal flags | not reset — modals are user-initiated actions, not derived state |
| `cloneLoading` | In-flight clone indicator | not reset — clone navigates away on success |

The reset block sits *before* the `try { ... }` to ensure it fires
even if the network call throws.

## Reset block

```ts
// Issue #173 item 3
packageElementsLoaded = false;
packageElementsLoading = false;
packageElements = [];
packageElementsTotal = 0;
packageElementsError = null;
editingDetails = false;
detailsDirty = false;
```

## Acceptance criteria

1. After viewing package A's Relationships tab, navigating to
   package B and opening its Relationships tab shows B's elements
   without a hard refresh.
2. A user editing details on A who navigates to B sees B's read-
   only Details view (not A's edit-mode buffers).
3. Repeat-opening the same package's Relationships tab without
   navigation still skips the redundant fetch
   (`!packageElementsLoaded && !packageElementsLoading` guard
   preserved).
4. Mutation handlers that call `loadPackage(pkg.id)` to refresh
   after a save (`saveDetails`, `handleSetParent`,
   `handleRemoveParent`) will re-fetch the relationships list,
   which is the desired behaviour — these are usually triggered by
   changes that may affect membership.

## Tests

`frontend/tests/unit/packageDetailStateReset.test.ts` — 8 cases:

1-5. Each of the five `packageElements*` flags is reset in
   `loadPackage`'s body.
6-7. `editingDetails` and `detailsDirty` reset in the same place.
8. Activation-side guard `!packageElementsLoaded &&
   !packageElementsLoading` remains in `activateRelationshipsTab`.

Also re-runs `tests/unit/packageRelationshipsTab.test.ts` to
confirm no regression to the existing ADR-189 behaviour.

## Verification

```
npx vitest run \
  tests/unit/packageDetailStateReset.test.ts \
  tests/unit/packageRelationshipsTab.test.ts
```

Both files green. Manual smoke per ADR-195 verification section.
