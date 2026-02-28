# ADR-021: Admin Settings and Configurable Session Timeout

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-021 |
| **Initiative** | Admin Settings Page and Configurable Session Timeout |
| **Proposed By** | Architecture Team |
| **Date** | 2026-02-28 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris application where system-wide parameters such as session timeout (hardcoded at 15 minutes in `AuthConfig`) and gallery thumbnail display mode have no admin-facing configuration surface, requiring code changes and redeployment to adjust operational settings,

**facing** the need for administrators to tune system behaviour without developer intervention — particularly session timeout duration which affects security posture and user experience, and gallery thumbnail rendering which affects performance and visual fidelity,

**we decided for** a database-backed settings table with a REST API and an admin settings page:

1. **Settings table:** A new `settings` migration (`m006_settings`) creates a key-value `settings` table with audit metadata (`updated_at`, `updated_by`), seeded with default values on startup.
2. **Settings API:** Three endpoints (`GET /api/settings`, `GET /api/settings/{key}`, `PUT /api/settings/{key}`) with read access for authenticated users and write access restricted to admins.
3. **Dynamic session timeout:** The login endpoint reads `session_timeout_minutes` from the settings table and passes it to `create_access_token()`, overriding the static `AuthConfig` default.
4. **Admin settings page:** A new `/admin/settings` page with form controls for session timeout (number input, 5-480 minute range) and gallery thumbnail mode (SVG/PNG radio buttons).

**and neglected** environment-variable-only configuration (no UI, requires restart), a YAML/JSON config file approach (no audit trail, requires file system access), and per-user settings (unnecessary complexity for system-wide parameters),

**to achieve** runtime configurability of key system parameters by administrators through a web interface, with full audit trail of who changed what and when, without requiring application restarts or code deployments,

**accepting that** this introduces a database lookup on each login to resolve the session timeout, and that the settings key-value model is less type-safe than structured configuration objects.

---

## Options Considered

### Option 1: Database-Backed Settings with Admin UI (Selected)

**Pros:**
- Runtime configurability without restarts
- Audit trail via `updated_at` / `updated_by` columns
- Consistent with existing admin pages (users, audit)
- Extensible — new settings are just new rows

**Cons:**
- Additional DB query on login path
- Key-value model requires string parsing for typed values

**Why selected:** Provides the best admin experience with audit trail and no-restart changes.

### Option 2: Environment Variables Only (Rejected)

**Pros:**
- Simple, no new tables or endpoints
- Follows 12-factor app principles

**Cons:**
- Requires restart to apply changes
- No web UI for administrators
- No audit trail of changes

**Why rejected:** Requires restart and developer access to change operational settings.

### Option 3: Config File on Disk (Rejected)

**Pros:**
- Easy to edit
- No database dependency

**Cons:**
- Requires file system access
- No audit trail
- Race conditions with concurrent edits

**Why rejected:** Requires server access and lacks audit capabilities.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-02-28 | Accepted | Implement settings table, API, and admin page | 6 months | 2026-08-28 |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Architecture Team | 2026-02-28 |
| Accepted | Project Lead | 2026-02-28 |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Depends On | ADR-001 | Enhanced ADR Format | This ADR follows the enhanced WH(Y) format |
| Depends On | ADR-005 | RBAC Design | Admin role required for write access |
| Related To | ADR-009 | Audit Log Read API | Settings changes visible in audit trail |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-021-A | Admin Settings | Technical Specification | [specs/SPEC-021-A-Admin-Settings.md](specs/SPEC-021-A-Admin-Settings.md) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
