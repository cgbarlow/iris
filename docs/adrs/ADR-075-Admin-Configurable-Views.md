# ADR-075: Admin-Configurable Views

## Proposal: Named UI visibility profiles that control which features are shown

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-075 |
| **Initiative** | SparxEA Gap Closure |
| **Proposed By** | Architecture Team |
| **Date** | 2026-03-04 |
| **Status** | Approved |
| **Dependencies** | ADR-071, ADR-074 |

---

## ADR (WH(Y) Statement format)

**In the context of** Iris supporting multiple notations (UML, ArchiMate, C4, Simple) with many configurable features (cardinality, role names, stereotypes, extended metadata, edge properties),

**facing** users who may be overwhelmed by advanced features they don't need, and administrators who want to tailor the UI for different audiences,

**we decided for** admin-configurable Views — named profiles with a JSON config controlling toolbar element/relationship types, metadata section visibility, and canvas feature visibility — stored in a `views` table with a REST API, global Svelte store, and admin CRUD page,

**and neglected** per-user UI preferences (too granular, hard to maintain consistency) and hardcoded view modes (not extensible),

**to achieve** a flexible, admin-managed way to simplify or expand the UI without code changes, with two default views (Standard: simplified, Advanced: full),

**accepting that** views are cosmetic filters only — they hide UI features but never delete data.

---

## Decisions

1. **Views table**: `id`, `name`, `description`, `config` (JSON), `is_default`, `created_by`, timestamps
2. **Two default views**: Standard (hides extended metadata, cardinality, roles, stereotypes, advanced types) and Advanced (everything visible)
3. **View config schema**: `toolbar` (element_types, relationship_types, show_routing_type, show_edge_properties), `metadata` (show_overview, show_details, show_extended), `canvas` (show_cardinality, show_role_names, show_stereotypes, show_description_on_nodes)
4. **REST API**: GET/POST/PUT/DELETE on `/api/views`, default views cannot be deleted
5. **Frontend store**: `viewStore.svelte.ts` with reactive state, localStorage persistence of active view ID
6. **ViewSelector**: Dropdown in top nav for switching active view
7. **Admin page**: `/admin/views` for CRUD operations on views

---

## Specification

See [SPEC-075-A](../specs/SPEC-075-A-Views-Backend.md) and [SPEC-075-B](../specs/SPEC-075-B-Views-Frontend.md).
