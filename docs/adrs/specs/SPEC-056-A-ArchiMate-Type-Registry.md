# SPEC-056-A: ArchiMate Type Registry Expansion

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-056-A |
| **ADR** | [ADR-056](../ADR-056-ArchiMate-Full-Specification.md) |
| **Status** | Accepted |
| **Date** | 2026-03-02 |

---

## Overview

Expand the ArchiMate type registry from 11 entity types across 3 layers to ~45 entity types across 6 layers, covering the full ArchiMate 3.2 specification. This is a frontend-only change — the backend stores `entity_type` as free-form TEXT and requires no migration.

## New Entity Types by Layer

### Business Layer (+5 new, 10 total)

| Key | Label | Icon | Description |
|-----|-------|------|-------------|
| `business_actor` | Business Actor | 👤 | Person or organisational unit |
| `business_role` | Business Role | 🎭 | Responsibility assigned to an actor |
| `business_process` | Business Process | ⟳ | Sequence of business behaviours |
| `business_service` | Business Service | ◎ | Externally visible business functionality |
| `business_object` | Business Object | ▤ | Business domain concept |
| `business_function` | Business Function | ⨍ | Collection of business behaviour |
| `business_interaction` | Business Interaction | ⇄ | Behaviour element performed by collaborating roles |
| `business_event` | Business Event | ⚡ | Business state change |
| `business_collaboration` | Business Collaboration | ⊕ | Aggregate of two or more business roles |
| `business_interface` | Business Interface | ◯ | Point of access to business services |

### Application Layer (+5 new, 8 total)

| Key | Label | Icon | Description |
|-----|-------|------|-------------|
| `application_component` | Application Component | ⬡ | Deployable application unit |
| `application_service` | Application Service | ◎ | Externally visible application functionality |
| `application_interface` | Application Interface | ◯ | Point of access to application services |
| `application_function` | Application Function | ⨍ | Automated behaviour element |
| `application_interaction` | Application Interaction | ⇄ | Behaviour element performed by collaborating components |
| `application_event` | Application Event | ⚡ | Application state change |
| `application_collaboration` | Application Collaboration | ⊕ | Aggregate of two or more application components |
| `application_process` | Application Process | ⟳ | Sequence of application behaviours |

### Technology Layer (+7 new, 10 total)

| Key | Label | Icon | Description |
|-----|-------|------|-------------|
| `technology_node` | Technology Node | ⬡ | Computational or physical resource |
| `technology_service` | Technology Service | ◎ | Externally visible technology functionality |
| `technology_interface` | Technology Interface | ◯ | Point of access to technology services |
| `technology_function` | Technology Function | ⨍ | Collection of technology behaviour |
| `technology_interaction` | Technology Interaction | ⇄ | Behaviour element performed by collaborating nodes |
| `technology_event` | Technology Event | ⚡ | Technology state change |
| `technology_collaboration` | Technology Collaboration | ⊕ | Aggregate of two or more technology nodes |
| `technology_process` | Technology Process | ⟳ | Sequence of technology behaviours |
| `technology_artifact` | Technology Artifact | ▤ | Piece of data used or produced |
| `technology_device` | Technology Device | ▣ | Physical computational resource |

### Motivation Layer (new, 8 types)

| Key | Label | Icon | Description |
|-----|-------|------|-------------|
| `stakeholder` | Stakeholder | ♦ | Role of an individual, team, or organisation with interests |
| `driver` | Driver | ⚡ | External or internal condition that motivates change |
| `assessment` | Assessment | ◈ | Result of analysis of a driver |
| `goal` | Goal | ★ | High-level statement of intent or direction |
| `outcome` | Outcome | ✦ | End result that is achievable and measurable |
| `principle` | Principle | ⊕ | Qualitative statement of intent for the architecture |
| `requirement_archimate` | Requirement | ⊡ | Statement of need that must be met |
| `constraint_archimate` | Constraint | ⊠ | Factor limiting the realisation of goals |

### Strategy Layer (new, 4 types)

| Key | Label | Icon | Description |
|-----|-------|------|-------------|
| `resource` | Resource | ◆ | Asset owned or controlled by an individual or organisation |
| `capability` | Capability | ⬢ | Ability that an organisation possesses |
| `course_of_action` | Course of Action | ➤ | Approach or plan for achieving a goal |
| `value_stream` | Value Stream | ≡ | Sequence of activities creating an overall result |

### Implementation & Migration Layer (new, 5 types)

| Key | Label | Icon | Description |
|-----|-------|------|-------------|
| `work_package` | Work Package | ▣ | Series of actions to achieve a result |
| `deliverable` | Deliverable | ◧ | Precisely defined output of a work package |
| `implementation_event` | Implementation Event | ⚑ | State change during implementation |
| `plateau` | Plateau | ▬ | Relatively stable state of the architecture |
| `gap` | Gap | △ | Difference between two plateaus |

## New Relationship Types (+3 new, 11 total)

| Key | Label | Description |
|-----|-------|-------------|
| `specialization` | Specialization | Source specialises target |
| `assignment` | Assignment | Source assigned to target |
| `association_archimate` | Association | Unspecified relationship |

## Layer Visual Styling

Each layer has a distinct colour scheme applied via CSS class on the node:

| Layer | CSS Class | Border Colour | Background | Badge Letter |
|-------|-----------|---------------|------------|--------------|
| Business | `archimate-node--business` | `#f59e0b` | (default) | B |
| Application | `archimate-node--application` | `#3b82f6` | (default) | A |
| Technology | `archimate-node--technology` | `#22c55e` | (default) | T |
| Motivation | `archimate-node--motivation` | `#9b59b6` | `#f5eef8` | M |
| Strategy | `archimate-node--strategy` | `#f39c12` | `#fef9e7` | S |
| Implementation & Migration | `archimate-node--implementation_migration` | `#27ae60` | `#eafaf1` | I |

## Files Modified

| File | Change |
|------|--------|
| `frontend/src/lib/types/canvas.ts` | Expanded `ArchimateEntityType`, `ArchimateLayer`, `ArchimateRelationshipType` unions; added entries to `ARCHIMATE_ENTITY_TYPES` and `ARCHIMATE_RELATIONSHIP_TYPES` arrays |
| `frontend/src/lib/canvas/archimate/nodes/index.ts` | Added all new type keys mapped to `ArchimateNode` component |
| `frontend/src/lib/canvas/archimate/edges/index.ts` | Added 3 new edge types mapped to `ArchimateEdge` component |
| `frontend/src/app.css` | Added layer-specific CSS for motivation, strategy, and implementation_migration |

## Acceptance Criteria

1. `ArchimateEntityType` union includes all ~45 types
2. `ArchimateLayer` union includes all 6 layers
3. `ARCHIMATE_ENTITY_TYPES` array has display metadata for all types
4. `archimateNodeTypes` registry maps all types to `ArchimateNode`
5. `archimateEdgeTypes` registry includes `specialization`, `assignment`, and `association_archimate`
6. CSS classes exist for `motivation`, `strategy`, and `implementation_migration` layers
7. Layer badge displays correct first letter for each layer
8. No backend changes required
