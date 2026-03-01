# SPEC-039-A: Model Export Implementation

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-039-A |
| **ADR Reference** | [ADR-039: Model Export](../ADR-039-Model-Export.md) |
| **Date** | 2026-03-01 |
| **Status** | Active |

---

## Overview

This specification details the implementation of client-side model export for the Iris canvas. Users can export their diagrams as SVG, PNG, or PDF files directly from the canvas toolbar. Two additional formats (Visio, Draw.io) are shown as disabled placeholders for future implementation.

---

## A. Export Utility Module

### Location

`frontend/src/lib/utils/export.ts`

### Functions

#### `sanitizeFilename(name: string): string`

Removes characters that are unsafe for filenames (anything not alphanumeric, hyphen, underscore, space, or dot). Returns `'export'` if the result would be empty.

#### `extractSvgString(flowElement: HTMLElement): string`

Finds the SVG element inside the `.svelte-flow` container, clones it, sets proper dimensions and xmlns attribute, and serialises it to an XML string. Throws if no SVG is found.

#### `exportToSvg(flowElement: HTMLElement, filename: string): void`

Extracts the SVG string and triggers a download as an `.svg` file.

#### `svgToPngBlob(svgString: string, width: number, height: number): Promise<Blob>`

Loads the SVG into an Image element, draws it onto an offscreen canvas with a white background, and returns the resulting PNG as a Blob.

#### `exportToPng(flowElement: HTMLElement, filename: string): Promise<void>`

Extracts SVG, converts to PNG via `svgToPngBlob`, and triggers a download.

#### `exportToPdf(flowElement: HTMLElement, filename: string, modelName: string): Promise<void>`

Extracts SVG, converts to PNG, creates a PDF document using jsPDF with the model name as title, embeds the PNG image, and triggers a download.

---

## B. Frontend Dependency

### jsPDF

Added as a production dependency: `npm install jspdf`

Used for PDF generation in `exportToPdf`. The library creates PDF documents entirely in the browser.

---

## C. Export Dropdown UI

### Location

Model detail page: `frontend/src/routes/models/[id]/+page.svelte`

### Placement

In the canvas toolbar's "View group" (right side, near the Focus button), visible only when `editing` is true.

### Behaviour

- A toggle button labelled "Export" opens/closes a dropdown menu
- Clicking outside the dropdown closes it
- Available options: SVG, PNG, PDF (enabled), Visio, Draw.io (disabled with "Coming soon" title)
- Each enabled option calls the corresponding export function with a reference to the `.svelte-flow` container element
- The dropdown uses relative positioning with absolute dropdown panel

### State

```typescript
let showExportMenu = $state(false);
```

### Obtaining the Flow Element

The export functions require a reference to the `HTMLElement` containing the `.svelte-flow` canvas. This is obtained at export time by querying `document.querySelector('.svelte-flow')` to find the active canvas container.

---

## D. Disabled Format Buttons

Visio and Draw.io buttons are rendered with:
- `disabled` attribute
- `title="Coming soon"` tooltip
- Reduced opacity via `disabled:opacity-50` class

These serve as visible indicators of the product roadmap without functional implementation.

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| Export dropdown visible in edit mode | Enter edit mode on canvas tab; verify Export button appears in toolbar |
| Export dropdown hidden in browse mode | View canvas in browse mode; verify no Export button |
| SVG export downloads a valid SVG file | Click Export > SVG; verify downloaded file is valid SVG |
| PNG export downloads a PNG image | Click Export > PNG; verify downloaded file is valid PNG |
| PDF export downloads a PDF with title | Click Export > PDF; verify PDF contains model name and diagram image |
| Visio button is disabled | Verify Visio option has disabled attribute and "Coming soon" title |
| Draw.io button is disabled | Verify Draw.io option has disabled attribute and "Coming soon" title |
| Filename is sanitised | Export a model with special characters in name; verify filename is safe |
| Dropdown closes on outside click | Open dropdown; click outside; verify it closes |

---

*This specification implements [ADR-039](../ADR-039-Model-Export.md).*
