# ADR-128: Server-Side Export (JSON + Markdown)

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-128 |
| **Initiative** | Agentic-AI-friendly API (Issue #21) |
| **Proposed By** | Engineering |
| **Date** | 2026-04-22 |
| **Status** | Proposed |

---

## ADR (WH(Y) Statement format)

**In the context of** ADR-039 shipping export as a **client-side**
feature — `exportSvg()` / `exportPng()` / `exportPdf()` pull DOM
content from the @xyflow/svelte canvas in the browser, convert via
native APIs + jsPDF, and trigger a download — which is exactly the
right design for a human clicking an "Export" button but yields
nothing for a headless caller (CLI, MCP tool, or AI agent) because
there is no browser, no DOM, no rendered canvas, and no access to the
canvas state from outside a logged-in SvelteKit session,

**facing** the requirement from Issue #21 that agentic AI tools be able
to extract meaningful data and insights from Iris as a resource —
meaning they need to be able to pull a diagram, a package, a set, or
a collection as structured text (to feed into their own context
window, commit to a repo, or send to another model), and to do so over
the HTTP API with a bearer token and no browser; and facing the DRY
constraint that any export implementation must reuse the existing
Pydantic response models rather than re-serialising entities,

**we decided for** introducing a **new `/api/export/*` router** that
exposes server-side export in **JSON** and **Markdown** formats for
five entity granularities — diagram, element, package, set, collection
— implemented as:
(a) a JSON renderer that reuses existing `ElementResponse` /
`DiagramResponse` / `PackageResponse` / `SetResponse` /
`CollectionResponse` Pydantic models and assembles them into bundle
schemas (e.g. a set export includes its packages, diagrams, elements,
and the relationships between them) — a single source of truth for
the on-the-wire schema;
(b) a Markdown renderer implemented as one deterministic template
function per entity type (`export/markdown.py`) producing H1 title +
metadata table + description + tags + relationships table + linked
diagrams list — suitable for pasting into a PR, a wiki, or an AI
context window;
(c) `Content-Disposition: attachment; filename="{name-kebab}-{id}.{json|md}"`
headers so curl / `iris export` / MCP tools write sensible filenames
on disk without client-side parsing;
(d) auth via `get_optional_user` — anonymous callers can export
anything that is already anonymously readable under ADR-123, keeping
parity with the existing list/get endpoints;
(e) a 10,000-element cap per bundle with a clear 413-style error and
a pointer to page the underlying list endpoints instead — prevents a
single export from dragging the server for hundreds of megabytes;
(f) **this ADR complements ADR-039; it does not supersede it** — the
canvas visual export stays exactly where it is for human users in the
browser, and server-side export covers headless callers only;
(g) v1 ships **JSON + Markdown only**; SVG / PNG / Mermaid are
deferred (a future ADR) because they require a rendering pipeline
that does not yet exist server-side (cairosvg is currently used only
for thumbnails, which are small and cached),

**and neglected** (a) **SVG / PNG / PDF server-side rendering** —
needed if we want to guarantee pixel-perfect visual parity with the
canvas in environments with no browser (e.g. a CI job producing docs),
but requires either a headless browser container or a dedicated SVG
templater that reimplements the canvas rendering — both are a
multi-ADR effort and not on the v1 agentic path; (b) **Mermaid text
output** — useful for pasting diagrams into GitHub PR bodies and
existing doc tooling, but requires a mapper from every Iris notation
(Simple / UML / ArchiMate / Sequence / C4 / DoView) to Mermaid syntax,
which is its own workstream — deferred; (c) **overloading the existing
`GET /api/diagrams/{id}` with a `?format=` switch** — blurs the
semantics of "fetch the entity record" vs "produce a portable
snapshot" and forces every response model to carry export logic;
keeping `/api/export/*` as a separate router isolates the concern;
(d) **stream-as-you-go chunked export** — a nice-to-have for very large
bundles, but hitting the 10k-element cap is rare and easy to page
around; (e) **write-back import from exported JSON** — the inverse of
export; Iris already has SparxEA and DoView importers (ADR-059,
ADR-107) for that purpose; Iris-native import is a future ADR,

**to achieve** a headless export path agents and CLIs can use with a
plain Bearer token, JSON output that round-trips through Pydantic
cleanly (so tools can parse it with `iris-client` models), Markdown
output that drops straight into a PR/doc/AI context, deterministic
filenames, parity with anonymous-read policy, and zero disruption to
the existing client-side export flow that human users already depend
on,

**accepting that** server-side export adds a new router (~5 endpoints)
plus a Markdown templater (~100 lines per entity type) that must be
kept in sync as new entity fields are added — mitigated by snapshot
tests on the Markdown output and by reusing Pydantic models for JSON;
accepting that visual export remains browser-only for now — the two
worlds don't collide because the paths are disjoint (`/api/export/*`
vs the frontend's `canvas/export.ts`); accepting the 10k-element cap
will cut off very large set exports — acceptable for v1 and revisitable
once real usage shows where the ceiling should sit.

---

## Summary

| Capability | Description | Specification |
|------------|-------------|---------------|
| `/api/export/*` router | Five endpoints: `diagrams/{id}`, `elements/{id}`, `packages/{id}`, `sets/{id}`, `collections/{id}`. Query param `format=json\|markdown`. Auth: `get_optional_user`. | [SPEC-128-A](./specs/SPEC-128-A-Server-Side-Export.md) |
| JSON renderer | Reuses existing response Pydantic models. Bundle schemas defined in SPEC-128. | SPEC-128-A |
| Markdown renderer | `export/markdown.py` — one template per entity type. Deterministic output (golden-file tested). | SPEC-128-A |
| Content-Disposition | `attachment; filename="{name-kebab}-{id}.{json\|md}"` — CLI / curl friendly. | SPEC-128-A |
| Bundle size cap | 10,000 elements per bundle. 413 on overflow with a hint to page. | SPEC-128-A |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Complements | ADR-039 | Model Export | Client-side visual export remains in force for browser users; this ADR covers headless text/structure export only. |
| Complements | ADR-052 | Export Improvements | Client-side SVG/PNG/PDF improvements remain unchanged. |
| Depends On | ADR-123 | Anonymous Read-Only Bypass | Export inherits the same anonymous-read policy as list/get. |
| Enables | ADR-130 | CLI Architecture | `iris export diagram\|element\|package\|set\|collection <id> --format json\|markdown`. |
| Enables | ADR-131 | MCP Server Architecture | MCP `export_*` tools + `iris://` resources resolve to these endpoints. |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-128-A | Server-Side Export Implementation | Technical Specification | [specs/SPEC-128-A-Server-Side-Export.md](./specs/SPEC-128-A-Server-Side-Export.md) |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Engineering | 2026-04-22 |
