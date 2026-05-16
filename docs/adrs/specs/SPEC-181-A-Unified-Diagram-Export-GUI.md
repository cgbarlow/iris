# SPEC-181-A: Unified diagram export options in the GUI

ADR: [ADR-181](../ADR-181-Unified-Diagram-Export-GUI.md)

## Summary

Replace the inline Export menu in `frontend/src/routes/views/[id]/+page.svelte` with a reusable `DiagramExportMenu.svelte` component. Add server-rendered md/docx/pdf options (via Phase 2 backend endpoints) alongside the retained client-side SVG/PNG. Remove the jsPDF rasterised-pdf path.

## Component

`frontend/src/lib/components/DiagramExportMenu.svelte`:

```svelte
<script lang="ts">
  interface Props {
    diagramId: string;
    diagramName: string;
    isMarkdownContent?: boolean;
    flowElement?: () => HTMLElement | null;
  }
  let { diagramId, diagramName, isMarkdownContent = false, flowElement } = $props();
  let open = $state(false);
  let busy = $state<string | null>(null);

  async function renderServerSide(format: 'md' | 'docx' | 'pdf') {
    busy = format;
    try {
      const resp = await fetch(`/api/export/diagram/${diagramId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ format }),
      });
      if (!resp.ok) throw new Error(`Render failed: ${resp.status}`);
      const meta = await resp.json();
      // Trigger browser download by following the artefact URL.
      window.location.href = `/api/artefacts/${meta.id}`;
    } finally {
      busy = null;
      open = false;
    }
  }

  async function captureSvg() { /* call exportToSvg(flow, diagramName) */ }
  async function capturePng() { /* call exportToPng(flow, diagramName) */ }
</script>
```

Menu layout:

- Always: Markdown / Docx / PDF (server-rendered)
- If `!isMarkdownContent` AND `flowElement()` returns non-null: SVG / PNG (client-rasterised)
- Always disabled: Visio, Draw.io

The disabled entries stay for affordance / future work; remove them in a follow-up ADR if and when import paths exist.

## `frontend/src/lib/utils/export.ts` changes

- Remove the jsPDF import (`import { jsPDF } from 'jspdf';`).
- Remove the `exportToPdf` function (was the rasterised path).
- Keep `exportToSvg` and `exportToPng` unchanged — those are the client-rasterised options.
- Audit: if `jspdf` has no other importers in the repo, remove from `frontend/package.json`.

## Wiring in `+page.svelte`

Replace lines 2459–2482 (the inline Export menu dropdown) with:

```svelte
<DiagramExportMenu
  diagramId={diagram.id}
  diagramName={diagram.name}
  isMarkdownContent={diagram.notation === 'markdown'}
  flowElement={() => getFlowElement()}
/>
```

Repeat for the second inline menu at lines 2781–2789 (the focus-mode export).

The `handleExportPdf` function in `+page.svelte` (lines 1790–1796) becomes dead code. Remove it; the import of `exportToPdf` from `$lib/utils/export` is dropped too. The PDF behaviour now lives entirely inside `DiagramExportMenu`.

## E2E test

`frontend/tests/e2e/diagram-export.spec.ts`:

- Visit a markdown-content diagram (the existing test fixture set includes one — confirm at write time, or seed via the test setup).
- Click Export → Docx.
- Intercept the browser-initiated download.
- Assert the downloaded bytes start with `PK\x03\x04` (valid docx).
- Click Export → PDF.
- Assert bytes start with `%PDF`.

## Versioning

`mcp/pyproject.toml`: 6.4.0 → 6.5.0.
`frontend/package.json`: 6.4.0 → 6.5.0.

## CHANGELOG

`[6.5.0]` Added: unified DiagramExportMenu with server-rendered md/docx/pdf. Removed: jsPDF rasterised-pdf path. Changed: `frontend/src/lib/utils/export.ts` no longer depends on jsPDF.

## Acceptance criteria

- [ ] `DiagramExportMenu.svelte` exists; `+page.svelte` consumes it.
- [ ] `exportToPdf` removed from `export.ts`; no other importers.
- [ ] `jspdf` removed from `frontend/package.json` (if no other importers remain).
- [ ] E2E spec passes against a running backend.
- [ ] Manual: SVG/PNG still work on visual diagrams; PDF/docx work on markdown-content diagrams.
- [ ] No regressions in unrelated frontend tests.
