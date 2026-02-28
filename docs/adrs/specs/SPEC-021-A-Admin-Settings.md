# SPEC-021-A: Admin Settings

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-021-A |
| **ADR Reference** | [ADR-021: Admin Settings and Configurable Session Timeout](../ADR-021-Admin-Settings-and-Configurable-Session-Timeout.md) |
| **Date** | 2026-02-28 |
| **Status** | Active |

---

## Overview

This specification defines the settings storage, API endpoints, dynamic session timeout integration, and admin settings page for configuring system-wide parameters at runtime.

---

## Database Schema

### Settings Table (Migration m006)

```sql
CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT,
  updated_by TEXT
);
```

### Default Settings (Seeded on Startup)

| Key | Default Value | Description |
|-----|---------------|-------------|
| `session_timeout_minutes` | `15` | JWT access token expiry in minutes (range: 5-480) |
| `gallery_thumbnail_mode` | `svg` | Model thumbnail rendering mode (`svg` or `png`) |

---

## Access Control

| Rule | Detail |
|------|--------|
| **Read** | Any authenticated user (`get_current_user`) |
| **Write** | Admin role only (`require_admin` check) |
| **Unauthenticated** | `401 Unauthorized` |
| **Non-Admin Write** | `403 Forbidden` with `{ "detail": "Admin access required" }` |

---

## API Endpoints

### GET /api/settings

Retrieve all settings.

#### Response Schema

```json
[
  {
    "key": "session_timeout_minutes",
    "value": "15",
    "updated_at": null,
    "updated_by": null
  },
  {
    "key": "gallery_thumbnail_mode",
    "value": "svg",
    "updated_at": null,
    "updated_by": null
  }
]
```

### GET /api/settings/{key}

Retrieve a single setting by key.

#### Response Schema

```json
{
  "key": "session_timeout_minutes",
  "value": "15",
  "updated_at": "2026-02-28T10:00:00+00:00",
  "updated_by": "uuid-admin-123"
}
```

#### Error Responses

| Status | Condition |
|--------|-----------|
| `404` | Setting key does not exist |

### PUT /api/settings/{key}

Update a setting value. Admin only.

#### Request Body

```json
{
  "value": "30"
}
```

#### Response Schema

Returns the updated setting (same schema as GET).

#### Error Responses

| Status | Condition |
|--------|-----------|
| `403` | User is not admin |
| `404` | Setting key does not exist |

---

## Dynamic Session Timeout

The login endpoint (`POST /api/auth/login`) reads the `session_timeout_minutes` setting from the database and uses it as the JWT expiry duration, overriding the static `AuthConfig.access_token_expire_minutes` default.

The refresh endpoint (`POST /api/auth/refresh`) also reads the setting to ensure refreshed tokens use the current timeout value.

### Flow

1. User submits login credentials
2. Credentials validated against database
3. `session_timeout_minutes` fetched from settings table
4. `create_access_token()` called with `timeout_minutes` override
5. Token issued with dynamic expiry

### Fallback

If the settings table query fails or returns a non-numeric value, the system falls back to `config.auth.access_token_expire_minutes` (15 minutes).

---

## Frontend: Admin Settings Page

### Route

`/admin/settings`

### Navigation

A "Settings" card is added to the admin home page (`/admin`) alongside the existing "User Management" and "Audit Log" cards.

### UI Components

| Component | Type | Details |
|-----------|------|---------|
| Session Timeout | Number input | Min 5, max 480 minutes |
| Gallery Thumbnails | Radio group | SVG (inline) or PNG (server-generated) |
| Save button | Button | Saves all settings via PUT requests |

### Behaviour

- Page loads all settings on mount via `GET /api/settings`
- Form fields populated from setting values
- Save button sends individual `PUT /api/settings/{key}` for each changed setting
- Success/error messages displayed via alert roles
- Input sanitised with DOMPurify before sending

### Breadcrumb

`Admin / Settings`

---

## Startup Integration

1. Migration `m006_settings` runs after `m005_search` during startup
2. `seed_defaults()` called after `seed_roles_and_permissions()` to populate default values (uses `INSERT OR IGNORE` for idempotency)

---

## File Inventory

| File | Purpose |
|------|---------|
| `backend/app/migrations/m006_settings.py` | Settings table migration |
| `backend/app/settings/__init__.py` | Package marker |
| `backend/app/settings/models.py` | Pydantic request/response models |
| `backend/app/settings/service.py` | Settings CRUD + seed logic |
| `backend/app/settings/router.py` | API route handlers |
| `frontend/src/routes/admin/settings/+page.svelte` | Admin settings page |
