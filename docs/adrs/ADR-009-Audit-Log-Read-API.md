# ADR-009: Audit Log Read API

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-009 |
| **Initiative** | Iris Security — Audit Read Access |
| **Proposed By** | Architecture Team |
| **Date** | 2026-02-27 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** building the admin audit page for Iris, which requires reading audit log entries and verifying hash chain integrity through the frontend,

**facing** the fact that the `verify_audit_chain()` function exists in `audit/service.py` but has no HTTP endpoint, and that the audit write path (middleware) is already implemented and unchanged, leaving no read-side API for the admin interface to consume,

**we decided for** exposing read-only audit log endpoints (`GET /api/audit` for paginated, filterable log retrieval and `GET /api/audit/verify` for hash chain verification), restricted to the admin role via the existing `audit.read` permission,

**and neglected** a frontend-only audit display using a different data source (no other source of audit data exists — the hash-chained audit database is the sole record), and exposing audit write operations via API (unnecessary and dangerous — the audit middleware handles all writes as part of the operation transaction, and exposing writes would undermine append-only integrity),

**to achieve** a functional admin audit page that can display, filter, and paginate audit log entries, the ability for administrators to verify audit chain integrity through the UI, and a clean separation where the write path remains middleware-only and the read path is a standard REST API,

**accepting that** the read API adds a new attack surface that must be restricted to admin role only, that paginated queries on large audit logs may require index optimisation over time, and that verification of very long audit chains may be slow (acceptable given admin-only access and infrequent use).

---

## Endpoints

| Endpoint | Method | Permission | Purpose |
|----------|--------|------------|---------|
| `/api/audit` | GET | `audit.read` (Admin only) | Paginated, filterable audit log query |
| `/api/audit/verify` | GET | `audit.read` (Admin only) | Hash chain integrity verification |

The audit log write path (middleware) is unchanged by this ADR.

---

## Options Considered

### Option 1: Read-Only Admin Endpoints (Selected)

**Pros:**
- Minimal scope — only adds read access, write path unchanged
- Uses existing `audit.read` permission from RBAC (SPEC-005-A)
- Enables the admin audit page to function
- Exposes existing `verify_audit_chain()` function that was otherwise unreachable via HTTP
- Standard REST patterns (GET with query parameters, pagination)

**Cons:**
- New endpoints increase API surface area
- Must ensure non-admin roles receive 403 consistently

### Option 2: Frontend-Only Audit Display Using a Different Data Source (Rejected)

**Pros:**
- No new API endpoints

**Cons:**
- No alternative data source exists — the hash-chained audit database is the only record of auditable actions
- Would require inventing a parallel audit mechanism, contradicting ADR-007

**Why rejected:** There is no other source of audit data. The audit database is the single source of truth.

### Option 3: Exposing Audit Writes via API (Rejected)

**Pros:**
- Would allow external systems to write audit entries

**Cons:**
- Undermines append-only integrity — audit writes must occur within the same transaction as the audited operation
- The middleware already handles all writes correctly
- Exposes a dangerous mutation surface for no user-facing benefit

**Why rejected:** Unnecessary and harmful. The middleware write path is the correct and only write mechanism.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-02-27 | Approved | Implement read-only audit endpoints | 6 months | 2026-08-27 |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Architecture Team | 2026-02-27 |
| Approved | Project Lead | 2026-02-27 |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Depends On | ADR-001 | Enhanced ADR Format | This ADR follows the enhanced WH(Y) format |
| Depends On | ADR-007 | Audit Log Integrity | Read API serves data from the hash-chained audit log |
| Depends On | ADR-005 | RBAC Design | `audit.read` permission restricts access to admin role |
| Relates To | ADR-004 | Backend Language and Framework | Endpoints implemented as FastAPI routes |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-009-A | Audit Read API | Technical Specification | [specs/SPEC-009-A-Audit-Read-API.md](specs/SPEC-009-A-Audit-Read-API.md) |
| SPEC-007-A | Audit Log Schema and Hash Chain Implementation | Technical Specification | [specs/SPEC-007-A-Audit-Log-Schema.md](specs/SPEC-007-A-Audit-Log-Schema.md) |
| SPEC-005-A | RBAC Permission Matrix | Technical Specification | [specs/SPEC-005-A-RBAC-Permissions.md](specs/SPEC-005-A-RBAC-Permissions.md) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
