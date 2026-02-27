# SPEC-007-A: Audit Log Schema and Hash Chain Implementation

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-007-A |
| **ADR Reference** | [ADR-007: Audit Log Integrity](../ADR-007-Audit-Log-Integrity.md) |
| **Date** | 2026-02-27 |
| **Status** | Active |

---

## Overview

This specification defines the audit log schema, hash chain implementation, and verification procedures for Iris's tamper-evident audit system stored in a separate SQLite database file.

---

## Database Configuration

| Setting | Value |
|---------|-------|
| **File** | `data/iris_audit.db` |
| **Separate from** | `data/iris.db` (application database) |
| **WAL Mode** | Enabled (PRAGMA journal_mode=WAL) |
| **Foreign Keys** | Not applicable (no FK references to application DB) |

---

## Schema

```sql
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,              -- ISO 8601 UTC
    user_id TEXT NOT NULL,                -- User who performed the action
    username TEXT NOT NULL,               -- Username at time of action (denormalised for independence)
    action TEXT NOT NULL,                 -- Action identifier (see Auditable Actions)
    target_type TEXT NOT NULL,            -- 'entity' | 'model' | 'relationship' | 'user' | 'role' | 'system' | 'comment' | 'search'
    target_id TEXT,                       -- ID of affected object (NULL for system-level actions)
    detail TEXT,                          -- JSON with action-specific detail
    ip_address TEXT,                      -- Client IP address
    session_id TEXT,                      -- JWT token ID (jti claim)
    previous_hash TEXT NOT NULL,          -- SHA-256 hash of the previous entry
    entry_hash TEXT NOT NULL              -- SHA-256 hash of this entry
);

CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp);
CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_target ON audit_log(target_type, target_id);
```

---

## Hash Chain Implementation

### Genesis Entry

The first entry in the audit log uses a known genesis hash:

```python
GENESIS_HASH = hashlib.sha256(b"IRIS_AUDIT_GENESIS").hexdigest()
# = "a1b2c3..."  (deterministic, reproducible)
```

### Hash Computation

For each new entry:

```python
import hashlib
import json

def compute_entry_hash(entry: dict, previous_hash: str) -> str:
    """Compute SHA-256 hash for an audit log entry."""
    payload = "|".join([
        str(entry["id"]),
        entry["timestamp"],
        entry["user_id"],
        entry["username"],
        entry["action"],
        entry["target_type"],
        entry.get("target_id") or "",
        entry.get("detail") or "",
        entry.get("ip_address") or "",
        entry.get("session_id") or "",
        previous_hash,
    ])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
```

### Write Protocol

```python
async def write_audit_entry(
    db: aiosqlite.Connection,
    user_id: str,
    username: str,
    action: str,
    target_type: str,
    target_id: str | None,
    detail: dict | None,
    ip_address: str | None,
    session_id: str | None,
) -> None:
    """Write a hash-chained audit log entry. Must be called within a transaction."""

    # 1. Get the previous entry's hash (or genesis hash)
    cursor = await db.execute(
        "SELECT entry_hash FROM audit_log ORDER BY id DESC LIMIT 1"
    )
    row = await cursor.fetchone()
    previous_hash = row[0] if row else GENESIS_HASH

    # 2. Get next ID
    cursor = await db.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM audit_log")
    next_id = (await cursor.fetchone())[0]

    # 3. Build entry
    timestamp = datetime.utcnow().isoformat() + "Z"
    detail_json = json.dumps(detail) if detail else None

    entry = {
        "id": next_id,
        "timestamp": timestamp,
        "user_id": user_id,
        "username": username,
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "detail": detail_json,
        "ip_address": ip_address,
        "session_id": session_id,
    }

    # 4. Compute hash
    entry_hash = compute_entry_hash(entry, previous_hash)

    # 5. Insert
    await db.execute(
        """INSERT INTO audit_log
           (id, timestamp, user_id, username, action, target_type, target_id,
            detail, ip_address, session_id, previous_hash, entry_hash)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (next_id, timestamp, user_id, username, action, target_type,
         target_id, detail_json, ip_address, session_id, previous_hash, entry_hash)
    )
```

---

## Auditable Actions

| Action | Target Type | Detail Content |
|--------|-------------|----------------|
| `entity.create` | entity | `{ "entity_type": "...", "name": "...", "version": 1 }` |
| `entity.update` | entity | `{ "version": N, "change_summary": "..." }` |
| `entity.delete` | entity | `{ "version": N }` |
| `entity.rollback` | entity | `{ "from_version": N, "to_version": M, "new_version": K }` |
| `model.create` | model | `{ "name": "...", "model_type": "..." }` |
| `model.update` | model | `{ "changed_fields": [...] }` |
| `model.delete` | model | `{ "name": "..." }` |
| `relationship.create` | relationship | `{ "source_id": "...", "target_id": "...", "type": "..." }` |
| `relationship.delete` | relationship | `{ "source_id": "...", "target_id": "...", "type": "..." }` |
| `auth.login` | user | `{ "success": true }` |
| `auth.login_failed` | user | `{ "reason": "invalid_credentials" }` |
| `auth.logout` | user | `{}` |
| `auth.password_change` | user | `{}` |
| `auth.role_change` | user | `{ "old_role": "...", "new_role": "..." }` |
| `auth.permission_denied` | system | `{ "attempted_action": "...", "target": "..." }` |
| `user.create` | user | `{ "username": "...", "role": "..." }` |
| `user.update` | user | `{ "changed_fields": [...] }` |
| `user.deactivate` | user | `{}` |
| `system.config_change` | system | `{ "key": "...", "old_value": "...", "new_value": "..." }` |
| `system.audit_verify` | system | `{ "result": "pass" | "fail", "entries_checked": N }` |
| `comment.create` | comment | `{ "target_type": "...", "target_id": "..." }` |
| `comment.delete` | comment | `{ "target_type": "...", "target_id": "..." }` |
| `search.execute` | search | `{ "query": "..." }` |

---

## Verification

### Verify Audit Chain

```python
async def verify_audit_chain(db: aiosqlite.Connection) -> tuple[bool, int]:
    """Verify the audit log hash chain. Returns (is_valid, entries_checked)."""

    cursor = await db.execute("SELECT * FROM audit_log ORDER BY id ASC")
    rows = await cursor.fetchall()

    if not rows:
        return True, 0

    expected_previous = GENESIS_HASH

    for row in rows:
        entry = dict(row)

        # Check previous_hash matches expected
        if entry["previous_hash"] != expected_previous:
            return False, entry["id"]

        # Recompute entry_hash
        computed = compute_entry_hash(entry, entry["previous_hash"])
        if computed != entry["entry_hash"]:
            return False, entry["id"]

        expected_previous = entry["entry_hash"]

    return True, len(rows)
```

### Verification Schedule

| Trigger | Action |
|---------|--------|
| Application startup | Verify last 100 entries |
| Daily scheduled task | Full chain verification |
| Admin request | Full chain verification via API |
| After backup restore | Full chain verification |

Verification results are themselves logged to the audit log (`system.audit_verify`).

---

## API

### Query Audit Log (Admin Only)

```
GET /api/audit?action=entity.update&user_id=abc&from=2026-01-01&to=2026-02-28&limit=50&offset=0
```

Requires `audit.read` permission.

### Verify Audit Chain (Admin Only)

```
POST /api/audit/verify
Response: { "valid": true, "entries_checked": 1234, "verified_at": "..." }
```

---

## Backup Procedures

Both database files must be backed up together:

```bash
# Backup both databases atomically
sqlite3 data/iris.db ".backup 'backup/iris_$(date +%Y%m%d).db'"
sqlite3 data/iris_audit.db ".backup 'backup/iris_audit_$(date +%Y%m%d).db'"
```

The audit database backup should include verification of the hash chain before and after backup.

---

*This specification implements [ADR-007](../ADR-007-Audit-Log-Integrity.md).*
