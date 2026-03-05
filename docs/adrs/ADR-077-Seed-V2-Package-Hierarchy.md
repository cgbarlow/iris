# ADR-077: Seed V2 — Package Hierarchy & C4 Diagram

## Proposal: Restructure example seed to demonstrate v2 package hierarchy and C4 support

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-077 |
| **Initiative** | Seed Data Enhancement |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-04 |
| **Status** | Approved |
| **Dependencies** | ADR-071, ADR-074 |

---

## ADR (WH(Y) Statement format)

**In the context of** the v2.0.0 release introducing packages, package nesting, and C4 model support (ADR-071, ADR-074),

**facing** the Default set's example seed still using the v1 flat structure with no packages and no `parent_package_id` on diagrams,

**we decided for** rewriting the seed to organise all 7 diagrams into a 4-package hierarchy (1 root + 3 children), add a new C4 System Context diagram, set `parent_package_id` on every diagram, and auto-clear stale v1 seed data on upgrade,

**and neglected** keeping the flat seed unchanged (would not demonstrate v2 features) and adding packages via a separate migration (seed data should be self-contained),

**to achieve** a Default set that showcases the full v2 feature set — package nesting, diagram-in-package, modelref cross-references, and C4 notation — out of the box,

**accepting that** existing v1 seed data will be deleted and recreated in v2 format on first startup after upgrade.

---

## Decisions

1. **4-package hierarchy**: Root package "Iris" with children "Application Layer", "Data Layer", and "Enterprise"
2. **7 diagrams in packages**: Every diagram gets a `parent_package_id` pointing to one of the 4 packages
3. **New C4 diagram**: C4 System Context diagram with `person` and `software_system` node types in the Application Layer package
4. **System Overview modelrefs**: Updated to include a modelref node for the new C4 diagram
5. **v1→v2 auto-migration**: If element_tags with tag='example' exist but no root package, clear old seed data and reseed in v2 format
6. **Deterministic IDs**: Package IDs use the same `_gen_id("pkg", index)` pattern as elements and diagrams

---

## Specification

See [SPEC-077-A](specs/SPEC-077-A-Seed-V2-Package-Hierarchy.md).
