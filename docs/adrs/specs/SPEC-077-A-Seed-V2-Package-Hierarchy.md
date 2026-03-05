# SPEC-077-A: Seed V2 — Package Hierarchy & C4 Diagram

**ADR:** [ADR-077](../ADR-077-Seed-V2-Package-Hierarchy.md)
**Status:** Approved
**Date:** 2026-03-04

---

## Overview

Rewrite the example seed in `backend/app/seed/example_models.py` to organise diagrams into a package hierarchy and add a C4 System Context diagram. Includes auto-clearing of stale v1 seed data.

## Package Hierarchy

```
Iris (root package)
├── Application Layer (child package)
│   ├── Iris Architecture (component diagram)
│   ├── API Request Flow (sequence diagram)
│   └── Iris C4 Context (C4 diagram) ← NEW
├── Data Layer (child package)
│   ├── Data Layer (component diagram)
│   └── Data Model (component diagram)
├── Enterprise (child package)
│   └── Iris Enterprise View (archimate diagram)
└── Iris System Overview (component diagram — modelrefs to all above)
```

## Changes to `backend/app/seed/example_models.py`

### New: `_PACKAGES` definition
```
(0, "Iris", "Root package for Iris architecture examples", None)
(1, "Application Layer", "Frontend, API, and C4 views", 0)
(2, "Data Layer", "Database schema and data services", 0)
(3, "Enterprise", "Enterprise architecture views", 0)
```

### New: `_build_c4_context_model()` builder
- 5 nodes: User (person), Admin (person), Iris (software_system), Web Browser (software_system_external), SQLite (software_system)
- 4 edges: c4_relationship type with technology annotations

### New: `_clear_old_seed_data(db)` function
Deletes old seed data by deterministic IDs in dependency order.

### Updated: `_DIAGRAMS` entries
Each entry gains a `parent_package_index` field mapping to a package.

### Updated: `seed_example_models()` idempotency
- If `_gen_id("pkg", 0)` exists in packages → already v2, skip
- If element_tags with tag='example' exist but no root package → old v1, clear and reseed
- Otherwise → fresh seed

### Updated: `_build_system_overview_model()`
Add modelref node for C4 diagram + connecting edge.

## Acceptance Criteria

1. Seed creates 4 packages in Default set
2. Root package "Iris" has no parent (`parent_package_id IS NULL`)
3. 3 child packages reference root as parent
4. All 7 diagrams have `parent_package_id` set
5. System Overview has modelref nodes for all 6 sub-diagrams including C4
6. C4 diagram exists with `person` and `software_system` node types
7. Old v1 seed data is auto-cleared on reseed
8. Idempotent: running seed twice doesn't duplicate
9. 15 elements and 20 relationships still present
10. Package and diagram IDs are deterministic via `_gen_id()`
