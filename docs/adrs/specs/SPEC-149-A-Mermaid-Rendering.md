# SPEC-149-A: Mermaid rendering in MarkdownView

ADR: [ADR-149](../ADR-149-Mermaid-In-Markdown-Renderer.md)

## Frontend file map

| Surface                          | File |
|---|---|
| `marked` mermaid extension       | `frontend/src/lib/components/markdownMermaidExtension.ts` |
| Lazy-load mermaid runner         | `frontend/src/lib/components/markdownMermaidRender.ts`    |
| Pipeline registration            | `frontend/src/lib/components/markdownHelpers.ts`          |
| Component wiring + styling       | `frontend/src/lib/components/MarkdownView.svelte`         |
| Mermaid library (lazy chunk)     | `frontend/node_modules/mermaid/` (dynamic `import('mermaid')`) |

## Rendering pipeline (post-v5.7.0)

```
markdown source
  → marked.parse({ async: false })       ← mermaid extension intercepts ```mermaid fences,
                                            emits <pre class="mermaid-block" data-mermaid-source="b64">
  → DOMPurify.sanitize({ ALLOWED_URI_REGEXP: /^(?:https?|mailto|iris):|… })
  → walk anchors → enforce URL-scheme allowlist + tag iris:// targets
  → walk imgs → enforce src allowlist
  → {@html}                              ← stage-1 done, placeholder is now in the DOM
  → MarkdownView.svelte $effect
     → runMermaidIn(rootEl, theme)
        → if no .mermaid-block: return
        → dynamic import('mermaid') (cached after first call)
        → mermaid.initialize({ securityLevel: 'strict', theme })
        → for each placeholder:
            → decode data-mermaid-source (base64)
            → mermaid.render(uniqueId, source) → svg
            → DOMPurify.sanitize(svg, { USE_PROFILES: { svg: true, svgFilters: true }, ADD_TAGS: ['foreignObject'] })   ← stage 2
            → placeholder.innerHTML = sanitisedSvg
            → on error: replace placeholder with <div class="mermaid-error">…</div>
```

## Placeholder contract

The marked extension emits exactly:

```html
<pre class="mermaid-block" data-mermaid-source="<base64>"><code>...escaped source...</code></pre>
```

| Attribute / class | Purpose |
|---|---|
| `class="mermaid-block"` | Selector used by the runner to find blocks. |
| `data-mermaid-source` | Base64-encoded original source. Base64 sidesteps quote/newline escaping pitfalls in HTML attributes and survives DOMPurify with default config. |
| Inner `<code>...</code>` | Holds the human-readable source so search/select-copy still works on the placeholder if for some reason mermaid never runs (e.g. no JS, lazy-load fails, SSR snapshot). |

The runner reads `data-mermaid-source`, base64-decodes, and renders.
The inner `<code>` is replaced when the SVG injects.

## Stage-1 DOMPurify (unchanged)

```ts
DOMPurify.sanitize(raw, {
  ALLOWED_URI_REGEXP: /^(?:(?:https?|mailto|iris):|\/|\.{1,2}\/)/i,
});
```

The placeholder uses `<pre>` + `class` + `data-*` attribute — all
covered by DOMPurify's default tag/attribute allowlist. No
configuration change at this stage.

## Stage-2 DOMPurify (new)

```ts
DOMPurify.sanitize(svg, {
  USE_PROFILES: { svg: true, svgFilters: true },
  ADD_TAGS: ['foreignObject'],
});
```

| Tag/attr | Why it's allowed |
|---|---|
| `<svg>`, `<g>`, `<path>`, `<rect>`, `<line>`, `<polygon>`, `<text>`, `<tspan>`, `<marker>`, `<defs>`, `<use>`, `<symbol>` | Default svg profile — needed for any mermaid SVG. |
| svg filter primitives | `svgFilters` profile — mermaid uses `<filter>` for drop-shadow effects. |
| `<foreignObject>` | Explicit add. Mermaid uses it for HTML labels in flowcharts. The HTML inside is mermaid-controlled because `securityLevel: 'strict'` disables user-authored HTML in labels. Stage-2 sanitisation still strips `<script>` / `onload` / `onerror` etc. inside foreignObject — verified by `markdownMermaidSvgSanitise.test.ts`. |

Tags **not** added: `<iframe>`, `<object>`, `<embed>`, `<script>`,
`<form>`. Inline event handlers (`onload`, `onerror`, `onclick`)
remain stripped by DOMPurify defaults.

## Mermaid configuration

```ts
mermaid.initialize({
  startOnLoad: false,           // we drive rendering ourselves
  securityLevel: 'strict',      // protocol #7 alignment
  theme: themeFor(rootEl),      // see "Theme integration" below
  suppressErrorRendering: true, // we render our own error placeholder
});
```

`startOnLoad: false` is critical — mermaid's default is to scan the
document for `.mermaid` selectors at load and render automatically.
We want our runner to be the only entry point so error handling and
sanitisation are centralised.

## Lazy-load contract

The mermaid bundle lives behind a dynamic `import('mermaid')` in
`markdownMermaidRender.ts`. The first call awaits the import; the
result is cached in module scope. Subsequent calls reuse the resolved
promise.

Vite produces a separate chunk for `mermaid` because it's a dynamic
import. The `vite build` output should show a chunk named like
`mermaid.<hash>.js` distinct from the main app chunk. This is verified
manually during release.

If a document contains zero `.mermaid-block` placeholders, the
dynamic import is **not** triggered. `markdownMermaidExtension.test.ts`
asserts this contract via `vi.mock('mermaid')` configured to fail if
called.

## Theme integration

Iris uses class-based theming (`frontend/src/app.css:15,27`):

| Theme | Class on `<html>` | Mermaid theme |
|---|---|---|
| Light (default) | (none) | `'default'` |
| Dark | `dark` | `'dark'` |
| High-contrast | `high-contrast` | `'dark'` (no high-contrast preset; closest match is dark with explicit overrides via `themeVariables` if needed) |

The runner reads `document.documentElement.classList` at render time
to derive the mermaid theme. A `MutationObserver` on
`document.documentElement.attributes` (filter to `class`) re-invokes
`runMermaidIn` when the theme class changes. The observer is created
once per `MarkdownView` mount and disposed on unmount.

## Error UX

When `mermaid.render(...)` throws (invalid syntax, unsupported diagram
type, etc.), the runner replaces the placeholder with:

```html
<div class="mermaid-error" role="alert">
  <strong>Mermaid render error:</strong>
  <code>{{ message }}</code>
</div>
```

Styling (in `MarkdownView.svelte` `<style>`):

```css
.md-view :global(.mermaid-error) {
  border: 1px solid var(--color-danger, #dc2626);
  background: var(--color-surface-hover, #f3f4f6);
  border-radius: 6px;
  padding: 8px 12px;
  color: var(--color-danger, #dc2626);
  font-family: ui-monospace, monospace;
  font-size: 0.92em;
}
```

The rest of the document continues to render — one bad mermaid block
does not break the whole view.

## Re-render hygiene

`MarkdownView` already runs `renderMarkdown` inside a `$derived`,
which re-runs whenever `source` changes. The new `$effect` watches
`html` and `theme` and re-invokes `runMermaidIn` on each change. To
avoid mermaid's "duplicate id" error, the runner uses a per-block
unique id derived from a monotonically incrementing module counter
plus a per-render salt.

Mermaid injects a small `<style>` tag into `<head>` on first render.
Subsequent renders reuse the same tag (mermaid de-dups). On
`MarkdownView` unmount we leave the style tag in place — removing it
would force a flash on the next mount.

## Component wiring

`MarkdownView.svelte` changes:

```svelte
<script lang="ts">
  // ... existing imports ...
  import { runMermaidIn } from './markdownMermaidRender';

  let rootEl: HTMLDivElement;

  // ... existing $derived blocks ...

  $effect(() => {
    // Re-run on html change (new content) or theme change
    if (!rootEl) return;
    void html;            // depend on html
    void currentTheme;    // depend on theme signal
    runMermaidIn(rootEl, currentTheme);
  });
</script>

<div bind:this={rootEl} class="md-view" onclick={onClick} role="presentation">
  {@html html}
</div>
```

CSS additions:

```css
.md-view :global(.mermaid-block) {
  background: transparent;
  padding: 0;
  border-radius: 0;
  overflow: visible;
}
.md-view :global(.mermaid-block svg) {
  max-width: 100%;
  height: auto;
}
```

The `.mermaid-block` rule overrides the existing `:global(pre)` rule
at lines 125-132 because the placeholder is itself a `<pre>`.

## Tests

| Test file | Coverage |
|---|---|
| `frontend/tests/unit/markdownMermaidExtension.test.ts` | Placeholder shape; base64 round-trip; non-mermaid fences untouched; mixed-content document; lazy-load contract (`vi.mock('mermaid')` asserts no import). |
| `frontend/tests/unit/markdownMermaidSvgSanitise.test.ts` | Stage-2 DOMPurify config preserves `<svg>/<g>/<path>/<marker>/<defs>/<foreignObject>`; strips `<script>` / `onload="..."` / `onerror="..."` even inside `foreignObject`. |
| `frontend/tests/unit/markdownViewMermaidComponent.test.ts` | Mounts `MarkdownView` with `vi.mock('mermaid')`; asserts placeholder swapped for SVG; invalid syntax produces `.mermaid-error`; rest of document renders; zero blocks → zero `mermaid` imports. |
| `frontend/tests/e2e/text-view-mermaid.spec.ts` | Playwright: create Text view with flowchart, browse-mode shows SVG, edit-mode shows source, theme switch re-renders. |
| `frontend/tests/e2e/user-guide-mermaid.spec.ts` | Playwright: User Guide page containing a mermaid block renders SVG (cross-consumer parity). |

Existing tests must continue to pass:

- `frontend/tests/unit/markdownView.test.ts` — sanitisation, iris://
  link rewriting, heading extraction.
- `frontend/tests/unit/markdownImageAllowlist.test.ts` — image-src
  allowlist defence-in-depth.

## Out of scope

Tracked verbatim in the [ADR-149 "Out of scope (deferred)"](../ADR-149-Mermaid-In-Markdown-Renderer.md) section. Headlines:

- `SetQA` consolidation — issue #71.
- Mermaid toolbar buttons / live-preview / export — future ADRs.
- Callouts and footnotes — still deferred from ADR-137.
