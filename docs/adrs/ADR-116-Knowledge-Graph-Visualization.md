# ADR-116: Knowledge Graph Visualization

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-116 |
| **Initiative** | Knowledge Graph |
| **Proposed By** | Engineering |
| **Date** | 2026-04-03 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** Iris as an enterprise architecture tool where elements are connected via typed relationships, and users need to visualise the topology of their architecture at a glance,

**facing** the lack of a global view showing how elements in a set relate to each other — existing views are list-based (elements page) or diagram-scoped (canvas editor), neither of which reveals the full relationship network,

**we decided for** embedding a force-directed knowledge graph on the dashboard page using the `force-graph` npm library (Canvas-based, d3-force under the hood), backed by a new `GET /api/graph` endpoint that returns all elements and relationships for a set in a single call,

**and neglected** (a) reusing @xyflow/svelte — DOM-based, poor performance at hundreds of nodes, designed for editors not network visualisation; (b) 3D force graph — unnecessary complexity, accessibility concerns; (c) Kumu.io embedding — external dependency, no customisation, data privacy concerns; (d) separate /graph route — less discoverable than embedding on the dashboard,

**to achieve** a Kumu.io-style interactive network visualisation showing element relationships with click-to-navigate, hover tooltips, drag-to-rearrange, zoom/pan, colour-coded by element type, theme-aware, and performant at hundreds of nodes,

**accepting that** Canvas rendering means no DOM accessibility for individual nodes (mitigated by the elements list view as an accessible alternative), the graph layout is non-deterministic (force simulation varies each time), and the graph section only appears when a set or collection is active.

---

## Summary

| Capability | Description | Specification |
|------------|-------------|---------------|
| Graph Data API | GET /api/graph endpoint returning nodes + edges for a set | [SPEC-116-A](./specs/SPEC-116-A-Graph-Data-API.md) |
| Knowledge Graph Component | force-graph Svelte 5 wrapper on dashboard | [SPEC-116-B](./specs/SPEC-116-B-Knowledge-Graph-Component.md) |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Relates To | ADR-003 | Entity Domain Model | Elements and relationships as graph data |
| Relates To | ADR-012 | Sets | Set-scoped graph queries |
| Relates To | ADR-102 | Collections | Collection-scoped graph queries |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-116-A | Graph Data API | Technical Specification | [specs/SPEC-116-A-Graph-Data-API.md](./specs/SPEC-116-A-Graph-Data-API.md) |
| SPEC-116-B | Knowledge Graph Component | Technical Specification | [specs/SPEC-116-B-Knowledge-Graph-Component.md](./specs/SPEC-116-B-Knowledge-Graph-Component.md) |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Engineering | 2026-04-03 |
| Approved | Engineering | 2026-04-03 |
