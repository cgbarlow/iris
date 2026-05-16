# ADR-181: Unified diagram export options in the GUI

Status: Accepted (2026-05-16)
Supersedes (partially): the jsPDF rasterised-pdf path in `frontend/src/lib/utils/export.ts`.
Extends: ADR-179.

## Context

Before Phase 5 of issue #133, the diagram view's Export menu offered:

- **SVG** — client-side `html-to-image` capture of the canvas. Visual.
- **PNG** — client-side `html-to-image`. Visual.
- **PDF** — client-side jsPDF wrapping the PNG. Visual (rasterised).
- (disabled) Visio, Draw.io — placeholder entries.

The PDF path was always a screenshot of the canvas inside an A4 sheet — not a "real" PDF document. For markdown-content diagrams (the new `notation='markdown'` family from m051 onwards — `doview_analysis` and friends), rasterising a markdown viewer is silly: the source IS text, and text PDFs are the right output shape.

Phase 2 (v6.2.0, ADR-179) shipped the server-side renderer that does proper md → docx / pdf via python-docx + weasyprint. Phase 5 brings the GUI Export menu up to par.

## Decision

Add a reusable `DiagramExportMenu.svelte` component and switch the export pipeline to the right code path per diagram type:

| Format | Markdown-content diagrams | Visual diagrams |
|---|---|---|
| Markdown (.md) | Server-rendered via `POST /api/export/markdown` (or `/api/export/diagram/{id}?format=md` for saved diagrams) | Server-rendered summary via the same endpoint |
| Docx (.docx) | Server-rendered via Phase 2 endpoint | Server-rendered summary via the same endpoint |
| PDF (.pdf) | Server-rendered via Phase 2 endpoint (REAL text PDF) | Server-rendered summary via the same endpoint |
| SVG | n/a (no canvas) | Client-side `html-to-image` (retained) |
| PNG | n/a | Client-side `html-to-image` (retained) |
| Visio / Draw.io | (disabled, "coming soon") | (disabled) |

The jsPDF rasterised-pdf path is **removed**. For visual diagrams, users who want a screenshot can still pick PNG. The "PDF" menu entry now always produces a proper text-based PDF using the server renderer.

### Component contract

```svelte
<DiagramExportMenu
  diagramId={diagram.id}
  diagramName={diagram.name}
  isMarkdownContent={diagram.notation === 'markdown'}
  flowElement={getFlowElement}
/>
```

- `diagramId` — for the server-render endpoint.
- `diagramName` — for filename slugification (the server already does this; the prop is for the menu label tooltip).
- `isMarkdownContent` — controls whether SVG/PNG menu items are shown (hidden for markdown notation).
- `flowElement` — `() => HTMLElement | null` getter, used by SVG/PNG client-side capture.

### Export hand-off

The menu component returns the artefact URL from the backend and triggers a browser download via the standard `<a download>` pattern. No bytes flow through Svelte — the browser fetches from `/api/artefacts/<id>` directly with the existing auth cookie. (Phase 2's `GET /api/artefacts/{id}` is auth-optional, so anonymous browse-mode works too.)

## Why not also remove SVG/PNG

The client-side SVG/PNG capture gives the user a literal screenshot of what they see — useful for slides, screenshots in tickets, etc. The server can't produce that (it has the canvas data but not the rendered DOM). Two distinct affordances; both valuable.

## Why retain disabled Visio / Draw.io entries

Marker for future work — users can see we're aware of those formats and they're not just missing from the menu by oversight. Future ADR adds them if the demand justifies the import logic.

## Consequences

- New `frontend/src/lib/components/DiagramExportMenu.svelte` (~100 LoC).
- `frontend/src/lib/utils/export.ts` keeps `exportToSvg` and `exportToPng`. `exportToPdf` (jsPDF) is removed. A new `exportDiagramAsArtefact(diagramId, format)` helper hits the backend.
- `frontend/src/routes/views/[id]/+page.svelte` replaces the inline menu with `<DiagramExportMenu>`. The three `handleExport*` functions stay for SVG/PNG, the PDF handler becomes a no-op (replaced by component-internal logic) and is removed.
- `frontend/package.json` no longer needs `jspdf` if nothing else uses it. Audit at Phase 5 close; remove the dep if free of references.
- `frontend/tests/e2e/diagram-export.spec.ts` exercises the new menu — open a markdown-content diagram, click Export → Docx, verify the download is a real docx (server returns valid bytes).
- CHANGELOG `[6.5.0]`.
- Version bumps: mcp + frontend 6.4.0 → 6.5.0.

## Verification

- E2E spec asserts docx download is a valid ZIP (`PK\x03\x04` header).
- Manual: open a markdown diagram → Export → PDF → file is a proper text PDF.
- Manual: open a visual diagram → Export → SVG/PNG still produce the canvas screenshot.
- Byte-equality between GUI-downloaded docx, CLI `iris render diagram <id> --format docx`, and MCP `render_diagram(<id>, "docx")` — same renderer code path (Phase 6 parity script asserts this).

## See also

- [ADR-179](ADR-179-Renderer-And-Artefact-Store.md) — backend renderer the new menu calls.
- [SPEC-181-A](specs/SPEC-181-A-Unified-Diagram-Export-GUI.md) — component contract, layout, test plan.
- Issue #133.
