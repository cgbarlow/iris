# ADR-045: Example Iris Architecture Models

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-045 |
| **Initiative** | Example Iris Architecture Models (WP-16) |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-01 |
| **Status** | Accepted |

---

## ADR (WH(Y) Statement format)

**In the context of** a fresh Iris installation where new users see an empty dashboard with no models or entities, making it difficult to understand the tool's purpose and capabilities,

**facing** the need for immediately visible example content that demonstrates both the modelling workflow and Iris's own internal architecture, while ensuring the seed data does not interfere with production content or cause errors on repeated startups,

**we decided for** an idempotent seed script (`app/seed/example_models.py`) that runs during application startup after migrations and existing seeds, creating five component entities (Frontend, Backend, Database, Auth Service, Canvas Engine) and one component model ("Iris Architecture") with canvas nodes and edges showing their interactions, all tagged with `iris` and `example` (model additionally tagged `template`), skipping entirely if entities with the `example` tag already exist,

**and neglected** a manual import/export approach (requires user action, not zero-config), a migration-based approach (migrations are for schema changes, not content), and loading from an external JSON fixture file (adds file I/O complexity and a separate file to maintain when the data is simple enough to define inline),

**to achieve** a zero-configuration onboarding experience where new installations immediately display a meaningful example model that users can browse, clone, and learn from, while remaining fully idempotent and safe for production environments,

**accepting that** the seed creates a deactivated `system` user to satisfy foreign key constraints on `created_by` columns, that the example content only appears after the first admin user completes initial setup (the seed skips if no active users exist, to avoid interfering with `/api/auth/setup`), and that deleting the example entities and model requires manual cleanup (the seed will not re-create them once any `example`-tagged entities exist).

---

## Options Considered

### Option 1: Startup Seed Script (Selected)

**Pros:**
- Runs automatically on first startup, zero user action required
- Idempotent via tag-based existence check
- Follows existing seed patterns (roles, settings)
- Deterministic UUIDs via uuid5 ensure stability across runs

**Cons:**
- Adds startup time on first run (negligible for 5 entities + 1 model)
- Requires a system user for FK compliance

**Why selected:** Consistent with existing seed infrastructure, provides immediate value to new users.

### Option 2: External JSON Fixture File (Rejected)

**Pros:**
- Data separated from code
- Easier to edit without touching Python

**Cons:**
- Adds file I/O and JSON parsing complexity
- Another file to maintain and keep in sync with schema changes
- Over-engineered for a small, stable dataset

**Why rejected:** Unnecessary indirection for five entities and one model.

### Option 3: Migration-Based Seed (Rejected)

**Pros:**
- Runs exactly once via migration tracking

**Cons:**
- Migrations are for schema changes, not content
- Mixing concerns makes migration history harder to reason about

**Why rejected:** Violates separation of concerns between schema and content.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-03-01 | Accepted | Add example architecture seed | 6 months | 2026-09-01 |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Architecture Team | 2026-03-01 |
| Accepted | Project Lead | 2026-03-01 |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Depends On | ADR-001 | Enhanced ADR Format | This ADR follows the enhanced WH(Y) format |
| Depends On | ADR-037 | Tag Management System | Uses entity and model tags for idempotency and categorisation |
| Depends On | ADR-043 | Template Designation | Example model tagged as template |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-045-A | Example Architecture Models Seed | Technical Specification | [specs/SPEC-045-A-Example-Architecture-Models.md](specs/SPEC-045-A-Example-Architecture-Models.md) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
