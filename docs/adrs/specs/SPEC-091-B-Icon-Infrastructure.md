# SPEC-091-B: Icon Infrastructure

**ADR:** ADR-091
**Date:** 2026-03-08

## Changes

### 1. Install lucide-svelte

Add `lucide-svelte` as a frontend dependency. Import icons by name for tree-shaking:

```ts
import { Server, AppWindow, Database } from 'lucide-svelte';
```

### 2. Icon reference data model

Store icon assignments on nodes as a structured reference in visual data:

```ts
interface IconRef {
  set: 'lucide' | 'archimate' | 'custom';
  name: string;  // icon identifier within the set
}
```

Add `icon?: IconRef` to the node visual override schema (backend Pydantic model and
frontend type).

### 3. IconRenderer component

Create `IconRenderer.svelte` that resolves an `IconRef` to the correct SVG:
- `lucide` set: dynamically import from lucide-svelte
- `archimate` set: render from existing ArchiMate SVG assets
- Fallback: render nothing if icon not found (no broken state)

### 4. Semantic matching during EA import

Add `icon_mapper.py` in `import_sparx/` with a mapping table from EA stereotype strings to
Lucide icon names. Apply during `build_node_visual()`:

| EA Stereotype | Lucide Icon |
|---|---|
| ApplicationComponent | `app-window` |
| Node | `server` |
| DataObject | `database` |
| Artifact | `file-code` |
| BusinessProcess | `workflow` |

Unmapped stereotypes receive no icon (graceful degradation).

### 5. Backend schema migration

Add nullable `icon_set` (varchar) and `icon_name` (varchar) columns to the node visual
override table. Update the Pydantic response model to include these fields.

## Test Plan

- Unit test: `icon_mapper.py` maps known stereotypes correctly, returns None for unknown
- Unit test: IconRenderer renders lucide icons, archimate icons, and handles missing icons
- Unit test: backend schema accepts and returns icon fields
