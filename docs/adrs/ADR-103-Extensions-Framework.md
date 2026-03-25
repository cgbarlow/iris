# ADR-103: Extensions Framework

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-103 |
| **Initiative** | Extensions Framework |
| **Proposed By** | Engineering |
| **Date** | 2026-03-25 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris architecture modeling tool, which needs to support optional integrations with third-party tools like roadmapping software,

**facing** the need for a clean, extensible mechanism to install, enable, disable, and manage optional integrations without coupling them to the core codebase,

**we decided for** a database-backed extensions registry with an admin UI, where each extension is registered with metadata (name, version, enabled status) and can be toggled without redeployment,

**and neglected** plugin-based dynamic loading (over-engineered for a small set of known extensions), config-file-only toggles (no admin UI, no audit trail), and feature flags (too generic, no install/uninstall semantics),

**to achieve** a maintainable integration pattern where extensions can be installed/uninstalled by administrators, their state persists across restarts, and API endpoints can be gated on extension availability,

**accepting that** this introduces a new database table and admin page, and that the initial implementation supports a fixed set of known extensions rather than arbitrary plugin discovery.

---

## Summary

| Capability | Description | Specification |
|------------|-------------|---------------|
| Extension Registry | Database table storing installed extensions with metadata | [SPEC-103-A](./specs/SPEC-103-A-Extension-Registry.md) |
| Extension CRUD API | REST endpoints to install, uninstall, enable, disable, list extensions | [SPEC-103-A](./specs/SPEC-103-A-Extension-Registry.md) |
| Admin UI | Extensions management page in the admin section | [SPEC-103-A](./specs/SPEC-103-A-Extension-Registry.md) |
| Extension Gating | FastAPI dependency to gate routes on extension availability | [SPEC-103-A](./specs/SPEC-103-A-Extension-Registry.md) |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Enables | ADR-104 | Scenia Schema Mapping | First extension to use this framework |
| Relates To | ADR-004 | Backend Stack | Extensions follow FastAPI module patterns |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-103-A | Extension Registry | Technical Specification | [specs/SPEC-103-A-Extension-Registry.md](./specs/SPEC-103-A-Extension-Registry.md) |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Engineering | 2026-03-25 |
| Approved | Chris Barlow | 2026-03-25 |
