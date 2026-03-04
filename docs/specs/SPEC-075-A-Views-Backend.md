# SPEC-075-A: Admin-Configurable Views — Backend

**ADR:** [ADR-075](../adrs/ADR-075-Admin-Configurable-Views.md)
**Status:** Implemented

---

## Overview

Backend implementation of admin-configurable views: database migration, Pydantic models, service layer, and REST API.

## Database Schema (Migration m017)

```sql
CREATE TABLE views (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    config TEXT NOT NULL DEFAULT '{}',
    is_default INTEGER NOT NULL DEFAULT 0,
    created_by TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

## API Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/api/views` | List all views | Required |
| POST | `/api/views` | Create view | Required |
| GET | `/api/views/{id}` | Get single view | Required |
| PUT | `/api/views/{id}` | Update view | Required |
| DELETE | `/api/views/{id}` | Delete view | Required (non-default only) |

## View Config Schema

```json
{
  "toolbar": {
    "element_types": ["component", "service", ...],
    "relationship_types": ["uses", "depends_on", ...],
    "show_routing_type": true,
    "show_edge_properties": true
  },
  "metadata": {
    "show_overview": true,
    "show_details": true,
    "show_extended": false
  },
  "canvas": {
    "show_cardinality": true,
    "show_role_names": true,
    "show_stereotypes": true,
    "show_description_on_nodes": true
  }
}
```

## Default Views

| View | Description | Key Differences |
|------|-------------|-----------------|
| Standard | Simplified for common use | Hides extended metadata, routing, edge properties, cardinality, roles, stereotypes |
| Advanced | Full functionality | Everything visible |

## Service Functions

- `create_view(db, name, description, config, is_default, created_by)` — creates view with UUID
- `list_views(db)` — returns all views, defaults first, then alphabetical
- `get_view(db, view_id)` — returns single view or None
- `update_view(db, view_id, name, description, config)` — updates view, returns None if not found
- `delete_view(db, view_id)` — deletes non-default view, returns False for default/missing
- `seed_default_views(db)` — idempotent seed of Standard and Advanced views

## Files

- `backend/app/migrations/m017_views.py`
- `backend/app/views/__init__.py`
- `backend/app/views/models.py`
- `backend/app/views/service.py`
- `backend/app/views/router.py`
