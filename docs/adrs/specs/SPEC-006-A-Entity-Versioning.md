# SPEC-006-A: Entity Version Control Schema

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-006-A |
| **ADR Reference** | [ADR-006: Version Control and Rollback Semantics](../ADR-006-Version-Control-Rollback-Semantics.md) |
| **Date** | 2026-02-27 |
| **Status** | Active |

---

## Overview

This specification defines the entity versioning schema and implementation for Iris's immutable append-only version control system with revert-as-new-version rollback semantics.

---

## Schema

### Entity Identity Table

```sql
CREATE TABLE entities (
    id TEXT PRIMARY KEY,                -- UUID, stable identity
    entity_type TEXT NOT NULL,          -- 'component', 'service', 'interface', 'actor', etc.
    current_version INTEGER NOT NULL,   -- Points to latest version number
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    created_by TEXT NOT NULL REFERENCES users(id),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),  -- Updated on every version change
    is_deleted INTEGER NOT NULL DEFAULT 0  -- Soft delete flag
);

CREATE INDEX idx_entities_type ON entities(entity_type);
CREATE INDEX idx_entities_created_by ON entities(created_by);
```

### Entity Versions Table

```sql
CREATE TABLE entity_versions (
    entity_id TEXT NOT NULL REFERENCES entities(id),
    version INTEGER NOT NULL,           -- Monotonically increasing per entity
    name TEXT NOT NULL,                 -- Entity display name at this version
    description TEXT,                   -- Entity description at this version
    data TEXT NOT NULL,                 -- JSON blob of entity-type-specific state
    metadata TEXT,                      -- JSON blob of user-defined metadata
    change_type TEXT NOT NULL CHECK (change_type IN ('create', 'update', 'rollback', 'delete')),
    change_summary TEXT,               -- Human-readable description of what changed
    rollback_to INTEGER,               -- If change_type='rollback', the source version
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    created_by TEXT NOT NULL REFERENCES users(id),
    PRIMARY KEY (entity_id, version)
);

CREATE INDEX idx_entity_versions_created_at ON entity_versions(created_at);
CREATE INDEX idx_entity_versions_created_by ON entity_versions(created_by);
```

---

## Operations

### Create Entity

```sql
-- 1. Insert entity identity
INSERT INTO entities (id, entity_type, current_version, created_by)
VALUES (:id, :entity_type, 1, :user_id);

-- 2. Insert first version
INSERT INTO entity_versions (entity_id, version, name, description, data, metadata, change_type, created_by)
VALUES (:id, 1, :name, :description, :data, :metadata, 'create', :user_id);
```

Both operations in a single transaction.

### Update Entity

```sql
-- 1. Check optimistic concurrency
SELECT current_version FROM entities WHERE id = :id;
-- If current_version != expected_version → HTTP 409 Conflict

-- 2. Insert new version
INSERT INTO entity_versions (entity_id, version, name, description, data, metadata, change_type, change_summary, created_by)
VALUES (:id, :current_version + 1, :name, :description, :data, :metadata, 'update', :summary, :user_id);

-- 3. Update current version pointer
UPDATE entities SET current_version = :current_version + 1, updated_at = datetime('now')
WHERE id = :id;
```

All operations in a single transaction.

### Rollback Entity (Admin Only)

```sql
-- 1. Read target version's state
SELECT name, description, data, metadata FROM entity_versions
WHERE entity_id = :id AND version = :target_version;

-- 2. Get current version number
SELECT current_version FROM entities WHERE id = :id;

-- 3. Insert rollback version (content matches target version)
INSERT INTO entity_versions (entity_id, version, name, description, data, metadata, change_type, rollback_to, change_summary, created_by)
VALUES (:id, :current_version + 1, :target_name, :target_description, :target_data, :target_metadata, 'rollback', :target_version, 'Rolled back to version ' || :target_version, :user_id);

-- 4. Update current version pointer
UPDATE entities SET current_version = :current_version + 1
WHERE id = :id;
```

All operations in a single transaction. Requires `version.rollback` permission.

### Soft Delete Entity (Admin Only)

```sql
-- 1. Insert delete version (marks the deletion in history)
INSERT INTO entity_versions (entity_id, version, name, description, data, metadata, change_type, change_summary, created_by)
VALUES (:id, :current_version + 1, :current_name, :current_description, :current_data, :current_metadata, 'delete', 'Entity deleted', :user_id);

-- 2. Mark entity as soft-deleted
UPDATE entities SET is_deleted = 1, current_version = :current_version + 1
WHERE id = :id;
```

Soft-deleted entities are excluded from normal queries but remain in the database for audit purposes. They can be restored via rollback to a pre-delete version.

---

## Version History API

### Get Entity Version History

```
GET /api/entities/:id/versions
Response: [
    { version: 6, change_type: "rollback", rollback_to: 3, created_at: "...", created_by: "..." },
    { version: 5, change_type: "update", change_summary: "Updated dependencies", ... },
    { version: 4, change_type: "update", change_summary: "Changed hosting", ... },
    { version: 3, change_type: "update", change_summary: "Added security config", ... },
    { version: 2, change_type: "update", change_summary: "Added endpoints", ... },
    { version: 1, change_type: "create", change_summary: null, ... }
]
```

### Get Entity at Specific Version

```
GET /api/entities/:id/versions/:version
Response: { entity_id, version, name, description, data, metadata, change_type, ... }
```

### Compare Versions (Diff)

```
GET /api/entities/:id/diff?from=3&to=5
Response: { from: { version: 3, ... }, to: { version: 5, ... }, changes: [...] }
```

The diff is computed at the API layer by comparing the JSON `data` fields.

---

## Optimistic Concurrency Control

Every write operation includes the expected current version:

```
PUT /api/entities/:id
Header: If-Match: "5"      -- Expected current version
Body: { name: "...", ... }

If entity.current_version == 5 → proceed, create version 6
If entity.current_version != 5 → HTTP 409 Conflict
```

The client must re-read the entity and re-apply changes on conflict.

---

## Storage Considerations

| Metric | Estimate |
|--------|----------|
| Average entity versions | 10-50 per entity over project lifetime |
| Average version size | 1-5 KB (JSON metadata) |
| Entities per enterprise model | 500-5,000 |
| Total version storage | 25 MB - 1.25 GB for a mature enterprise model |

Storage growth is linear and predictable. SQLite handles this comfortably.

---

*This specification implements [ADR-006](../ADR-006-Version-Control-Rollback-Semantics.md).*
