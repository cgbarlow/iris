# ADR-149: Mermaid diagram rendering in the shared Markdown view

Status: Accepted (2026-05-10) — supersedes the "Markdown extensions" deferral in [ADR-137](ADR-137-Text-Diagram-Subclass-And-Shared-Markdown-Renderer.md) §"Out of scope (deferred)" for the mermaid clause only (callouts and footnotes remain deferred).

## Context

ADR-137 shipped a shared markdown rendering pipeline used by the User
Guide and Text diagram views, and explicitly deferred markdown
extensions: *"Markdown extensions (mermaid blocks, callouts,
footnotes) — start with stock markdown; extend if users ask."* The
user is now asking — Mermaid diagrams as code (` ```mermaid ` fenced
blocks) are commonly the most natural way to embed flowcharts,
sequence diagrams and ER diagrams inside an architectural document,
and Iris's existing Diagram canvases don't cover the lightweight
"sketch a flow inline with prose" use case that markdown-based docs
target.

The AI Q&A panel (`SetQA.svelte`) maintains a divergent local
`renderMarkdown` independent of the shared pipeline. Bringing AI
answers onto the shared renderer (so they also render mermaid,
`iris://` links and images) is recognised but **out of scope for
v5.7.0** — it is tracked in [issue
#71](https://github.com/cgbarlow/iris/issues/71). Scoping it out keeps
this release focused on the Markdown view surface and avoids bundling
an AI-answer behavioural change with the mermaid feature.

## Decision

Three concrete decisions:

### 1. Mermaid is integrated via a custom `marked` extension that emits a placeholder, plus a post-render Svelte effect that calls `mermaid.run()` on the live DOM

The pipeline at `frontend/src/lib/components/markdownHelpers.ts:82` is
intentionally synchronous (`marked.parse(source, { async: false })`)
and SSR-safe (early-returns when `document` is undefined). Pre-rendering
mermaid SVG inside the helper would force the pipeline async and pull
the ~500KB mermaid bundle into every render — defeats lazy loading and
breaks SSR.

Instead, the `marked` extension matches ` ```mermaid ` fenced blocks
and emits:

```html
<pre class="mermaid-block" data-mermaid-source="<base64-encoded-source>"><code>...escaped source...</code></pre>
```

This placeholder survives stage-1 DOMPurify with default config (no
allowlist widening at the markdown stage). After `{@html}` injects the
sanitised HTML, a Svelte `$effect` in `MarkdownView.svelte` calls
`runMermaidIn(rootEl, theme)` which lazy-imports `mermaid`, walks the
placeholders, decodes the source, calls `mermaid.render()` per block,
sanitises the resulting SVG (stage 2 — see decision 2), and replaces
the placeholder.

Per-block errors are caught and shown as a small
`<div class="mermaid-error">…</div>`; the rest of the document still
renders.

### 2. Two-stage DOMPurify sanitisation

Protocol #7 mandates DOMPurify on every `{@html}`. The pipeline now
has two stages:

1. **Stage 1 (existing)**: markdown → marked → DOMPurify (default tags
   + Iris's URL allowlist). The placeholder `<pre>` survives unchanged.
2. **Stage 2 (new)**: mermaid output SVG → `DOMPurify.sanitize(svg, {
   USE_PROFILES: { svg: true, svgFilters: true }, ADD_TAGS:
   ['foreignObject'] })` → the placeholder's `innerHTML` is replaced
   with the sanitised SVG.

`foreignObject` is **not** in DOMPurify's default SVG profile (it is
the typical XSS vector for SVG sanitisers) but mermaid uses it for
HTML labels in flowcharts. Because mermaid runs in
`securityLevel: 'strict'` (decision 3), the HTML inside any
`foreignObject` is mermaid-controlled and bounded — we accept the
narrow widening as the cost of HTML-label rendering.

### 3. Mermaid runs in `securityLevel: 'strict'`

`mermaid.initialize({ securityLevel: 'strict', ... })` disables HTML
in user-authored labels and disables click-bindings emitted into the
SVG. This aligns with protocol #7's "treat user content as hostile"
posture and constrains mermaid's own input parser. Stage-2 DOMPurify
remains as defence-in-depth.

If a future use case warrants HTML labels, a one-line ADR amendment
documents the trade-off and relaxes the level.

## Why a `marked` extension + post-render effect, not pre-rendering inside the helper

- The helper is sync and SSR-safe today. Going async cascades to every
  consumer (the User Guide route, `TextCanvas`, and every test that
  imports `renderMarkdown`).
- Mermaid intrinsically mutates a live DOM (it appends measurement
  nodes to `document.body`). The cleanest place for that is a Svelte
  `$effect` where mount/unmount lifecycle is already handled.
- The placeholder approach keeps the helper a pure function of its
  input. Tests that exercise `renderMarkdown` continue to need only
  jsdom — they never need the mermaid bundle to assert on rendered
  HTML shape.

## Why lazy-load mermaid via dynamic `import('mermaid')`

The mermaid bundle is ~500KB gzipped — the largest dependency in the
frontend. Loading it eagerly would inflate the initial JS chunk for
every user, including those who never view a markdown document
containing a mermaid block. Dynamic import keeps mermaid in a separate
Vite chunk that is only fetched when the renderer detects at least one
`.mermaid-block` placeholder. Zero-block documents pay zero bundle
cost.

## Why `securityLevel: 'strict'` not `'loose'`

`'strict'` disables HTML labels and click bindings in user-authored
mermaid source. Mermaid is itself a parser running on user input —
the strict level reduces the surface that the parser can inject. The
stage-2 DOMPurify pass is the second layer; running mermaid loose
would force DOMPurify to do the only line of defence on richer HTML,
inverting protocol #7's "be conservative at every stage" approach.

## Compatibility

- Existing markdown documents are unaffected — non-mermaid fenced code
  blocks render exactly as before.
- The TOC heading extractor already skips fenced blocks
  (`markdownHelpers.ts:59`); mermaid blocks are still fenced, so TOC
  behaviour is unchanged.
- The `iris://` link allowlist, image-src allowlist, and URL scheme
  allowlist are unchanged.
- The existing `<pre>` styles in `MarkdownView.svelte` lines 125-132
  apply to ordinary fenced code blocks; the new
  `:global(.mermaid-block)` rule overrides them with a transparent
  background and no padding so the placeholder reads cleanly during
  the brief moment before the SVG replaces it.
- SSR is preserved: the `marked.parse` step runs server-side and
  emits the placeholder; the `$effect` only runs client-side.

## Out of scope (deferred)

- **AI Q&A panel mermaid + DRY consolidation** — `SetQA.svelte`'s
  divergent local `renderMarkdown` is left untouched. Tracked in
  [issue #71](https://github.com/cgbarlow/iris/issues/71).
- **Mermaid editor toolbar buttons** (insert flowchart / sequence
  templates) — typing a fence is straightforward enough; defer toolbar
  ergonomics until usage warrants.
- **Live-preview mermaid while typing** in `TextCanvas` — the current
  browse-vs-edit toggle is sufficient; split-pane preview is its own
  workstream.
- **Mermaid in non-markdown views** (Sequence canvas, BPMN canvas) —
  those have their own native renderers; mermaid here is a markdown
  feature, not a general diagram backend.
- **Export-to-PNG/SVG of rendered mermaid** — browser print or
  right-click-save-image is the workaround.
- **Markdown callouts and footnotes** — still deferred from ADR-137.
- **Relaxing `securityLevel`** to allow HTML labels and click
  bindings — defer to a future ADR amendment if user requests it.

## See also

- [ADR-137](ADR-137-Text-Diagram-Subclass-And-Shared-Markdown-Renderer.md) —
  shared MarkdownView pipeline that this ADR extends.
- [SPEC-149-A](specs/SPEC-149-A-Mermaid-Rendering.md) — extension
  shape, placeholder contract, lazy-load flow, theme integration,
  error UX, file map, test coverage.
- [Issue #71](https://github.com/cgbarlow/iris/issues/71) — follow-up
  to consolidate `SetQA` onto the shared renderer.
