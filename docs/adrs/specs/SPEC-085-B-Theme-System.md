# SPEC-085-B: Theme System

## Parent ADR
ADR-085: Per-Element Visual Overrides and Theme System

## Summary
Defines the themes backend (table, CRUD API, seed data) and frontend (store, selector, cascade resolution).

## Database Schema
```sql
CREATE TABLE themes (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    notation TEXT NOT NULL,
    config TEXT NOT NULL DEFAULT '{}',
    is_default INTEGER NOT NULL DEFAULT 0,
    created_by TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

## Theme Config Structure
```json
{
  "element_defaults": { "<entity_type>": { "bgColor": "#...", "borderColor": "#...", "fontColor": "#..." } },
  "stereotype_overrides": { "<stereotype>": { "bgColor": "#..." } },
  "edge_defaults": { "<rel_type>": { "lineColor": "#..." } },
  "global": { "defaultBgColor": "#...", "defaultBorderColor": "#...", "defaultFontColor": "#..." }
}
```

## API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | /api/themes | List all (optional ?notation= filter) |
| POST | /api/themes | Create theme |
| GET | /api/themes/:id | Get theme |
| PUT | /api/themes/:id | Update theme |
| DELETE | /api/themes/:id | Delete (non-default only) |

## Seed Themes
1. "Iris Default" (UML) — white/black defaults
2. "Sparx EA Default" (UML) — yellow class boxes, stereotype colours
3. "Iris Default" (Simple) — white defaults

## Frontend Store
- `themeStore.svelte.ts` — reactive state with `$state` runes
- `resolveNodeVisual(notation, entityType, stereotype?)` — cascade resolution
- `resolveEdgeVisual(notation, relType)` — edge style resolution
- Active theme per notation persisted in localStorage

## Style Cascade
1. Per-element `data.visual`
2. Stereotype override from active theme
3. Element type default from active theme
4. Global default from active theme
5. Renderer hardcoded defaults

## Files
- `backend/app/migrations/m024_themes.py`
- `backend/app/themes/{__init__,models,service,router}.py`
- `frontend/src/lib/stores/themeStore.svelte.ts`
- `frontend/src/lib/components/ThemeSelector.svelte`
- `frontend/src/routes/admin/themes/+page.svelte`
