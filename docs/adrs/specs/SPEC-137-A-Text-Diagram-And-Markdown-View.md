# SPEC-137-A: Text diagram and shared MarkdownView

ADR: [ADR-137](../ADR-137-Text-Diagram-Subclass-And-Shared-Markdown-Renderer.md)

## Storage model

A Text document is a row in the existing `diagrams` table with:

| Column           | Value                              |
|---|---|
| `diagram_type`   | `'text'`                           |
| `notation`       | `'markdown'`                       |
| `data` (JSONB)   | `{ "content": "<markdown source>" }` |

No new tables, no new columns. Existing fields (`id`, `name`,
`description`, `parent_package_id`, `set_id`, `metadata`,
`created_at`, etc.) carry the same semantics as for any other
diagram. Tags, comments, search, packages, hierarchy all work
unchanged because Text *is* a Diagram.

## Registry seed

Seeded by `m044_text_diagram_class.py` (SQLite) and
`m045_text_diagram_class.sql` (Supabase):

- `notations` row: `('markdown', 'Markdown', 'Markdown text documents …', 6)`.
- `diagram_types` row: `('text', 'Text Document', 'Markdown-backed text document with TOC navigation', 15)`.
- `diagram_type_notations` mapping: `('text', 'markdown', is_default=true)`.
- `ai_creation_prompts` row `('markdown-notation', layer='notation', notation='markdown', …)` teaching the model the markdown content shape + iris:// link convention.

## Frontend file map

| Surface                   | File |
|---|---|
| Shared markdown helpers   | `frontend/src/lib/components/markdownHelpers.ts`           |
| Shared MarkdownView       | `frontend/src/lib/components/MarkdownView.svelte`          |
| TOC drawer                | `frontend/src/lib/components/MarkdownToc.svelte`           |
| Text canvas               | `frontend/src/lib/canvas/text/TextCanvas.svelte`           |
| Diagram routing branch    | `frontend/src/routes/diagrams/[id]/+page.svelte` (canvasType `'text'` branch) |
| Hierarchy menu submenu    | `frontend/src/routes/+page.svelte` (View → Diagram / Text) |
| Create dialog fallback    | `frontend/src/lib/components/DiagramDialog.svelte` (markdown → text) |
| Tree node muted styling   | `frontend/src/lib/components/TreeNode.svelte` (`tree-node__name--text`) |
| User Guide refactor       | `frontend/src/routes/guide/[section]/+page.svelte` |

## Rendering pipeline

```
markdown source
  → marked.parse({ async: false })
  → DOMPurify.sanitize({ ALLOWED_URI_REGEXP: /^(?:https?|mailto|iris):/i })
  → walk anchors → enforce URL-scheme allowlist + tag iris:// targets
  → {@html}
```

URL scheme allowlist: `{http, https, mailto, iris}`. Anything else
gets its `href` stripped (the anchor remains in the DOM but no longer
navigates).

## iris:// URL scheme

Two recognised forms:

```
iris://diagram/<id>
iris://element/<id>
```

The id token matches `[A-Za-z0-9_\-:.]+`. Any other path or scheme is
treated as an unknown link (passes through as plain marked output;
not tagged with the iris classes).

Rendered anchor:

```html
<a
  href="iris://diagram/abc123"
  class="md-iris-link md-iris-link--diagram"
  data-iris-kind="diagram"
  data-iris-id="abc123"
>label</a>
```

If the diagram id appears in the optional `textDiagramIds` set passed
to `MarkdownView`, the `md-iris-link--text` class is added so CSS
applies the muted colour (issue #26 grey-vs-black distinction).

Click handling: `MarkdownView` listens at the root `<div class="md-view">`,
delegates by `closest('a.md-iris-link')`, calls `goto('/diagrams/<id>')`
or `/elements/<id>` from `$app/navigation`.

## TOC heading extraction

Walks the source line-by-line:

- Skips fenced code blocks (lines between matching ` ``` ` fences).
- Matches ATX headings: `^(#{1,6})\s+(.+?)\s*#*\s*$`.
- Slugs heading text via `lower().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '')`.
- Disambiguates duplicate slugs by appending `-2`, `-3`, ...

Output: `{ id, level, text }[]`. The TOC drawer uses `level` to
indent (`(level - 1) * 12px`) and `id` to anchor-jump.

## TextCanvas modes

`TextCanvas.svelte` has two modes driven by an `editing` prop:

- **View mode** (`editing=false`): renders `<MarkdownView source={content} />`
  inside a `max-width: 920px` reading column.
- **Edit mode** (`editing=true`): renders a full-height `<textarea>`
  bound to `content`. `oninput` fires `oncontentchange(value)` so the
  parent (the diagram detail page) can persist the change via the
  existing diagram update endpoint with `data.content` patched.

The diagram detail page wires `diagram.data.content` into the canvas.
Save uses the existing diagrams PUT endpoint with the patched data
JSON — no new API.

## TOC drawer integration

The diagram detail page already has a 300px right-side drawer for
`CommentsPanel`. `MarkdownToc` mirrors the layout (background fill,
border, 6px radius, scrollable). A `showTocDrawer` boolean controls
visibility; toggle button can sit next to the existing Comments
button (out of scope for this spec — left to the page-level
integration).

## DRY: User Guide refactor

Before:

```svelte
<script>
  import { marked } from 'marked';
  import DOMPurify from 'dompurify';
  import { GUIDE_BY_SLUG, DEFAULT_SECTION } from '$lib/guide';
  ...
  const html = $derived(DOMPurify.sanitize(marked.parse(section.markdown)));
</script>
{@html html}
```

After:

```svelte
<script>
  import { GUIDE_BY_SLUG, DEFAULT_SECTION } from '$lib/guide';
  import MarkdownView from '$lib/components/MarkdownView.svelte';
</script>
<MarkdownView source={section.markdown} />
```

The `marked` and `DOMPurify` imports now live in exactly one place
(`markdownHelpers.ts`). Future security fixes apply once.

## Hierarchy menu

The dashboard "+ New" menu (`frontend/src/routes/+page.svelte`)
gains a "View" submenu header above two entries — "Diagram" (opens
the create dialog with no notation pre-set) and "Text" (opens the
dialog with `initialNotation='markdown'`, which then displays only
the Text Document type per the markdown→text fallback).

The third entry (Package) is unchanged.

## Visual distinction in TreeNode

`TreeNode.svelte`'s `.tree-node__name` element gains a
`tree-node__name--text` modifier class when `node.diagram_type === 'text'`.
The class applies `color: var(--color-muted)`. Same approach for any
breadcrumb / picker that lists diagram names (out of scope here —
TreeNode covers the dashboard hierarchy where it matters most).

## Tests

| File                                                          | Coverage |
|---|---|
| `backend/tests/test_diagrams/test_text_diagram.py` (5 tests)  | Registry seed, default notation, create + round-trip content, iris:// link content preserved verbatim |
| `frontend/tests/unit/markdownView.test.ts` (9 tests)          | Sanitisation (XSS, javascript:, file:, data:), iris:// link extraction + tagging, text-class muted class, heading extraction with depth + slug, fenced-code skipped |

## Out of scope (in line with ADR-137)

- A `text_links` table or `target_kind` column on `diagram_links`.
  Iris's link graph for Text content is the iris:// links inside the
  markdown — extracted at render time, no separate persistence.
- Bidirectional "what references this" graph — defer until needed.
- Markdown extensions beyond stock marked output.
- Collaborative editing OT/CRDT.

## Amendment 2026-05-05 — UAT follow-ups (issue #27)

This amendment records the implementation surfaces for the seven
follow-up items captured in the ADR-137 amendment (sections A–G).

### A. Mark-dirty in the markdown editor

`frontend/src/routes/views/[id]/+page.svelte` — `oncontentchange`
callback on the `<TextCanvas>` instance now sets `canvasDirty = true`
in addition to writing `diagram.data.content`. The toolbar Save
button (which gates on `!canvasDirty`) now enables the moment the
user types.

### B. Persist content (not nodes/edges) for Text views

`saveCanvas()` builds the request body's `data` field via:

```ts
const data = canvasType === 'text'
  ? { content: markdownContent }
  : { nodes: canvasNodes, edges: canvasEdges };
```

`canvasType === 'text'` already exists for the canvas-vs-text
rendering branch — we reuse it for the save branch.

### C. Cursor-position markdown insertion

`frontend/src/lib/canvas/text/TextCanvas.svelte` adds a new
`textareaEl` prop declared with `$bindable()`. The internal
`<textarea>` binds its DOM element via `bind:this={textareaEl}`. The
parent page binds it back as `bind:textareaEl={textTextareaEl}`.

The parent then provides a single helper:

```ts
function insertMarkdownAtCursor(snippet: string) {
  // splice at selectionStart..selectionEnd, fall back to append
  // restore cursor + focus via queueMicrotask
}
```

The three add/link button handlers (`handleAddElement`,
`handleLinkElement`, `handleInsertDiagram`) each gain a one-shot
`canvasType === 'text'` branch that calls `insertMarkdownAtCursor`
with the appropriate `[name](iris://kind/<id>)` snippet.

### D. NotationPills now includes Markdown

Covered by SPEC-136-A amendment (NotationPills lists all seven
notations).

### E. Frontend rename — `/diagrams` → `/views`

| Surface                              | Change |
|---|---|
| `src/routes/diagrams/+page.svelte`   | git-renamed to `src/routes/views/+page.svelte` |
| `src/routes/diagrams/[id]/+page.svelte` | git-renamed to `src/routes/views/[id]/+page.svelte` |
| `src/routes/diagrams/+page.ts`       | New stub: `redirect(308, '/views' + url.search + url.hash)` |
| `src/routes/diagrams/[id]/+page.ts`  | New stub: `redirect(308, '/views/' + params.id + url.search + url.hash)` |
| `src/routes/+page.svelte` (Dashboard) | Cards/labels: "Diagrams" → "Views"; "Diagram Hierarchy" → "View Hierarchy"; nav target `/views`; search placeholder updated |
| `src/lib/components/AppShell.svelte` | Menu item `/views`, label "Views" |
| `src/lib/components/MarkdownView.svelte` | Internal `goto` for `iris://diagram/<id>` clicks now goes to `/views/<id>` |
| `src/lib/components/TreeNode.svelte` | `nodeHref` builds `/views/<id>` for non-package nodes |
| `src/lib/canvas/nodes/ModelRefNode.svelte` | "View diagram" link target `/views/<id>` |
| `src/lib/canvas/controls/EntityDetailPanel.svelte` | Linked-diagram button targets `/views/<id>`; "Open Linked Diagram" → "Open Linked View" |
| Page detail `recordVisit({ href })`  | Stored history entries point at `/views/<id>` |
| `src/routes/elements/[id]/+page.svelte` | "Used in" links go to `/views/<id>` |
| `src/routes/bookmarks/+page.svelte`  | Bookmarked-diagram links go to `/views/<id>` |
| `src/routes/import/+page.svelte`     | "View Diagrams" CTA → "Browse Views"; href `/views` |
| `src/routes/packages/[id]/+page.svelte` | After child create, `goto('/views/<id>')` |
| `src/lib/components/SetQA.svelte`    | After AI applies a primary diagram, `goto('/views/<id>')` |
| `src/lib/components/DiagramDialog.svelte` | Field label "Diagram Type" → "View Type"; markdown notation type entry "Text Document" → "Text" |

The dialog filename, the underlying types (`Diagram`,
`DiagramHierarchyNode`), the API URLs (`/api/diagrams/...`), the
`diagram` column in `recordVisit.type`, and all backend code keep the
`diagram` term — the rename is strictly user-facing.

### F. `HierarchyControls` (shared component)

New `frontend/src/lib/components/HierarchyControls.svelte` renders
two dropdowns: **+ New** (View | Package) and **Show** (Diagrams
checkbox + Text checkbox + an explanatory note that packages are
always shown).

Adopted by:

- Dashboard hierarchy panel — replaces the inline "+ New" submenu and
  removes the temporary `View → Diagram | Text` flattening that
  v5.1.0 shipped (the notation pill in the Create dialog now drives
  the choice).
- Views index toolbar — replaces the standalone "New Diagram" + "New
  Package" buttons.

`TreeNode` gains `showDiagrams: boolean` and `showText: boolean`
props (default `true`), with a derived `passesKindFilter` that hides
leaf nodes whose kind is toggled off. Packages always pass.

The Dashboard's existing Reorder button is preserved with a clearer
tooltip ("Reorder — drag tree items to change their position").

### G. EntityDialog scopes the notation pill

`frontend/src/lib/canvas/controls/EntityDialog.svelte` passes
`notations={['simple','uml','archimate','c4','bpmn','doview']}` to
`<NotationPills>` — `markdown` is intentionally absent because text
views do not have entities.

### Tests added

| File                                                          | Coverage |
|---|---|
| `frontend/tests/unit/notationPillsCoverage.test.ts`           | Every notation key in `DiagramDialog.NOTATION_TYPE_FALLBACK` appears in `NotationPills.ALL_NOTATIONS` (catches issue #27 root cause). |
| `frontend/tests/unit/textCanvasSavePersistence.test.ts`       | Detail page `saveCanvas` branches on `canvasType === 'text'` and persists `data: { content: markdownContent }`; `oncontentchange` callback flips `canvasDirty = true`. |
| `frontend/tests/unit/textCanvasInsertLink.test.ts`            | `TextCanvas` exposes `$bindable()` `textareaEl`; parent page defines `insertMarkdownAtCursor` and the three handlers branch on text mode to call it with `iris://element/` and `iris://diagram/` snippets. |
| `frontend/tests/unit/docrefSelectorPolling.test.ts`           | Optimistic `importing` flip + 3 s polling while any document is `importing` + cleanup on teardown. |
| `frontend/tests/unit/viewsRedirect.test.ts`                   | `/diagrams/+page.ts` and `/diagrams/[id]/+page.ts` redirect (308) to the `/views` equivalents preserving query + hash. |
| `frontend/tests/unit/hierarchyControls.test.ts`               | Component renders the two dropdowns and emits `oncreateview` / `oncreatepackage` / `onShowDiagrams` / `onShowText`. |

## Amendment 2026-05-05 — markdown experience overhaul (issue #32 reopen, v5.3.0)

Implementation surface map for the four ADR-137 v5.3.0 amendments.

### A. Rendering parity (single source of truth in MarkdownView)

Typography selectors lifted from `guide/+layout.svelte` (`.guide-content :global(…)`) to `MarkdownView.svelte` (`.md-view :global(…)`):

- `h1` (1.875rem bold) / `h2` (1.25rem 600) / `h3` (1.05rem 600) / `h4`–`h6` (600)
- `p` / `ul` (`list-style: disc`) / `ol` (`list-style: decimal`) / `li` / `strong` / `em`
- `code` / `pre` / `pre code` (transparent reset) / `blockquote` / `hr` (1px border-top)
- `img` (max-width: 100%, border, border-radius)

`guide/+layout.svelte` reduces to layout-only (sticky nav, grid, narrow-screen breakpoint).

### B. TOC drawer toggle

`views/[id]/+page.svelte` toolbar — gated on `canvasType === 'text'`:

```svelte
{#if canvasType === 'text'}
  <button
    onclick={() => (showTocDrawer = !showTocDrawer)}
    aria-pressed={showTocDrawer}
    aria-label="Toggle table of contents"
    title="Table of contents"
  >TOC</button>
{/if}
```

Mounted in both the in-place toolbar and the focus-mode toolbar (matches the existing `Comments` button placement). The drawer mounts at lines 2834 (edit) and 2903 (browse) were already in place from v5.1.0 — this amendment adds the trigger.

### C. Image / link allowlist (defence in depth)

| Layer | Check | `/guide/foo.png` | `data:` |
|---|---|---|---|
| 1. DOMPurify `ALLOWED_URI_REGEXP` | `/^(?:(?:https?|mailto|iris):|\/|\.{1,2}\/)/i` | passes | rejected → DOMPurify strips |
| 2. `urlIsAllowed` post-walk on anchors | `new URL(href, placeholder).protocol ∈ ALLOWED_SCHEMES` | passes (resolves to `https:`) | rejected (`data:`) |
| 3. **NEW**: `urlIsAllowed` post-walk on `<img src>` | same | passes | rejected (DOMPurify allows `data:` on img by default — this layer covers that gap) |

### D. Markdown editor toolbar

| File | Lines | Purpose |
|---|---|---|
| `frontend/src/lib/canvas/text/markdownEditorToolbarHelpers.ts` | ~95 | Pure helpers (`wrapSelection`, `prefixLines`, `insertAtCursor`, `applyOp`) returning `EditorOp` records. Trivially unit-testable; no Svelte. |
| `frontend/src/lib/canvas/text/MarkdownEditorToolbar.svelte` | ~110 | 12-button bar that calls helpers + applies the result via `applyOp` + fires `onchange`. |
| `frontend/src/lib/canvas/text/TextCanvas.svelte` | (modified) | Mounts the toolbar above the textarea in edit mode. Adds Ctrl/Cmd+B / +I / +K shortcuts inside the existing `handleKeydown` (alongside the v5.1.2 Tab trap). |

Toolbar buttons (left → right):

| Button | Action | Shortcut |
|---|---|---|
| **B** | wrap `**…**` | Ctrl/Cmd+B |
| **I** | wrap `*…*` | Ctrl/Cmd+I |
| **H1** | line prefix `# ` (toggle) | — |
| **H2** | line prefix `## ` (toggle) | — |
| **H3** | line prefix `### ` (toggle) | — |
| **• UL** | line prefix `- ` (toggle, every selected line) | — |
| **1. OL** | line prefix `1. ` (toggle, every selected line) | — |
| **❝ Quote** | line prefix `> ` (toggle) | — |
| **`</>` Code** | wrap `` `…` `` | — |
| **🔗 Link** | wrap `[…](url)` | Ctrl/Cmd+K |
| **🖼 Image** | insert `![alt](path)` | — |
| **─ HR** | insert `\n---\n` | — |

Cursor / selection behaviour:
- Empty selection + wrap → caret placed between markers so the user types content directly.
- Non-empty selection + wrap → markers wrap the selection; cursor restored adjusted for marker length.
- Line-prefix actions toggle: if all touched lines already start with the prefix, it's stripped (matches GitHub / VSCode markdown shortcut conventions).

### Tests added in v5.3.0

| File | Coverage |
|---|---|
| `frontend/tests/unit/markdownImageAllowlist.test.ts` | Absolute and relative paths preserved; `javascript:`/`data:`/`file:` stripped on both `<a>` and `<img>`. |
| `frontend/tests/unit/markdownViewParity.test.ts` | Heading + list + img rules live in MarkdownView and are absent from the guide layout. |
| `frontend/tests/unit/textViewTocToggle.test.ts` | TOC button rendered for Text views; flips `showTocDrawer`. |
| `frontend/tests/unit/markdownEditorToolbar.test.ts` | Pure-helper unit tests: wrap, line-prefix (single/multi-line, toggle off), insert-at-cursor. |
