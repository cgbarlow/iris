# SPEC-103-A: Extension Registry

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-103-A |
| **ADR** | [ADR-103](../ADR-103-Extensions-Framework.md) |
| **Status** | Draft |
| **Date** | 2026-03-25 |

---

## Overview

The extension registry provides a database-backed system for managing optional Iris integrations. Extensions can be installed, uninstalled, enabled, and disabled by administrators. API endpoints for extensions are gated behind a FastAPI dependency that checks the registry.

## Database Schema

### SQLite Migration (m031)

```sql
CREATE TABLE IF NOT EXISTS extensions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    version TEXT NOT NULL,
    is_enabled INTEGER NOT NULL DEFAULT 1,
    installed_at TEXT NOT NULL,
    installed_by TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    config TEXT DEFAULT '{}'
);
```

### Supabase Migration (m034)

Same schema in PostgreSQL syntax with `BOOLEAN` instead of `INTEGER` for `is_enabled`.

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/extensions` | List all installed extensions |
| GET | `/api/extensions/{id}` | Get a single extension |
| POST | `/api/extensions/{id}/install` | Install an extension (admin only) |
| POST | `/api/extensions/{id}/uninstall` | Uninstall an extension (admin only) |
| POST | `/api/extensions/{id}/enable` | Enable an extension |
| POST | `/api/extensions/{id}/disable` | Disable an extension |

## Backend Module Structure

```
backend/app/extensions/
├── __init__.py
├── models.py      — ExtensionResponse, ExtensionListResponse
├── service.py     — install, uninstall, enable, disable, list, is_enabled
└── router.py      — APIRouter(prefix="/api/extensions")
```

## Service Functions

- `install_extension(db, extension_id, name, description, version, installed_by)` — Insert row, return dict
- `uninstall_extension(db, extension_id)` — Delete row
- `enable_extension(db, extension_id)` — Set is_enabled = 1
- `disable_extension(db, extension_id)` — Set is_enabled = 0
- `get_extension(db, extension_id)` — Fetch single row
- `list_extensions(db)` — Fetch all rows
- `is_extension_enabled(db, extension_id)` — Return bool

## Extension Gating

FastAPI dependency for gating routes:

```python
async def require_extension_enabled(extension_id: str, request: Request):
    db = request.app.state.db_manager.main_db
    if not await is_extension_enabled(db, extension_id):
        raise HTTPException(status_code=404, detail="Extension not available")
```

## Admin UI

- Page at `/admin/extensions` listing all known extensions
- Each extension shows: name, description, version, enabled status, install/uninstall action
- Toggle switch for enable/disable on installed extensions
- "Extensions" link added to admin navigation in AppShell

## Acceptance Criteria

1. Extensions table is created by migration m031
2. All 6 API endpoints work correctly
3. `is_extension_enabled` returns correct state
4. Admin UI lists extensions and supports install/toggle
5. Extension gating blocks requests when extension is disabled or not installed
