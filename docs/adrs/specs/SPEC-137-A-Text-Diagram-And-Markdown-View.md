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
