# ADR-007: Audit Log Integrity

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-007 |
| **Initiative** | Iris Security — Audit and Accountability |
| **Proposed By** | The CISO (Cat) |
| **Date** | 2026-02-27 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** designing the audit logging system for Iris, which must provide tamper-evident records of all state-changing operations for NZ ITSM compliance and enterprise governance requirements,

**facing** the choice between storing audit logs in the same SQLite database as application data (simple but co-located), storing audit logs in a separate SQLite database file (isolated but two files to manage), or implementing hash-chained logs within the main database (tamper-evident without file separation),

**we decided for** hash-chained audit logs stored in a separate SQLite database file, combining both isolation and tamper evidence — each log entry includes a SHA-256 hash of the previous entry, creating a verifiable chain, and the audit database is a separate file from the application database,

**and neglected** co-located audit logs without hash chaining (which provides no tamper evidence — a compromised database means compromised audit logs), co-located hash-chained logs (which provides tamper evidence but not isolation — a database restore or corruption affects both data and audit), and external logging services (which adds infrastructure dependency disproportionate to current scope),

**to achieve** tamper-evident audit records that can be independently verified, isolation of audit data from application data so that database operations (backup, restore, migration) do not inadvertently affect audit integrity, compliance with NZ ITSM audit and accountability requirements, and a foundation for future log analysis and incident investigation,

**accepting that** managing two SQLite database files adds operational complexity, that hash chain verification requires sequential scanning (acceptable for audit review cadence), and that the separate audit database must be included in backup procedures alongside the main database.

---

## Audit Log Design

### Hash Chain Structure

Each audit log entry includes a hash of the previous entry's hash, creating a tamper-evident chain:

```
audit_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT NOT NULL,       -- ISO 8601 UTC
    user_id         TEXT NOT NULL,       -- Who performed the action
    action          TEXT NOT NULL,       -- 'entity.create' | 'entity.update' | 'entity.delete' | etc.
    target_type     TEXT NOT NULL,       -- 'entity' | 'model' | 'relationship' | 'user' | 'role'
    target_id       TEXT NOT NULL,       -- ID of the affected object
    detail          TEXT,                -- JSON with action-specific detail (old/new values, metadata)
    ip_address      TEXT,                -- Client IP address
    session_id      TEXT,                -- Session identifier
    previous_hash   TEXT NOT NULL,       -- SHA-256 hash of the previous log entry
    entry_hash      TEXT NOT NULL        -- SHA-256 hash of this entry (computed from all fields above + previous_hash)
)
```

### Hash Computation

For each new log entry:

```
entry_hash = SHA-256(
    id || timestamp || user_id || action || target_type || target_id ||
    detail || ip_address || session_id || previous_hash
)
```

The first entry in the chain uses a known genesis hash (e.g., SHA-256 of "IRIS_AUDIT_GENESIS").

### Verification

To verify the audit chain has not been tampered with:

1. Read all entries in order by ID
2. For each entry, recompute `entry_hash` from its fields and `previous_hash`
3. Verify the computed hash matches the stored `entry_hash`
4. Verify each entry's `previous_hash` matches the previous entry's `entry_hash`

If any hash doesn't match, the chain has been tampered with. The first mismatching entry indicates where tampering occurred.

### Auditable Actions

| Action Category | Specific Actions | Detail Content |
|----------------|------------------|----------------|
| **Entity operations** | `entity.create`, `entity.update`, `entity.delete`, `entity.rollback` | Entity ID, version, change summary |
| **Model operations** | `model.create`, `model.update`, `model.delete` | Model ID, metadata changes |
| **Relationship operations** | `relationship.create`, `relationship.delete` | Source entity, target entity, relationship type |
| **Authentication** | `auth.login`, `auth.logout`, `auth.login_failed`, `auth.password_change` | Username, success/failure reason |
| **Authorisation** | `auth.role_change`, `auth.permission_denied` | User ID, old role, new role |
| **User management** | `user.create`, `user.update`, `user.deactivate` | User ID, changed fields |
| **System** | `system.config_change`, `system.backup`, `system.audit_verify` | Configuration key, old/new value |
| **Comments** | `comment.create`, `comment.delete` | Comment ID, target entity/model |
| **Search** | `search.execute` | Query text (for security audit purposes) |

### API Layer Constraints

The audit log API enforces append-only semantics:

- **INSERT only.** No UPDATE or DELETE operations are exposed at the API layer.
- **No direct database access.** All audit writes go through a dedicated audit service that computes the hash chain.
- **Synchronous logging.** Audit entries are written in the same transaction as the operation they record. If the audit write fails, the operation fails.
- **Read access is Admin-only.** Only users with `audit.read` permission can query the audit log.

### Separate Database Configuration

The audit database is configured as a separate SQLite file:

```
data/
  iris.db           -- Application database (entities, models, relationships, users)
  iris_audit.db     -- Audit database (audit_log table only)
```

Both files must be included in backup procedures. The application opens both database connections at startup.

---

## Options Considered

### Option 1: Hash-Chained Logs in Separate Database (Selected)

**Pros:**
- Tamper evidence through hash chaining — any modification breaks the chain
- Isolation — database operations on application data don't affect audit logs
- Independent backup and retention policies for audit data
- Verification is straightforward sequential scan
- Meets NZ ITSM audit integrity requirements

**Cons:**
- Two database files to manage, backup, and monitor
- Hash chain verification requires sequential scan (O(n))
- Slight write overhead for hash computation (negligible for audit cadence)

### Option 2: Co-located Logs Without Hash Chaining (Rejected)

**Pros:**
- Simplest implementation — single database file
- No hash computation overhead

**Cons:**
- No tamper evidence — anyone with database access can modify logs
- Database restore overwrites audit history
- Does not meet NZ ITSM requirements for audit integrity

**Why rejected:** Fails the fundamental requirement of tamper evidence.

### Option 3: Co-located Hash-Chained Logs (Rejected)

**Pros:**
- Tamper evidence through hash chaining
- Single database file

**Cons:**
- Database backup/restore affects both data and audit logs
- A corrupted database loses both application data and audit trail
- No independent retention policy for audit data

**Why rejected:** Isolation is worth the operational complexity of a second file. Audit logs should survive application database operations.

### Option 4: External Logging Service (Rejected)

**Pros:**
- Professional-grade log management
- Built-in tamper evidence, retention, search
- Scales independently

**Cons:**
- Adds external infrastructure dependency
- Network latency on every auditable operation
- Cost and complexity disproportionate to current scope
- Contradicts the self-contained SQLite architecture

**Why rejected:** Over-engineered for current requirements. The hash-chained separate database provides equivalent integrity guarantees for the expected log volume.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-02-27 | Approved | Implement hash-chained audit logs in Phase A schema | 6 months | 2026-08-27 |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | The CISO (Cat) | 2026-02-27 |
| Approved | Project Lead | 2026-02-27 |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Depends On | ADR-001 | Enhanced ADR Format | This ADR follows the enhanced WH(Y) format |
| Depends On | ADR-003 | Architectural Vision | Audit trail is part of The Foundation layer |
| Depends On | ADR-004 | Backend Language and Framework | FastAPI middleware implements audit logging |
| Relates To | ADR-005 | RBAC Design | audit.read permission controls access to logs |
| Relates To | ADR-006 | Version Control Rollback Semantics | Version history and audit logs are complementary records |
| Relates To | TBD | NZ ITSM Control Mapping | Addresses audit and accountability controls |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-007-A | Audit Log Schema and Hash Chain Implementation | Technical Specification | specs/SPEC-007-A-Audit-Log-Schema.md (TBD) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
