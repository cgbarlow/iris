# SPEC-075-B: Admin-Configurable Views — Frontend

**ADR:** [ADR-075](../adrs/ADR-075-Admin-Configurable-Views.md)
**Status:** Implemented

---

## Overview

Frontend implementation: global view store, view selector dropdown, and admin CRUD page.

## View Store (`viewStore.svelte.ts`)

Global reactive store managing the active view:

- **State**: `views: View[]`, `activeViewId: string` (persisted in localStorage as `iris_active_view`)
- **Functions**:
  - `getViews()` — returns all views
  - `getActiveViewId()` — returns current active view ID
  - `getActiveView()` — returns current View object
  - `getActiveConfig()` — returns ViewConfig with sensible defaults
  - `setActiveView(viewId)` — sets active view and persists to localStorage
  - `loadViews()` — fetches views from `/api/views`
- **Default fallback**: If no matching view found, returns config with all features enabled

## ViewSelector Component

Dropdown in top navigation:

- Renders `<select>` with `aria-label="Active view"`
- Loads views on mount via `loadViews()`
- On change, calls `setActiveView(target.value)`
- Only renders when views are loaded (`views.length > 0`)

## Admin Views Page (`/admin/views`)

Full CRUD interface:

- **List**: Shows all views with name, description, Default badge, Edit/Delete buttons
- **Create**: "New View" button opens form with name, description, JSON config textarea
- **Edit**: Click Edit to populate form with existing view data
- **Delete**: Confirmation dialog, disabled for default views
- **Config editing**: Raw JSON textarea with pre-populated default config template

## Files

- `frontend/src/lib/stores/viewStore.svelte.ts`
- `frontend/src/lib/components/ViewSelector.svelte`
- `frontend/src/routes/admin/views/+page.svelte`
