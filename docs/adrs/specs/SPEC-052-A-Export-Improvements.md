# SPEC-052-A: Export Improvements

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-052-A |
| **ADR Reference** | [ADR-052: Export Improvements](../ADR-052-Export-Improvements.md) |
| **Date** | 2026-03-01 |
| **Status** | Accepted |

---

## Overview

This specification details two export improvements: (1) replacing the current SVG-based export with `html-to-image` for full viewport capture that includes all visible nodes and edges regardless of viewport scroll position, and (2) making the export button visible in both edit and browse mode so that all users can export model diagrams.

---

## A. html-to-image Library Integration

### Dependency

**Package:** `html-to-image`

```bash
npm install html-to-image
```

### Why html-to-image

The current export approach extracts the SVG element from the @xyflow canvas, which misses:
- Nodes rendered as HTML overlays (via `<foreignObject>` or the HTML node layer)
- Edge labels rendered via `EdgeLabelRenderer` (DOM-based, not SVG)
- Custom CSS-styled elements that do not translate to pure SVG

`html-to-image` captures the entire DOM subtree as a raster image, including all HTML overlays, CSS styling, and positioned elements.

### Export Functions

**File:** `src/lib/canvas/export-utils.ts`

```typescript
import { toPng, toSvg } from 'html-to-image';

export async function exportCanvasAsPng(
    canvasElement: HTMLElement,
    filename: string
): Promise<void> {
    const dataUrl = await toPng(canvasElement, {
        backgroundColor: 'white',
        pixelRatio: 2, // High-DPI export
        filter: (node: HTMLElement) => {
            // Exclude toolbar, controls, and minimap from export
            const excludeClasses = [
                'svelte-flow__controls',
                'svelte-flow__minimap',
                'canvas-toolbar',
            ];
            return !excludeClasses.some((cls) =>
                node.classList?.contains(cls)
            );
        },
    });
    downloadDataUrl(dataUrl, `${filename}.png`);
}

export async function exportCanvasAsSvg(
    canvasElement: HTMLElement,
    filename: string
): Promise<void> {
    const dataUrl = await toSvg(canvasElement, {
        backgroundColor: 'white',
        filter: (node: HTMLElement) => {
            const excludeClasses = [
                'svelte-flow__controls',
                'svelte-flow__minimap',
                'canvas-toolbar',
            ];
            return !excludeClasses.some((cls) =>
                node.classList?.contains(cls)
            );
        },
    });
    downloadDataUrl(dataUrl, `${filename}.svg`);
}

function downloadDataUrl(dataUrl: string, filename: string): void {
    const link = document.createElement('a');
    link.download = filename;
    link.href = dataUrl;
    link.click();
}
```

### Viewport Preparation

Before capturing, the canvas should be fitted to show all nodes so the export includes the complete diagram:

```typescript
import { useSvelteFlow } from '@xyflow/svelte';

export async function exportWithFitView(
    svelteFlow: ReturnType<typeof useSvelteFlow>,
    canvasElement: HTMLElement,
    filename: string,
    format: 'png' | 'svg'
): Promise<void> {
    // Fit all nodes into view before capture
    svelteFlow.fitView({ padding: 0.1, duration: 0 });

    // Wait for layout to settle
    await new Promise((resolve) => requestAnimationFrame(resolve));

    if (format === 'png') {
        await exportCanvasAsPng(canvasElement, filename);
    } else {
        await exportCanvasAsSvg(canvasElement, filename);
    }
}
```

### Filter Function

The `filter` option excludes UI chrome from the export:

| Excluded Element | CSS Class | Reason |
|-----------------|-----------|--------|
| Zoom controls | `svelte-flow__controls` | Interactive UI, not part of diagram |
| Minimap | `svelte-flow__minimap` | Navigation aid, not diagram content |
| Toolbar | `canvas-toolbar` | Edit controls, not diagram content |

---

## B. Export Button Visibility

### Current Behaviour

The export button/dropdown is only rendered when `$canvasMode === 'edit'`, limiting exports to users with edit permissions.

### Updated Behaviour

The export button is visible in both edit and browse mode, allowing all users (including Viewers and Reviewers) to export diagrams.

**File:** `src/routes/models/[id]/+page.svelte` (toolbar section)

```svelte
<!-- Export group - visible in both edit and browse mode -->
<div class="flex items-center gap-2">
    <button
        onclick={handleExport}
        class="rounded px-3 py-1.5 text-sm"
        style="border: 1px solid var(--color-border); color: var(--color-text)"
        aria-label="Export diagram"
    >
        Export
    </button>
</div>
```

### Conditional Placement

The export button is placed:
- **Edit mode:** Within the existing toolbar alongside other edit controls
- **Browse mode:** In a minimal toolbar or standalone position above the canvas

If the toolbar itself is mode-gated, the export button must be extracted to a section that renders regardless of mode:

```svelte
<!-- Always-visible toolbar section -->
<div class="canvas-actions">
    {#if $canvasMode === 'edit'}
        <!-- Edit-only buttons: Delete, Undo, Redo, etc. -->
    {/if}
    <!-- Export always visible -->
    <button onclick={handleExport}>Export</button>
</div>
```

---

## C. Export Format Options

### Supported Formats

| Format | Method | Notes |
|--------|--------|-------|
| PNG | `toPng()` | Raster, 2x pixel ratio for retina displays |
| SVG | `toSvg()` | Vector, best for further editing |
| PDF | Deferred | Placeholder in dropdown, disabled |
| Visio | Deferred | Placeholder in dropdown, disabled |
| Draw.io | Deferred | Placeholder in dropdown, disabled |

The existing export dropdown structure (with disabled placeholders for Visio, Draw.io, PDF) is preserved. Only the PNG and SVG handlers are updated to use `html-to-image`.

---

## D. Error Handling

```typescript
async function handleExport(format: 'png' | 'svg' = 'png') {
    const canvasEl = document.querySelector('.svelte-flow') as HTMLElement;
    if (!canvasEl) {
        error = 'Canvas element not found';
        return;
    }
    try {
        const filename = sanitizeFilename(modelName);
        await exportWithFitView(svelteFlow, canvasEl, filename, format);
    } catch (e) {
        error = e instanceof Error ? e.message : 'Export failed';
    }
}
```

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| PNG export captures all nodes | Create model with nodes at various positions; export PNG; verify all nodes visible |
| PNG export captures edge labels | Add edge labels; export PNG; verify labels visible in output |
| PNG export excludes toolbar | Export PNG; verify no toolbar buttons in image |
| PNG export excludes minimap | Export PNG; verify no minimap in image |
| PNG export excludes zoom controls | Export PNG; verify no zoom controls in image |
| SVG export captures full viewport | Export SVG; verify complete diagram |
| Export button visible in edit mode | Switch to edit mode; verify export button present |
| Export button visible in browse mode | Switch to browse mode; verify export button present |
| Viewer role can export | Log in as viewer; verify export button functional |
| Fit-to-view before export | Zoom in to partial view; export; verify full diagram in output |
| Filename based on model name | Export model named "My Architecture"; verify file named `My-Architecture.png` |
| Error message on export failure | Simulate failure; verify error displayed |
| html-to-image dependency installed | Verify `html-to-image` in `package.json` dependencies |

---

*This specification implements [ADR-052](../ADR-052-Export-Improvements.md).*
