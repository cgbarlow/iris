# ADR-106: Scenia React Embedding

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-106 |
| **Initiative** | Scenia React Embedding |
| **Proposed By** | Engineering |
| **Date** | 2026-03-25 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** integrating the Scenia React roadmapping app into Iris's SvelteKit frontend,

**facing** the need to embed the full Scenia React UI (not just a data view) at `/scenia` while maintaining an Iris-native data view at `/roadmap`,

**we decided for** patching the Scenia fork (cgbarlow/waylonkenning_scenia) with a pluggable db adapter and `embed.tsx` entry point, mounting via React's `createRoot` inside a SvelteKit route, with CSS isolation via scoped Tailwind theme variables,

**and neglected** iframe embedding (no auth sharing, poor UX), full Svelte rewrite (too expensive), direct source copy (breaks upstream compatibility), and shadow DOM mounting (complications with portals and modals),

**to achieve** a fully functional Scenia roadmapping experience embedded within Iris, backed by Iris's database, with bidirectional cross-links between the two UIs,

**accepting that** React becomes a runtime dependency alongside Svelte, Tailwind CSS requires careful isolation between the two apps, and the fork must be maintained for embedding patches.

---

## Summary

| Capability | Description | Specification |
|------------|-------------|---------------|
| Pluggable DB Adapter | Fork's db.ts accepts external adapter to bypass IndexedDB | [SPEC-106-A](./specs/SPEC-106-A-Scenia-Embedding.md) |
| Library Build | Fork builds as ES module for embedding via npm install | [SPEC-106-A](./specs/SPEC-106-A-Scenia-Embedding.md) |
| React-in-Svelte Mount | createRoot mounting inside SvelteKit route with lifecycle cleanup | [SPEC-106-A](./specs/SPEC-106-A-Scenia-Embedding.md) |
| CSS Isolation | Scenia theme variables scoped to avoid Iris Tailwind conflicts | [SPEC-106-A](./specs/SPEC-106-A-Scenia-Embedding.md) |
| Dual Routes | /scenia (React app) + /roadmap (Iris data view) | [SPEC-106-A](./specs/SPEC-106-A-Scenia-Embedding.md) |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Supersedes | ADR-105 | Scenia Adapter Pattern | Replaces adapter-only approach with full fork patching strategy |
| Extends | ADR-103 | Extensions Framework | Scenia is an extension managed by the registry |
| Extends | ADR-104 | Scenia Schema Mapping | Uses the schema mapping and bulk data API defined here |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-106-A | Scenia Embedding | Technical Specification | [specs/SPEC-106-A-Scenia-Embedding.md](./specs/SPEC-106-A-Scenia-Embedding.md) |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Engineering | 2026-03-25 |
| Approved | Chris Barlow | 2026-03-25 |
