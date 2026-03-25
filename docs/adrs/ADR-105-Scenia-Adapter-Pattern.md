# ADR-105: Scenia Adapter Pattern

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-105 |
| **Initiative** | Scenia Adapter Pattern |
| **Proposed By** | Engineering |
| **Date** | 2026-03-25 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** integrating the Scenia React roadmapping app into Iris's SvelteKit frontend,

**facing** the need to replace Scenia's IndexedDB storage with Iris's API-backed database while keeping Scenia's React UI unchanged,

**we decided for** an adapter layer that implements Scenia's db.ts interface (getAppData/saveAppData) using fetch calls to /api/scenia/data, plus React-in-Svelte mounting via createRoot,

**and neglected** iframe embedding (no auth sharing, poor UX), full rewrite in Svelte (too expensive), and direct Scenia modification (breaks upstream compatibility),

**to achieve** seamless integration where Scenia thinks it's using local storage but data actually lives in Iris's database,

**accepting that** this requires React as a peer dependency alongside Svelte, and that Scenia source may need minimal patches for external mounting.

---

## Summary

| Capability | Description |
|------------|-------------|
| Adapter Layer | Replaces Scenia's db.ts with API-backed fetch calls |
| React-in-Svelte | Mount Scenia React app inside SvelteKit route via createRoot |
| Auth Bridge | Passes Iris auth tokens to API calls transparently |
| Set Awareness | Scenia reads from and writes to the active Iris set |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Extends | ADR-103 | Extensions Framework | Scenia is an extension managed by the registry |
| Extends | ADR-104 | Scenia Schema Mapping | Adapter calls the bulk data API defined here |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Engineering | 2026-03-25 |
| Approved | Chris Barlow | 2026-03-25 |
