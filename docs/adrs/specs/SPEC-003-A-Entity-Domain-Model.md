# SPEC-003-A: Entity Domain Model

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-003-A |
| **ADR Reference** | [ADR-003: Architectural Vision — Repository First](../ADR-003-Architectural-Vision.md) |
| **Date** | 2026-02-27 |
| **Status** | Active |

---

## Overview

This specification defines the complete domain model for the Iris repository: entity types, relationships, models, and the junction between models and entities. It is the centrepiece of the repository-first architecture (ADR-003) and the prerequisite for all Phase A data foundation work.

The Iris repository contains three categories of first-class objects:

1. **Entities** — the atoms of truth (schema defined in [SPEC-006-A](./SPEC-006-A-Entity-Versioning.md))
2. **Relationships** — the typed bonds between entities
3. **Models** — the views that project entities and relationships onto a canvas

All three are versioned using the same immutable append-only pattern with revert-as-new-version rollback semantics (ADR-006).

---

## Entity Type Taxonomy

Entity types are organised in two tiers corresponding to the two editing views:

### Simple View Types

Available in Simple View (component + sequence diagrams) and Full View.

| Type Key | Display Name | Description | Applicable Diagrams |
|----------|-------------|-------------|-------------------|
| `component` | Component | A modular unit of software with defined interfaces | Component |
| `service` | Service | A deployed or logical service boundary | Component |
| `interface` | Interface | A contract or API surface | Component |
| `package` | Package | A grouping/namespace container | Component |
| `actor` | Actor | A person or external system that interacts with the system | Sequence, Component |
| `database` | Database | A persistent data store | Component |
| `queue` | Queue | An asynchronous message channel | Component |

### Full View Types — UML

Available only in Full View.

| Type Key | Display Name | Description | Applicable Diagrams |
|----------|-------------|-------------|-------------------|
| `class` | Class | A UML class with attributes and operations | Class |
| `object` | Object | An instance of a class | Object |
| `use_case` | Use Case | A user goal or system function | Use Case |
| `state` | State | A condition during the life of an object | State |
| `activity` | Activity | An action or step in a workflow | Activity |
| `node` | Node | A computational resource (deployment target) | Deployment |

### Full View Types — ArchiMate

Available only in Full View.

| Type Key | Display Name | Layer | Description |
|----------|-------------|-------|-------------|
| `business_actor` | Business Actor | Business | A person or organisational unit |
| `business_role` | Business Role | Business | A responsibility assigned to an actor |
| `business_process` | Business Process | Business | A sequence of business behaviours |
| `business_service` | Business Service | Business | An externally visible unit of business functionality |
| `business_object` | Business Object | Business | A concept relevant to the business domain |
| `application_component` | Application Component | Application | A modular, deployable unit of application functionality |
| `application_service` | Application Service | Application | An externally visible unit of application functionality |
| `application_interface` | Application Interface | Application | A point of access to application services |
| `technology_node` | Technology Node | Technology | A computational or physical resource |
| `technology_service` | Technology Service | Technology | An externally visible unit of technology functionality |
| `technology_interface` | Technology Interface | Technology | A point of access to technology services |

### View Mapping

| View | Available Entity Types |
|------|----------------------|
| Simple View | All Simple View types |
| Full View | All Simple View types + UML types + ArchiMate types |
| Browse Mode | All types (read-only) |

### Extensibility

The entity type taxonomy is validated in **application code**, not in database constraints. The `entities.entity_type` TEXT column accepts any string. Type-specific data (attributes, ports, operations) is stored in the `entity_versions.data` JSON blob. Adding new entity types requires no schema migration — only an update to the application-level type registry.

---

## Relationship Schema

Relationships are first-class repository objects connecting a source entity to a target entity with a typed bond. They follow the same versioning pattern as entities (SPEC-006-A).

### Relationship Identity Table

```sql
CREATE TABLE relationships (
    id TEXT PRIMARY KEY,                    -- UUID, stable identity
    source_entity_id TEXT NOT NULL REFERENCES entities(id),
    target_entity_id TEXT NOT NULL REFERENCES entities(id),
    relationship_type TEXT NOT NULL,        -- See Relationship Type Taxonomy
    current_version INTEGER NOT NULL,       -- Points to latest version number
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    created_by TEXT NOT NULL REFERENCES users(id),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),  -- Updated on every version change
    is_deleted INTEGER NOT NULL DEFAULT 0   -- Soft delete flag
);

CREATE INDEX idx_relationships_source ON relationships(source_entity_id);
CREATE INDEX idx_relationships_target ON relationships(target_entity_id);
CREATE INDEX idx_relationships_type ON relationships(relationship_type);
CREATE INDEX idx_relationships_created_by ON relationships(created_by);
```

### Relationship Versions Table

```sql
CREATE TABLE relationship_versions (
    relationship_id TEXT NOT NULL REFERENCES relationships(id),
    version INTEGER NOT NULL,               -- Monotonically increasing per relationship
    label TEXT,                             -- Optional display label for the relationship
    description TEXT,                       -- Description of this relationship at this version
    data TEXT,                              -- JSON blob of relationship-type-specific state
    metadata TEXT,                          -- JSON blob of user-defined metadata
    change_type TEXT NOT NULL CHECK (change_type IN ('create', 'update', 'rollback', 'delete')),
    change_summary TEXT,                    -- Human-readable description of what changed
    rollback_to INTEGER,                    -- If change_type='rollback', the source version
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    created_by TEXT NOT NULL REFERENCES users(id),
    PRIMARY KEY (relationship_id, version)
);

CREATE INDEX idx_relationship_versions_created_at ON relationship_versions(created_at);
CREATE INDEX idx_relationship_versions_created_by ON relationship_versions(created_by);
```

### Relationship Type Taxonomy

#### Simple View Relationship Types

| Type Key | Display Name | Description | Notation |
|----------|-------------|-------------|----------|
| `uses` | Uses | Source uses/depends on target | Dashed arrow |
| `depends_on` | Depends On | Source depends on target | Dashed arrow |
| `composes` | Composes | Source is composed of target | Filled diamond |
| `implements` | Implements | Source implements target interface | Dashed arrow, open head |
| `contains` | Contains | Source contains target (nesting) | Enclosure |

#### Full View — UML Relationship Types

| Type Key | Display Name | Description | Notation |
|----------|-------------|-------------|----------|
| `association` | Association | Structural link between classes | Solid line |
| `aggregation` | Aggregation | Whole-part (weak ownership) | Open diamond |
| `composition` | Composition | Whole-part (strong ownership, lifecycle) | Filled diamond |
| `dependency` | Dependency | Source depends on target | Dashed arrow |
| `realization` | Realization | Source implements target specification | Dashed line, open head |
| `generalization` | Generalization | Source inherits from target | Solid line, open head |

#### Full View — ArchiMate Relationship Types

| Type Key | Display Name | Description | Notation |
|----------|-------------|-------------|----------|
| `serving` | Serving | Source serves target | Arrow |
| `flow` | Flow | Transfer of content between elements | Dashed arrow |
| `triggering` | Triggering | Source triggers target | Arrow with bar |
| `access` | Access | Source accesses target data | Dashed arrow |
| `influence` | Influence | Source influences target | Dashed arrow |
| `archimate_realization` | Realization (ArchiMate) | Source realises target | Dashed line |
| `archimate_composition` | Composition (ArchiMate) | Source is composed of target | Line with diamond |
| `archimate_aggregation` | Aggregation (ArchiMate) | Source aggregates target | Line with open diamond |

### Extensibility

Like entity types, relationship types are validated in application code. The `relationships.relationship_type` TEXT column accepts any string. Type-specific data (cardinality, constraints, UML-specific properties) is stored in the `relationship_versions.data` JSON blob.

---

## Model Schema

Models are containers that project a subset of entities and relationships onto a canvas. They follow the same versioning pattern as entities (SPEC-006-A).

### Model Identity Table

```sql
CREATE TABLE models (
    id TEXT PRIMARY KEY,                    -- UUID, stable identity
    model_type TEXT NOT NULL,              -- See Model Type Taxonomy
    current_version INTEGER NOT NULL,       -- Points to latest version number
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    created_by TEXT NOT NULL REFERENCES users(id),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),  -- Updated on every version change
    is_deleted INTEGER NOT NULL DEFAULT 0   -- Soft delete flag
);

CREATE INDEX idx_models_type ON models(model_type);
CREATE INDEX idx_models_created_by ON models(created_by);
```

### Model Versions Table

```sql
CREATE TABLE model_versions (
    model_id TEXT NOT NULL REFERENCES models(id),
    version INTEGER NOT NULL,               -- Monotonically increasing per model
    name TEXT NOT NULL,                     -- Model display name at this version
    description TEXT,                       -- Model description at this version
    data TEXT NOT NULL,                     -- JSON: complete model state (see Model Version Data Structure)
    metadata TEXT,                          -- JSON blob of user-defined metadata
    change_type TEXT NOT NULL CHECK (change_type IN ('create', 'update', 'rollback', 'delete')),
    change_summary TEXT,                    -- Human-readable description of what changed
    rollback_to INTEGER,                    -- If change_type='rollback', the source version
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    created_by TEXT NOT NULL REFERENCES users(id),
    PRIMARY KEY (model_id, version)
);

CREATE INDEX idx_model_versions_created_at ON model_versions(created_at);
CREATE INDEX idx_model_versions_created_by ON model_versions(created_by);
```

### Model Type Taxonomy

| Type Key | Display Name | View | Description |
|----------|-------------|------|-------------|
| `component_diagram` | Component Diagram | Simple | Software components and their interfaces |
| `sequence_diagram` | Sequence Diagram | Simple | Interactions between actors/components over time |
| `class_diagram` | Class Diagram | Full | UML classes, attributes, operations, and relationships |
| `object_diagram` | Object Diagram | Full | Instances and their links at a point in time |
| `use_case_diagram` | Use Case Diagram | Full | Actors and use cases |
| `state_diagram` | State Diagram | Full | States and transitions of an object |
| `activity_diagram` | Activity Diagram | Full | Workflow and action sequences |
| `deployment_diagram` | Deployment Diagram | Full | Nodes and deployed artifacts |
| `archimate_business` | ArchiMate Business Layer | Full | Business actors, roles, processes, services |
| `archimate_application` | ArchiMate Application Layer | Full | Application components, services, interfaces |
| `archimate_technology` | ArchiMate Technology Layer | Full | Technology nodes, services, infrastructure |
| `archimate_motivation` | ArchiMate Motivation | Full | Stakeholders, drivers, goals, requirements |

### Model Version Data Structure

Model placements are **denormalised into the model version's `data` JSON**. Each model version is a complete snapshot of the diagram state. This avoids the complexity of separately versioning placement records and ensures rollback restores the entire visual state.

```json
{
  "placements": [
    {
      "entity_id": "uuid-of-entity",
      "position": { "x": 100, "y": 200 },
      "size": { "width": 180, "height": 80 },
      "visual": {}
    },
    {
      "entity_id": "uuid-of-another-entity",
      "position": { "x": 400, "y": 200 },
      "size": { "width": 180, "height": 80 },
      "visual": {}
    }
  ],
  "displayed_relationships": [
    "uuid-of-relationship-1",
    "uuid-of-relationship-2"
  ],
  "canvas": {
    "viewport": { "x": 0, "y": 0, "zoom": 1.0 },
    "grid": { "enabled": true, "snap": true, "size": 20 }
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `placements` | Array | Entities displayed on this model with position and visual state |
| `placements[].entity_id` | UUID | Reference to the entity in the repository |
| `placements[].position` | Object | Canvas coordinates `{ x, y }` |
| `placements[].size` | Object | Dimensions `{ width, height }` |
| `placements[].visual` | Object | Type-specific visual overrides (colour, collapsed state, etc.) |
| `displayed_relationships` | Array | Relationship UUIDs to render between placed entities |
| `canvas` | Object | Canvas-level state (viewport, grid settings) |

### Why Denormalise Placements?

1. **Atomic versioning** — rollback restores the complete visual state in one operation
2. **No orphan placements** — no risk of placement records referencing deleted model versions
3. **Query simplicity** — one read to get the full model state
4. **Consistency** — same JSON-in-version pattern as entities and relationships

---

## Cross-Reference Queries

The repository-first architecture enables powerful cross-reference queries:

### Entity Relationship Web

```sql
-- All relationships involving a given entity (for entity relationship web view)
SELECT r.id, r.relationship_type, r.source_entity_id, r.target_entity_id,
       rv.label, rv.description
FROM relationships r
JOIN relationship_versions rv ON r.id = rv.relationship_id AND r.current_version = rv.version
WHERE (r.source_entity_id = :entity_id OR r.target_entity_id = :entity_id)
  AND r.is_deleted = 0;
```

### Entity Usage Across Models

```sql
-- All models that reference a given entity (for "used in" statistics)
SELECT m.id, mv.name, m.model_type
FROM models m
JOIN model_versions mv ON m.id = mv.model_id AND m.current_version = mv.version
WHERE m.is_deleted = 0
  AND EXISTS (
    SELECT 1 FROM json_each(mv.data, '$.placements')
    WHERE json_extract(value, '$.entity_id') = :entity_id
  );
```

### Entity Statistics

```sql
-- Count of relationships and model appearances for an entity
SELECT
    (SELECT COUNT(*) FROM relationships
     WHERE (source_entity_id = :entity_id OR target_entity_id = :entity_id)
       AND is_deleted = 0) AS relationship_count,
    (SELECT COUNT(*) FROM models m
     JOIN model_versions mv ON m.id = mv.model_id AND m.current_version = mv.version
     WHERE m.is_deleted = 0
       AND EXISTS (
         SELECT 1 FROM json_each(mv.data, '$.placements')
         WHERE json_extract(value, '$.entity_id') = :entity_id
       )) AS model_count;
```

---

## Operations

### Create Relationship

```sql
-- 1. Insert relationship identity
INSERT INTO relationships (id, source_entity_id, target_entity_id, relationship_type, current_version, created_by)
VALUES (:id, :source_entity_id, :target_entity_id, :relationship_type, 1, :user_id);

-- 2. Insert first version
INSERT INTO relationship_versions (relationship_id, version, label, description, data, metadata, change_type, created_by)
VALUES (:id, 1, :label, :description, :data, :metadata, 'create', :user_id);
```

Both operations in a single transaction. Requires `relationship.create` permission.

### Update Relationship

```sql
-- 1. Check optimistic concurrency
SELECT current_version FROM relationships WHERE id = :id;
-- If current_version != expected_version → HTTP 409 Conflict

-- 2. Insert new version
INSERT INTO relationship_versions (relationship_id, version, label, description, data, metadata, change_type, change_summary, created_by)
VALUES (:id, :current_version + 1, :label, :description, :data, :metadata, 'update', :summary, :user_id);

-- 3. Update current version pointer
UPDATE relationships SET current_version = :current_version + 1, updated_at = datetime('now')
WHERE id = :id;
```

All operations in a single transaction.

### Delete Relationship (Soft Delete)

```sql
-- 1. Insert delete version
INSERT INTO relationship_versions (relationship_id, version, label, description, data, metadata, change_type, change_summary, created_by)
VALUES (:id, :current_version + 1, :current_label, :current_description, :current_data, :current_metadata, 'delete', 'Relationship deleted', :user_id);

-- 2. Mark as soft-deleted
UPDATE relationships SET is_deleted = 1, current_version = :current_version + 1, updated_at = datetime('now')
WHERE id = :id;
```

Requires `relationship.delete` permission.

### Create Model

```sql
-- 1. Insert model identity
INSERT INTO models (id, model_type, current_version, created_by)
VALUES (:id, :model_type, 1, :user_id);

-- 2. Insert first version (empty canvas)
INSERT INTO model_versions (model_id, version, name, description, data, metadata, change_type, created_by)
VALUES (:id, 1, :name, :description, :data, :metadata, 'create', :user_id);
```

Both operations in a single transaction. Requires `model.create` permission.

### Update Model

```sql
-- 1. Check optimistic concurrency
SELECT current_version FROM models WHERE id = :id;
-- If current_version != expected_version → HTTP 409 Conflict

-- 2. Insert new version (complete snapshot)
INSERT INTO model_versions (model_id, version, name, description, data, metadata, change_type, change_summary, created_by)
VALUES (:id, :current_version + 1, :name, :description, :data, :metadata, 'update', :summary, :user_id);

-- 3. Update current version pointer
UPDATE models SET current_version = :current_version + 1, updated_at = datetime('now')
WHERE id = :id;
```

All operations in a single transaction.

### Rollback Model (Admin Only)

```sql
-- Same pattern as entity rollback (SPEC-006-A)
-- 1. Read target version state
-- 2. Get current version number
-- 3. Insert rollback version with target's data
-- 4. Update current version pointer
```

Requires `version.rollback` permission.

---

## Referential Integrity

### Deletion Cascade Rules

| Action | Effect |
|--------|--------|
| Soft-delete entity | Relationships referencing it remain (with warning in UI). Model placements referencing it show "deleted entity" indicator. |
| Soft-delete relationship | Model `displayed_relationships` referencing it are ignored at render time. |
| Soft-delete model | Model and all versions retained for audit. Not listed in browse. |
| Hard delete | Not supported. All deletes are soft deletes per ADR-006. |

### Orphan Detection

When rendering a model, the application must handle:
- **Deleted entity references** — placements pointing to soft-deleted entities display a visual indicator
- **Deleted relationship references** — relationships in `displayed_relationships` that are soft-deleted are silently omitted from rendering

---

## Collaboration Schema (Preview)

These tables are defined for Phase C but included here for domain model completeness.

### Comments

```sql
CREATE TABLE comments (
    id TEXT PRIMARY KEY,                    -- UUID
    entity_id TEXT REFERENCES entities(id), -- NULL if model-level comment
    model_id TEXT REFERENCES models(id),    -- NULL if entity-level comment
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    created_by TEXT NOT NULL REFERENCES users(id),
    is_deleted INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX idx_comments_entity ON comments(entity_id);
CREATE INDEX idx_comments_model ON comments(model_id);
CREATE INDEX idx_comments_created_by ON comments(created_by);
```

### Bookmarks

```sql
CREATE TABLE bookmarks (
    user_id TEXT NOT NULL REFERENCES users(id),
    model_id TEXT NOT NULL REFERENCES models(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, model_id)
);
```

---

## Complete Schema Summary

| Table | Defined In | Phase |
|-------|-----------|-------|
| `users` | SPEC-005-B | A |
| `password_history` | SPEC-005-B | A |
| `roles` | SPEC-005-A | A |
| `role_permissions` | SPEC-005-A | A |
| `refresh_tokens` | SPEC-005-B | A |
| `entities` | SPEC-006-A | A |
| `entity_versions` | SPEC-006-A | A |
| `relationships` | **This spec** | A |
| `relationship_versions` | **This spec** | A |
| `models` | **This spec** | A |
| `model_versions` | **This spec** | A |
| `comments` | **This spec** (preview) | C |
| `bookmarks` | **This spec** (preview) | C |
| `audit_log` | SPEC-007-A (separate DB) | A |

---

## Storage Considerations

| Metric | Estimate |
|--------|----------|
| Relationships per enterprise model | 1,000-10,000 |
| Average relationship version size | 0.5-2 KB |
| Models per enterprise deployment | 50-500 |
| Average model version size | 5-50 KB (depends on placement count) |
| Model versions per model | 10-100 over project lifetime |
| Total additional storage | 50 MB - 2.5 GB for a mature enterprise deployment |

Combined with entity storage (SPEC-006-A), total database size remains well within SQLite's comfortable operating range.

---

*This specification implements [ADR-003](../ADR-003-Architectural-Vision.md) and extends [SPEC-006-A](./SPEC-006-A-Entity-Versioning.md) with the full repository domain model.*
