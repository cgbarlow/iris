# SPEC-062-A: Persistent Set Selection

## Overview

This specification describes the implementation of a persistent set selection mechanism, SetSelector enhancements for inline set creation, detail page tag/template cleanup, and rate limit tuning.

---

## 1. ActiveSet Store (`frontend/src/lib/stores/activeSet.svelte.ts`)

### API

| Function | Signature | Description |
|----------|-----------|-------------|
| `getActiveSetId()` | `() => string` | Returns current set ID (empty string = all sets) |
| `getActiveSetName()` | `() => string` | Returns current set name |
| `setActiveSet()` | `(id: string, name: string) => void` | Sets both ID and name, persists to sessionStorage |
| `clearActiveSet()` | `() => void` | Resets to empty, removes from sessionStorage |

### Storage

- Key: `iris-active-set`
- Format: `{ "id": "<uuid>", "name": "<string>" }`
- Storage: `sessionStorage` (per-tab, clears on tab close)

---

## 2. AppShell Header Integration

When a set is active, the header displays: `Iris / {SetName}`

- "Iris" links to `/` (existing)
- `/ {SetName}` links to `/sets`
- Uses `$derived` to reactively read from the store
- Style: `color: var(--color-fg)`, `text-lg` (matches "Iris" weight)

---

## 3. Page Sync Behavior

### Dashboard (`/`)

- On load with `?set_id=` param: calls `setActiveSet(id, name)` after resolving set info
- "Reset filter" button: calls `clearActiveSet()` and navigates to `/`
- Search: includes `set_id` filter when active

### Models (`/models`)

- Initializes `currentSetId` from URL param (`?set_id=`) or global store
- SetSelector changes: updates both local state and global store via `setActiveSet()`
- Clearing selector: calls `clearActiveSet()`

### Entities (`/entities`)

- Same pattern as Models page

### Sets (`/sets`)

- Active set highlighted with `border-color: var(--color-primary)` and `border-width: 2px`
- "Reset filter" button visible when a set is active, calls `clearActiveSet()` and navigates to `/`
- Button styling: `rounded border px-3 py-2 text-sm` (consistent with Models page)
- Clicking a set: calls `setActiveSet(id, name)` before navigating to dashboard

---

## 4. SetSelector Enhancements

### New Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `showNewSet` | `boolean` | `false` | Show "+ New Set..." option |
| `onNewSet` | `() => void` | `undefined` | Callback when "+ New Set..." selected |

### Changed Behavior

- `onchange` now passes `(setId: string, setName?: string)` (name from selected option)
- "+ New Set..." option uses value `__new__`, intercepted in change handler (resets to previous value, calls `onNewSet()`)
- Exported `reload()` async function for parent to trigger re-fetch after creating a set

---

## 5. Import Page Set Creation

- SetSelector with `showNewSet={true}` and `onNewSet` callback
- `SetDialog` for inline set creation
- `handleCreateSet`: POST to `/api/sets`, auto-select new set, reload selector
- "View Models" link includes `?set_id=` when a set was selected; sets the global store on click

---

## 6. Detail Page Cleanup

### Model Overview Tab

- **ID field**: Changed from `font-mono text-xs` to `text-sm` (matches other fields)
- **Template**: Read-only "Template: Yes/No" in the `<dl>` grid (was editable checkbox)
- **Tags**: Read-only badge display with pill styling (was editable `TagInput`)
- **Inherited tags**: Shown with muted styling and "Inherited tag" title tooltip

### Model Edit Dialog (`ModelDialog`)

- **New props**: `initialTags`, `initialIsTemplate`, `suggestions`, `inheritedTags`
- **Template checkbox**: Shown in edit mode only
- **TagInput**: Shown in edit mode only with add/remove capability
- **onsave**: Extended to `(name, type, description, tags?, isTemplate?)` — extra params only in edit mode

### Entity Details Tab

- **ID field**: Changed from `font-mono text-xs` to `text-sm`
- **Set field**: Added `entity.set_name ?? 'Default'` matching model overview pattern
- **Tags**: Read-only badge display (was editable `TagInput`)

### Entity Edit Dialog (`EntityDialog`)

- **New props**: `initialTags`, `suggestions`, `inheritedTags`
- **TagInput**: Shown in edit mode only
- **onsave**: Extended to `(name, type, description, tags?)` — extra param only in edit mode

---

## 7. Rate Limit

- `IRIS_RATE_LIMIT_GENERAL` default changed from `100` to `300` requests per 60 seconds
- Configurable via `IRIS_RATE_LIMIT_GENERAL` environment variable (unchanged)

---

## Files Modified

| File | Change |
|------|--------|
| `frontend/src/lib/stores/activeSet.svelte.ts` | **NEW** — global store |
| `frontend/src/lib/components/AppShell.svelte` | Header set display |
| `frontend/src/routes/+page.svelte` | Dashboard store sync, search filter |
| `frontend/src/routes/models/+page.svelte` | Init from store |
| `frontend/src/routes/entities/+page.svelte` | Init from store |
| `frontend/src/routes/sets/+page.svelte` | Highlight, reset, button styling |
| `frontend/src/lib/components/SetSelector.svelte` | New props, reload, name passing |
| `frontend/src/routes/import/+page.svelte` | SetDialog, create flow, View Models link |
| `frontend/src/routes/models/[id]/+page.svelte` | Read-only tags/template, ID styling |
| `frontend/src/lib/components/ModelDialog.svelte` | Tags/template in edit mode |
| `frontend/src/routes/entities/[id]/+page.svelte` | Read-only tags, Set field, ID styling |
| `frontend/src/lib/canvas/controls/EntityDialog.svelte` | Tags in edit mode |
| `backend/app/config.py` | Rate limit 100→300 |
