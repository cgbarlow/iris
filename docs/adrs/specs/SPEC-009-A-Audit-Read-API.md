# SPEC-009-A: Audit Read API

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-009-A |
| **ADR Reference** | [ADR-009: Audit Log Read API](../ADR-009-Audit-Log-Read-API.md) |
| **Date** | 2026-02-27 |
| **Status** | Active |

---

## Overview

This specification defines the read-only audit log API endpoints that enable the admin audit page to display, filter, and paginate audit log entries and to verify the hash chain integrity. The audit write path (middleware) is unchanged.

---

## Access Control

| Rule | Detail |
|------|--------|
| **Required Permission** | `audit.read` |
| **Roles with Permission** | Admin only (per SPEC-005-A) |
| **Non-Admin Response** | `403 Forbidden` with body `{ "detail": "Insufficient permissions" }` |
| **Unauthenticated Response** | `401 Unauthorized` |

All endpoints in this specification require the `audit.read` permission. Non-admin users (Architect, Reviewer, Viewer) receive a 403 response.

---

## Endpoints

### GET /api/audit

Retrieve paginated, filterable audit log entries.

#### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `action` | string | No | — | Filter by action (e.g., `entity.create`, `auth.login`) |
| `username` | string | No | — | Filter by username |
| `target_type` | string | No | — | Filter by target type (e.g., `entity`, `model`, `user`, `system`) |
| `from_date` | string (ISO 8601) | No | — | Filter entries from this date (inclusive) |
| `to_date` | string (ISO 8601) | No | — | Filter entries up to this date (inclusive) |
| `page` | integer | No | 1 | Page number (1-indexed) |
| `page_size` | integer | No | 50 | Number of entries per page (max 100) |

#### Request Example

```
GET /api/audit?action=entity.update&username=admin&from_date=2026-01-01T00:00:00Z&to_date=2026-02-28T23:59:59Z&page=1&page_size=25
Authorization: Bearer <admin-jwt-token>
```

#### Response Schema

```json
{
  "items": [
    {
      "id": 42,
      "timestamp": "2026-02-15T10:30:00Z",
      "user_id": "uuid-abc-123",
      "username": "admin",
      "action": "entity.update",
      "target_type": "entity",
      "target_id": "uuid-entity-456",
      "detail": { "version": 3, "change_summary": "Updated description" },
      "ip_address": "192.168.1.10",
      "session_id": "jti-xyz-789"
    }
  ],
  "total": 148,
  "page": 1,
  "page_size": 25
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `items` | AuditEntry[] | Array of audit log entries for the current page |
| `total` | integer | Total number of entries matching the filters |
| `page` | integer | Current page number |
| `page_size` | integer | Number of entries per page |

#### AuditEntry Schema

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | integer | No | Auto-incrementing entry ID |
| `timestamp` | string (ISO 8601) | No | UTC timestamp of the action |
| `user_id` | string | No | ID of the user who performed the action |
| `username` | string | No | Username at time of action (denormalised) |
| `action` | string | No | Action identifier (see SPEC-007-A Auditable Actions) |
| `target_type` | string | No | Type of the affected object |
| `target_id` | string | Yes | ID of the affected object (null for system-level actions) |
| `detail` | object | Yes | JSON object with action-specific detail |
| `ip_address` | string | Yes | Client IP address |
| `session_id` | string | Yes | JWT token ID (jti claim) |

Note: The `previous_hash` and `entry_hash` fields are not exposed in the API response. They are internal to the hash chain implementation and are only used by the verification endpoint.

#### Pagination Behaviour

- Pages are 1-indexed. Requesting `page=0` returns a `422 Unprocessable Entity`.
- `page_size` is clamped to a maximum of 100. Values above 100 are reduced to 100.
- `page_size` minimum is 1. Values below 1 return a `422 Unprocessable Entity`.
- Requesting a page beyond the last page returns an empty `items` array with the correct `total`.
- Results are ordered by `id` descending (most recent entries first).

#### HTTP Status Codes

| Status | Condition |
|--------|-----------|
| `200 OK` | Successful query |
| `401 Unauthorized` | No valid authentication token |
| `403 Forbidden` | Authenticated but lacks `audit.read` permission |
| `422 Unprocessable Entity` | Invalid query parameters |

---

### GET /api/audit/verify

Verify the integrity of the audit log hash chain.

#### Request Example

```
GET /api/audit/verify
Authorization: Bearer <admin-jwt-token>
```

#### Response Schema

```json
{
  "valid": true,
  "entries_checked": 1234,
  "verified_at": "2026-02-27T14:30:00Z"
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `valid` | boolean | `true` if the entire hash chain is intact, `false` if tampering is detected |
| `entries_checked` | integer | Number of audit log entries verified |
| `verified_at` | string (ISO 8601) | UTC timestamp of when the verification was performed |

#### Verification Behaviour

- Calls the existing `verify_audit_chain()` function from `audit/service.py`.
- Scans all entries sequentially, recomputing hashes and verifying the chain (see SPEC-007-A).
- On success, logs a `system.audit_verify` entry to the audit log with `{ "result": "pass", "entries_checked": N }`.
- On failure, logs a `system.audit_verify` entry with `{ "result": "fail", "entries_checked": N }` where N is the ID of the first mismatching entry.
- Verification may be slow on very large audit logs. This is acceptable given admin-only access and infrequent use.

#### HTTP Status Codes

| Status | Condition |
|--------|-----------|
| `200 OK` | Verification completed (check `valid` field for result) |
| `401 Unauthorized` | No valid authentication token |
| `403 Forbidden` | Authenticated but lacks `audit.read` permission |

---

## Implementation Notes

### Route Registration

```python
from fastapi import APIRouter, Depends, Query
from app.auth.dependencies import require_permission

router = APIRouter(prefix="/api/audit", tags=["audit"])

@router.get("")
async def get_audit_log(
    action: str | None = None,
    username: str | None = None,
    target_type: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    user=Depends(require_permission("audit.read")),
):
    ...

@router.get("/verify")
async def verify_audit(
    user=Depends(require_permission("audit.read")),
):
    ...
```

### Filter Construction

Filters are combined with AND logic. If no filters are provided, all entries are returned (paginated). Date filters use `>=` and `<=` comparison on the ISO 8601 `timestamp` field.

---

*This specification implements [ADR-009](../ADR-009-Audit-Log-Read-API.md).*
