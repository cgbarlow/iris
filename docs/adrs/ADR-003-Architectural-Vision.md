# ADR-003: Architectural Vision — Repository First

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-003 |
| **Initiative** | Iris Core Architecture |
| **Proposed By** | The Architect (Bear) |
| **Date** | 2026-02-27 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** designing the core architecture for Iris, an architectural modelling tool that must support entity reuse across models, relationship tracking, version control, and enterprise-scale modelling,

**facing** the fundamental design choice between building a diagramming tool (where diagrams are the primary artefact and shapes are independent per diagram) versus building a repository (where entities are first-class objects with identity, and diagrams are projections of a shared model of truth),

**we decided for** a repository-first architecture with three layers — The Foundation (data and domain model), The Engine (API and business logic), and The Lens (frontend and UX) — built strictly in that order, where entities exist once in the repository and are referenced across multiple models, creating a web of relationships,

**and neglected** a diagram-first architecture (where each diagram is a standalone canvas with shapes that happen to look similar across diagrams but have no shared identity, making enterprise-scale relationship tracking impossible) and a hybrid approach (starting with diagrams and retrofitting entity identity later, which would create painful migration and inconsistency),

**to achieve** true enterprise-scale modelling where entities have identity, metadata, version history, and navigable relationships across all models; where an entity view shows a web of all relationships and statistics; and where the system can serve as the single source of truth for architectural decisions,

**accepting that** this approach requires more upfront schema design and data modelling before any visual output appears, that the build sequence must go foundation-up (no shortcuts to "something on screen"), and that the entity model design in Phase A is the single most consequential decision in the project.

---

## The Three Layers

| Layer | Name | Responsibility | Build Phase |
|-------|------|---------------|-------------|
| 1 | **The Foundation** | Data & Domain Model — SQLite schema, entity identity, versioning, audit trail, relationships, metadata | Phase A |
| 2 | **The Engine** | API & Business Logic — Authentication, RBAC, CRUD, version control, semantic search, deep links, comments | Phases B-C |
| 3 | **The Lens** | Frontend & UX — Interactive canvas, Browse/Edit modes, Simple/Full views, theming, accessibility | Phases D-F |

## Build Sequence

| Phase | Focus | Key Deliverables |
|-------|-------|-----------------|
| A | Data Foundation | SQLite schema, entity model, relationships, versions, audit log, users, roles, migrations, tests |
| B | Core API | Backend framework, authentication, RBAC, CRUD operations, version control, audit logging, deep link URL scheme |
| C | Search & Collaboration | Semantic search indexing and query, commenting system, bookmarks/stars |
| D | Frontend Foundation | SvelteKit shell, routing, auth flow, theme system, accessibility scaffolding |
| E | The Canvas | Interactive modelling canvas, Simple View (component + sequence), Full View (UML + ArchiMate) |
| F | Browse Mode & Entity Views | Read-only model browsing, entity relationship web view, statistics |
| G | Polish & Compliance | WCAG audit, NZ ITSM verification, performance, edge cases |

## Key Architectural Principle

> If entities are just shapes on a canvas, Iris is a drawing tool. If entities are first-class objects in a repository with identity, versioning, relationships, and metadata — then Iris is what it claims to be: an Integrated Repository for Information & Systems.

---

## Options Considered

### Option 1: Repository-First Architecture (Selected)

**Pros:**
- Entities with true identity enable cross-model relationships and enterprise-scale modelling
- Version control and audit trail are natural at the entity level
- Entity relationship web view with statistics becomes straightforward
- Semantic search operates on structured, identified data
- Foundation supports any future diagram type without schema changes

**Cons:**
- More upfront design before visual output
- Requires disciplined build sequencing (no skipping to frontend)
- Schema design is high-stakes — errors are costly to fix

### Option 2: Diagram-First Architecture (Rejected)

**Pros:**
- Visual output appears quickly
- Simpler initial implementation
- Familiar to developers with drawing tool experience

**Cons:**
- No entity identity — shapes are per-diagram with no shared reference
- Enterprise-scale relationship tracking is impossible or requires painful retrofitting
- Version control applies to diagrams, not entities
- Semantic search has no structured data to operate on

**Why rejected:** Fundamentally incompatible with Iris's stated purpose as an integrated repository.

### Option 3: Hybrid — Start Diagrams, Add Repository Later (Rejected)

**Why rejected:** Retrofitting entity identity into a diagram-first system creates migration complexity, data inconsistency, and architectural debt. The repository model must be the foundation, not an afterthought.

---

## Governance

| Review Board | Date | Outcome | Action | Review Cadence | Next Review |
|--------------|------|---------|--------|----------------|-------------|
| Project Lead | 2026-02-27 | Approved | Proceed with repository-first architecture | 6 months | 2026-08-27 |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | The Architect (Bear) | 2026-02-27 |
| Approved | Project Lead | 2026-02-27 |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Depends On | ADR-001 | Enhanced ADR Format | This ADR follows the enhanced WH(Y) format |
| Depends On | ADR-002 | Frontend Tech Stack | The Lens layer uses the selected frontend stack |
| Enables | TBD | Data Foundation Schema Design | Schema design is the first implementation phase |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-003-A | Entity Domain Model | Technical Specification | specs/SPEC-003-A-Entity-Domain-Model.md (TBD) |
| SPEC-003-B | Build Phase Definitions | Technical Specification | specs/SPEC-003-B-Build-Phases.md (TBD) |

---

*This ADR was created following the WH(Y) format as specified in [SPEC-001-A](./specs/SPEC-001-A-WHY-Format.md).*
