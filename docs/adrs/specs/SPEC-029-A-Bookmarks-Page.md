# SPEC-029-A: Bookmarks Page

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-029-A |
| **ADR Reference** | [ADR-029: Bookmarks Page](../ADR-029-Bookmarks-Page.md) |
| **Date** | 2026-02-28 |
| **Status** | Active |

---

## Overview

This specification covers the implementation of a dedicated bookmarks page at `/bookmarks` and the addition of a "Bookmarks" sidebar navigation link. The page lists all bookmarked models with their details and provides the ability to remove bookmarks.

---

## A. Frontend Route: `/bookmarks`

### Route File

Create `frontend/src/routes/bookmarks/+page.svelte`.

### Data Loading

On mount (via `$effect`), the page:
1. Calls `GET /api/bookmarks` to retrieve the user's `Bookmark[]`
2. For each bookmark, calls `GET /api/models/{model_id}` to resolve the `Model` details
3. Stores results as `BookmarkWithModel[]` where each entry pairs a `Bookmark` with a nullable `Model`
4. Models that fail to resolve (deleted, permission error) are stored with `model: null` and displayed as "unavailable"

### State Management

```typescript
interface BookmarkWithModel {
    bookmark: Bookmark;
    model: Model | null;
}

let bookmarks = $state<BookmarkWithModel[]>([]);
let loading = $state(true);
let error = $state<string | null>(null);
```

### Remove Bookmark

Each bookmark row has a "Remove" button that calls `DELETE /api/models/{model_id}/bookmark` and optimistically removes the bookmark from the local list on success.

---

## B. Page Layout

### Header

- `<h1>` with text "Bookmarks"
- Subtitle paragraph: "Your bookmarked models."

### Loading State

- Text "Loading bookmarks..." shown while fetching

### Error State

- Error message displayed in a `role="alert"` div styled with `--color-danger`

### Empty State

- Text: "No bookmarked models yet. Bookmark a model from its detail page."

### Bookmark List

Each bookmark is rendered as a list item (`<li>`) containing:
- A link to the model detail page (`/models/{model.id}`) showing:
  - Model name (bold)
  - Model type badge
  - Truncated description (60 chars max)
- Updated date
- Remove button (styled with danger color)

For unavailable models (where model resolution failed):
- Text: "Model {bookmark.model_id} (unavailable)"
- Remove button still available

### Accessibility

- `aria-live="polite"` on the content region for dynamic updates
- `<svelte:head>` sets page title to "Bookmarks — Iris"
- All interactive elements are keyboard accessible

---

## C. Sidebar Navigation

### AppShell.svelte Update

Insert a "Bookmarks" entry into the `navItems` array between "Entities" and "Settings":

```javascript
const navItems = [
    { href: '/', label: 'Dashboard', shortcut: 'H' },
    { href: '/models', label: 'Models', shortcut: 'M' },
    { href: '/entities', label: 'Entities', shortcut: 'E' },
    { href: '/bookmarks', label: 'Bookmarks', shortcut: 'B' },
    { href: '/settings', label: 'Settings', shortcut: 'S' },
];
```

The shortcut `B` is assigned to Bookmarks. The sidebar link follows the same styling and `aria-current` pattern as existing nav items.

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| Bookmarks page loads at `/bookmarks` | Navigate to `/bookmarks`; verify page renders with heading |
| Bookmarks are listed with model details | Bookmark a model; visit `/bookmarks`; verify model name, type, description shown |
| Remove button removes bookmark | Click "Remove" on a bookmark; verify it disappears from the list |
| Empty state shown when no bookmarks | Remove all bookmarks; verify empty state message |
| Unavailable models shown gracefully | Bookmark a model, then delete the model; verify "unavailable" text on bookmarks page |
| Sidebar shows Bookmarks link | Verify "Bookmarks" appears in sidebar between "Entities" and "Settings" |
| Sidebar link navigates to `/bookmarks` | Click "Bookmarks" in sidebar; verify URL is `/bookmarks` |
| Sidebar highlights active page | Navigate to `/bookmarks`; verify sidebar link has `aria-current="page"` |
| Page title set correctly | Navigate to `/bookmarks`; verify browser tab shows "Bookmarks — Iris" |
| Loading state displayed | Verify "Loading bookmarks..." shown during data fetch |
| Error state displayed | Simulate API failure; verify error message shown |

---

*This specification implements [ADR-029](../ADR-029-Bookmarks-Page.md).*
