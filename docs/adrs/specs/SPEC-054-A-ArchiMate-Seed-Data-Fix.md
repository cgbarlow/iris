# SPEC-054-A: ArchiMate Seed Data Fix

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-054-A |
| **ADR** | [ADR-054](../ADR-054-ArchiMate-Seed-Data-Node-Type-Mapping.md) |
| **Status** | Approved |
| **Date** | 2026-03-01 |

---

## Overview

Fix the `_build_enterprise_model()` seed function to use ArchiMate-specific node types that exist in the `archimateNodeTypes` registry, and include `layer` and `archimateType` fields required by `ArchimateNode.svelte`.

## Node Type Mapping

| Node ID | Entity | Simple View Type (old) | ArchiMate Type (new) | Layer |
|---------|--------|----------------------|---------------------|-------|
| n10 | User | actor | business_actor | business |
| n11 | Admin | actor | business_actor | business |
| n1 | Frontend | component | application_component | application |
| n15 | Middleware Stack | package | technology_node | technology |
| n2 | Backend | component | application_component | application |
| n4 | Auth Service | service | application_service | application |
| n3 | Database | database | technology_node | technology |
| n6 | Search Service | service | technology_service | technology |

## Data Field Changes

Each node's `data` object must include:
- `layer`: ArchiMate layer string (`"business"`, `"application"`, or `"technology"`)
- `archimateType`: Human-readable ArchiMate type label for ARIA/badge display

## Test Coverage

- `archimateNodeTypes.test.ts` — Vitest unit test verifying all ArchiMate seed node types exist in the `archimateNodeTypes` registry

## Acceptance Criteria

1. All nodes in `_build_enterprise_model()` use types from `archimateNodeTypes`
2. All nodes include `layer` and `archimateType` in their `data` objects
3. Enterprise View renders with coloured layer borders and badges in edit mode
4. Unit test confirms type registry coverage
