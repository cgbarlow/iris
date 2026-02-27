# ADR-006: Version Control and Rollback Semantics

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-006 |
| **Initiative** | Iris Data Foundation — Version Control |
| **Proposed By** | The CISO (Cat) / The Architect (Bear) |
| **Date** | 2026-02-27 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** designing version control for Iris's repository-first architecture, where entities are first-class objects shared across multiple models and every mutation must be auditable and reversible,

**facing** the choice between mutable-in-place updates with undo logs, immutable append-only versioning with explicit rollback semantics, and git-style branching with merge operations,

**we decided for** immutable append-only versioning where every entity mutation creates a new version row, and rollback is implemented as "revert-as-new-version" — creating a new version whose content matches a previous version, preserving the full mutation history and audit trail,

**and neglected** mutable-in-place updates with undo logs (which destroy history and make audit trails unreliable), and git-style branching (which adds prohibitive complexity for an entity repository — merge conflicts on structured entities are fundamentally different from text file merges),

**to achieve** a complete, tamper-evident history of every entity state, safe rollback that never destroys data, clear audit trails for governance compliance, and predictable behaviour when rolling back entities that are referenced across multiple models,

**accepting that** immutable versioning increases storage requirements (mitigated by the metadata-heavy, data-light nature of architecture models), that "revert-as-new-version" means version numbers always increment (rollback to version 3 creates version 8, not a return to version 3), and that garbage collection of old versions must be a deliberate admin operation if ever needed.

---

## Version Control Model

### Core Principles

1. **Immutability.** Entity rows are never updated in place. Every change creates a new version row.
2. **Monotonic versioning.** Version numbers always increment. There is no "going back" to a previous version number.
3. **Revert-as-new-version.** Rollback creates a new version whose content matches a specified previous version. The rollback itself is a recorded mutation.
4. **Full history retention.** No version is ever deleted by normal operations. The complete mutation history is the audit trail.
5. **Optimistic concurrency.** Each entity carries a version stamp. Updates must specify the expected current version. Conflict if the entity has been modified since the client last read it.

### Schema Design

```
entities (
    id              TEXT PRIMARY KEY,   -- Stable entity identity (UUID)
    current_version INTEGER NOT NULL,   -- Points to latest version number
    entity_type     TEXT NOT NULL,      -- Component, service, interface, etc.
    created_at      TEXT NOT NULL,      -- ISO 8601
    created_by      TEXT NOT NULL       -- User ID
)

entity_versions (
    entity_id       TEXT NOT NULL,      -- FK → entities.id
    version         INTEGER NOT NULL,   -- Monotonically increasing per entity
    data            TEXT NOT NULL,      -- JSON blob of entity state
    created_at      TEXT NOT NULL,      -- ISO 8601
    created_by      TEXT NOT NULL,      -- User ID who made this change
    change_type     TEXT NOT NULL,      -- 'create' | 'update' | 'rollback'
    rollback_to     INTEGER,            -- If change_type='rollback', which version was reverted to
    PRIMARY KEY (entity_id, version)
)
```

### Rollback Behaviour

**Scenario:** Entity "Payment Service" is at version 5. Admin wants to rollback to the state it had at version 3.

**What happens:**
1. System reads `entity_versions` where `entity_id = X` and `version = 3`
2. System creates a new row in `entity_versions` with `version = 6`, `data` = (copy of version 3's data), `change_type = 'rollback'`, `rollback_to = 3`
3. System updates `entities.current_version` to 6

**What the history looks like:**

| Version | Change Type | Content | Notes |
|---------|-------------|---------|-------|
| 1 | create | Initial state | — |
| 2 | update | Added endpoints | — |
| 3 | update | Added security config | — |
| 4 | update | Changed hosting | — |
| 5 | update | Updated dependencies | — |
| 6 | rollback | Same as version 3 | `rollback_to: 3` |

**Key points:**
- Version 6 is a new version, not a deletion of versions 4-5
- Versions 4 and 5 are preserved in history
- The audit trail clearly shows who rolled back, when, and to which version
- Any models referencing this entity automatically see version 6 (the current version)

### Cross-Model Impact

When an entity is rolled back, every model that references it sees the updated state because models reference entities by ID, not by version. The current version is always resolved at read time.

**Implication:** Rolling back a shared entity affects all models that use it. This is by design — entities are shared objects in the repository, not copies per model. This is why rollback is Admin-only (see ADR-005).

### Optimistic Concurrency Control

To prevent lost updates when multiple users edit the same entity:

1. Client reads entity with `current_version = N`
2. Client submits update with `expected_version = N`
3. Server checks: if `current_version != N`, reject with HTTP 409 Conflict
4. Server creates version `N+1` and updates `current_version`

This ensures no silent overwrites. The client must re-read and re-apply changes on conflict.

---

## Options Considered

### Option 1: Immutable Append-Only with Revert-as-New-Version (Selected)

**Pros:**
- Complete, tamper-evident history
- Rollback never destroys data
- Clear audit trail — every state change is recorded
- Simple mental model: version numbers always go up
- Natural fit for NZ ITSM audit requirements

**Cons:**
- Storage grows with every change (acceptable for metadata-heavy architecture models)
- Version numbers don't "go back" — rollback to v3 creates v6, which may confuse users initially
- Requires UI to clearly communicate version semantics

### Option 2: Mutable-in-Place with Undo Log (Rejected)

**Pros:**
- Simpler schema (one row per entity)
- Lower storage
- Familiar CRUD model

**Cons:**
- Undo log is a secondary record — if it diverges from reality, the audit trail is broken
- In-place updates destroy previous state
- Rollback requires replaying undo operations in reverse — error-prone with shared entities
- Does not meet NZ ITSM tamper-evidence requirements

**Why rejected:** Fundamentally incompatible with audit and governance requirements. In-place mutation with a separate undo log creates two sources of truth.

### Option 3: Git-Style Branching (Rejected)

**Pros:**
- Powerful model with branch, merge, diff capabilities
- Familiar to developers

**Cons:**
- Merge conflicts on structured entities (not text) are extremely complex
- Branching implies isolated workspaces — conflicts with real-time shared repository
- Implementation complexity far exceeds current requirements
- Overkill for version control of architectural entities

**Why rejected:** Git solves a different problem (text file collaboration). Entity versioning in a shared repository needs simpler, more predictable semantics.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-02-27 | Approved | Implement immutable versioning in Phase A schema | 6 months | 2026-08-27 |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | The CISO (Cat) / The Architect (Bear) | 2026-02-27 |
| Approved | Project Lead | 2026-02-27 |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Depends On | ADR-001 | Enhanced ADR Format | This ADR follows the enhanced WH(Y) format |
| Depends On | ADR-003 | Architectural Vision | Repository-first architecture requires entity-level versioning |
| Depends On | ADR-005 | RBAC Design | Rollback restricted to Admin role |
| Relates To | ADR-007 | Audit Log Integrity | Version history and audit logs are complementary |
| Enables | TBD | Phase A Schema Implementation | Versioning is core to the entity model |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-006-A | Entity Version Control Schema | Technical Specification | specs/SPEC-006-A-Entity-Versioning.md (TBD) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
