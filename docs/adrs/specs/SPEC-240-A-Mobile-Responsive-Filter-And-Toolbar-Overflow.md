# SPEC-240-A: Mobile-responsive filter and toolbar overflow fixes

Implements **[ADR-240](../ADR-240-Mobile-Responsive-Filter-And-Toolbar-Overflow.md)**.

## 1. Canonical responsive selector pattern

`SetSelector.svelte` is the source of truth. Both filter selectors use the same
wrapper + `<select>` classes (DRY §13):

| Element | Classes |
|---------|---------|
| wrapper `<div>` | `flex min-w-0 flex-col items-start gap-1 sm:flex-row sm:items-center sm:gap-2` |
| `<select>` | `w-full min-w-0 max-w-full truncate rounded border px-3 py-1.5 text-sm sm:w-auto sm:max-w-xs` |

**Change:** `CollectionSelector.svelte` adopts both (previously
`flex items-center gap-2` wrapper and an unconstrained `rounded border px-3 py-1.5
text-sm` select). `min-w-0` lets the flex child shrink below its content width;
`truncate` ellipsises a long collection name instead of widening the row.

## 2. Bookmarks header (`routes/bookmarks/+page.svelte`)

| Element | Before | After |
|---------|--------|-------|
| header row | `flex items-center justify-between` | `flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between` |
| filter group | `flex items-center gap-2` | `flex w-full min-w-0 flex-col gap-2 sm:w-auto sm:flex-row sm:items-center` |

Mobile: title block stacks above a full-width filter column (each selector full
width). At `sm` (≥640px) it reverts to the original title-left / filters-right row.

## 3. View toolbar (`routes/views/[id]/+page.svelte`)

Both "View group" containers — the sequence-diagram toolbar and the non-sequence
toolbar — change from:

```
<div class="ml-auto flex items-center gap-2">
```

to:

```
<div class="ml-auto flex flex-wrap items-center justify-end gap-2">
```

`flex-wrap` lets the Comments / Checklist / TOC / Full-screen buttons wrap to a second
line; `justify-end` keeps the wrapped rows right-aligned under `ml-auto`. Both copies
must stay identical (known duplication, per ADR-240).

## 4. Tests (TDD)

Added to `frontend/tests/e2e/no-overflow.mobile.spec.ts` (ADR-229 `mobile` project,
Pixel 5 393px), reusing the existing `expectNoHorizontalOverflow(page)` helper
(asserts `documentElement.scrollWidth − clientWidth ≤ 1`):

1. **`bookmarks page filters do not overflow`** — seed admin, log in, `goto('/bookmarks')`,
   assert `#collection-selector` and `#set-selector` visible, then no overflow.
2. **`markdown view toolbar with checklist button does not overflow`** — create a
   `text`/`markdown` diagram with multi-item list content, log in, open the view,
   wait for the `Toggle checklist mode` button, then no overflow.

Run: `npm run test:mobile` (frontend).

## 5. Out of scope

- Extracting the duplicated "View group" block into a shared snippet (deferred,
  flagged in ADR-240).
