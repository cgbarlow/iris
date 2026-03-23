# SPEC-100-A: DoView Element-Backed Nodes

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-100-A |
| **ADR** | [ADR-100](../ADR-100-DoView-Element-Backed-Nodes.md) |
| **Status** | Draft |
| **Date** | 2026-03-23 |

---

## Overview

Ensure every DoView diagram node is backed by an element record (with `entityId` in node data) and every causal link edge is backed by a relationship record (with `relationshipId` in edge data). Applies to both seed data and AI-created diagrams.

---

## Part A: Seed Data

### File: `backend/app/seed/example_models.py`

**Helper:** Add `_de(eids, nid, bg, border, **extra)` — DoView entity helper wrapping `_e()` with visual colours, following the `_ae()` pattern for ArchiMate.

**Elements:** Replace 7 orphaned DoView entities (indices 59–65) with 28 Iris-themed entries (indices 59–86) covering all DoView diagram nodes:
- 5 `overview_tile` (Overview diagram)
- 3 `final_outcome` (Final Outcomes + Strategic Vision — cross-diagram reuse)
- 2 `outcome_box` (Strategic Vision only)
- 10 `outcome_box` (Platform Delivery)
- 7 `outcome_box` (User Enablement)
- 1 `source_reference` (Sources)

**Relationships:** Replace 5 orphaned causal_link entries (indices 58–62) with 19 entries (indices 58–76) matching actual diagram edges.

**Diagram builders:** Update all 6 DoView builders to use `_node()` + `_de()` + `_edge()` with `entityId` and `relationshipId`.

**Cross-diagram reuse:** Elements `dv_fo1`, `dv_fo2`, `dv_fo3` appear on both Final Outcomes and Strategic Vision diagrams.

**Version:** Bump to `_V8_MARKER = "seed_v8"`.

---

## Part B: AI Diagram Creation

### File: `backend/app/ai/creation.py`

Add **Phase 1.5** to `create_diagrams_from_ai()` between Phase 1 (create diagrams) and Phase 2 (resolve linkedDiagramIndex):

For each diagram in the AI JSON:
1. For each node: create element record → inject `entityId` into `node.data`
2. Build `node_id → element_id` mapping
3. For each edge: resolve source/target element IDs → create relationship record → inject `relationshipId` into `edge.data`
4. Update `diagram_versions` with enriched canvas data

### File: `backend/app/elements/materialise.py` (new)

Shared helper functions used by both seed and AI creation:
- `materialise_element(db, *, element_id, element_type, name, description, set_id, notation, created_by, now)`
- `materialise_relationship(db, *, rel_id, source_element_id, target_element_id, relationship_type, label, description, created_by, now)`

Both insert records without committing — caller controls transaction boundaries.

---

## Tests

### Seed: `backend/tests/test_seed/test_example_models.py`
- Element count: 66 → 87
- Relationship count: 63 → 77
- DoView notation count: 7 → 28
- New: `test_doview_nodes_have_entity_ids`
- New: `test_doview_cross_diagram_reuse`
- New: `test_doview_edges_have_relationship_ids`

### AI Creation: `backend/tests/test_ai/test_creation.py`
- New: `test_create_diagrams_creates_elements`
- New: `test_create_diagrams_creates_relationships`
- New: `test_element_notation_matches_diagram`
