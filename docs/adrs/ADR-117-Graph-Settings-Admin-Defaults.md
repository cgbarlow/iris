# ADR-117: Graph Settings & Admin Defaults

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-117 |
| **Initiative** | Knowledge Graph |
| **Proposed By** | Engineering |
| **Date** | 2026-04-03 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** the knowledge graph (ADR-116) where the force-directed layout uses hard-coded physics constants for charge strength, link distance, and node sizing, and the settings panel only exposes node/edge visibility toggles,

**facing** the need for administrators to tune the graph's visual density and spacing for their organisation's architecture data (which varies widely in node count and connectivity), and the inability for users to adjust how spread-out, how labelled, or how size-differentiated the graph appears without code changes,

**we decided for** extending the `GraphSettings` interface with four numeric physics/display parameters (label density, node spacing, size contrast, link length), persisting admin-configurable defaults in a new `graph_settings` database table scoped by global/collection/set, exposing GET/PUT API endpoints for those defaults, and adding slider controls plus "Save as default" / "Reset to defaults" action buttons to the settings panel,

**and neglected** (a) reusing the flat `settings` key-value table — graph settings are scoped JSON documents with a composite key (scope_type + scope_id) and structured values, not scalar key-value pairs, making the flat table a poor fit; (b) localStorage-only persistence — provides no admin control over cross-user defaults and leaves every new user with uncalibrated values; (c) a full user preferences system with per-user rows and a preferences API — overengineered for four numeric sliders and no other user preference exists in the system yet,

**to achieve** administrator-tunable graph physics that cascade (hard-coded defaults, then admin DB defaults, then user localStorage overrides) so that organisations get a well-tuned default view out of the box while individual users can still personalise their experience,

**accepting that** the settings cascade introduces a three-layer merge (hard-coded, DB, localStorage) which adds complexity to the settings-read path, and that admin defaults are per-scope rather than per-user, so all non-admin users within a scope share the same baseline.

---

## Summary

| Capability | Description | Specification |
|------------|-------------|---------------|
| Graph Settings Backend | `graph_settings` table, service layer, and REST endpoints for admin defaults | [SPEC-117-A](./specs/SPEC-117-A-Graph-Settings-Backend.md) |
| Graph Settings Frontend | Extended settings type, slider UI, save/reset actions, cascade logic | [SPEC-117-B](./specs/SPEC-117-B-Graph-Settings-Frontend.md) |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Extends | ADR-116 | Knowledge Graph Visualization | Adds configurable physics to the existing force graph |
| Relates To | ADR-012 | Sets | Set-scoped graph defaults |
| Relates To | ADR-102 | Collections | Collection-scoped graph defaults |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-117-A | Graph Settings Backend | Technical Specification | [specs/SPEC-117-A-Graph-Settings-Backend.md](./specs/SPEC-117-A-Graph-Settings-Backend.md) |
| SPEC-117-B | Graph Settings Frontend | Technical Specification | [specs/SPEC-117-B-Graph-Settings-Frontend.md](./specs/SPEC-117-B-Graph-Settings-Frontend.md) |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Engineering | 2026-04-03 |
| Approved | Engineering | 2026-04-03 |

---

## Amendment 2026-05-11 — v5.7.1 Supabase resilience

UAT (Supabase mode) returned HTTP 500 from `GET /api/graph/settings`
for both anonymous and authenticated callers, because the
`_initialize_supabase` startup path did not call
`seed_graph_settings_defaults()` (only the SQLite path did) and the
`get_graph_settings_cascaded` read path raised an unhandled exception
when the underlying SELECT failed. The frontend's
`fetchAdminDefaults()` silently caught the error and fell back to
hard-coded defaults — which is invisible to admins (their
localStorage carries their saved settings) but observable to
anonymous users, who see "all on" instead of the admin-saved
visibility.

**Decisions:**

1. **Defensive reads.** `get_graph_settings_cascaded` and
   `get_graph_settings` now catch DB-layer exceptions and return
   hard-coded `GRAPH_SETTINGS_DEFAULTS` (with whatever scope rows
   were already merged in) rather than propagating to a 500. The
   endpoint stays alive even with a partially-migrated DB.
2. **Seed parity.** `_initialize_supabase` now calls
   `seed_graph_settings_defaults(port)` alongside the SQLite path, so
   the `__global__` row gets inserted on first Supabase start.
3. **Defensive seed.** `seed_graph_settings_defaults` also wraps the
   SELECT/INSERT in a try/except so a missing table or transient DB
   issue logs-and-skips rather than crashing startup.

**Out of scope (deferred):**

- Telemetry on the defensive-fallback path (count how often it fires
  in prod) — would help spot recurrences of the underlying issue.
- A migration that re-applies m039 idempotently from Python startup
  if the table is missing — currently relies on operator running
  `scripts/supabase-migrate.sh`.
