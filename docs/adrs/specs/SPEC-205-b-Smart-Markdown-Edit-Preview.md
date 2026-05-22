# SPEC-205-b: Smart-markdown edit-view companion panel

Implements: extension of [ADR-205](../ADR-205-Smart-Markdown-View-Type.md). Supersedes the deferred inline-fillable-slot section ([SPEC-210-a §5.1](./SPEC-210-a-Smart-Markdown-Value-Overrides.md)). Addresses observations C5 + C6 from the [2026-05-22 issue #211 comment exchange](https://github.com/cgbarlow/iris/issues/211).

## 1. Problem

`SmartMarkdownCanvas.svelte` edit mode is a raw markdown textarea. Two reported friction points:

- **C5**: tokens like `{{element:a8db…:attr:attributes/Quantity/type=500}}` are opaque blobs. The author can't tell at a glance what each line will render to.
- **C6**: fillable slots (the trailing-`=` form) require manual cursor work inside long token blobs to type in a value. The original SPEC-210-a §5.1 specified inline editable spans; v6.18.0 shipped the backend grammar but deferred the editor UX.

## 2. Decision

Add a **right-hand companion panel** to `SmartMarkdownCanvas.svelte` in edit mode. Two stacked sections:

### 2.1 Top: Fill in the blanks

For every `{{...:attr:<path>=}}` empty-override token in `markdown_source`, render a labeled row:

- **Element name** (resolved via `/api/elements/{id}` GET; cached per session).
- **Attribute path label** (humanised — `attributes/Quantity/type` → `Quantity`).
- **Editable text input** for the value.
- **Resolved-line preview** (`↳ "500 g Pork mince"`) updated as you type.

On input blur, the panel rewrites the source token from `=` to `=<value>` at the exact byte-position the regex matched. The source textarea updates atomically.

### 2.2 Bottom: Tokens preview

The last-saved resolved markdown (`data.content`) rendered in a muted grey style via the existing `MarkdownView` component. A `↻ Saved` / `* unsaved` indicator distinguishes saved vs. drafting state.

## 3. Why this design

- **No client-side resolver port.** Fillable-slot editing only needs string rewriting on the source; the element-name + path are in the token itself + one cheap GET. We don't try to live-resolve every other token type — that would require either a JS port of the smart_markdown resolver (DRY violation §13) or a backend round-trip per keystroke.
- **No textarea replacement.** Source stays a plain textarea — power users / paste workflows unaffected. The panel is additive.
- **Honours SPEC-210-a §5.1's intent** (make `=` slots fillable) without committing to a full contenteditable rebuild.

## 4. Component

New `frontend/src/lib/canvas/text/SmartMarkdownCompanionPanel.svelte`:

```svelte
<script lang="ts">
  interface Props {
    source: string;                   // bind:source from parent canvas
    content: string;                  // resolved data.content (last save)
    canvasDirty: boolean;             // unsaved-flag from parent
    onsourcechange: (next: string) => void;
  }
  // ... regex out fillable tokens, fetch element data lazily, render rows
</script>
```

Mounted inside `SmartMarkdownCanvas.svelte` when `editing=true`. Layout: source textarea ~60%, panel ~40% on wide screens; tabbed on narrow.

## 5. Algorithm

### 5.1 Detecting fillable tokens

```ts
const FILLABLE_RE = /\{\{element:([^:}]+):attr:([^=}]+)=\}\}/g;
// Captures: (1) element_id, (2) attribute path (e.g. `attributes/Quantity/type`)
// Match's .index gives the byte position in the source.
```

For each match, store `{ start, end, elementId, attrPath, value: '' }`. The same element_id may appear multiple times (e.g. one for Quantity, one for Unit override) — each is its own row.

### 5.2 Element-name + attribute lookup

Lazy `GET /api/elements/{element_id}` once per unique id, cache result. Pull `name` and `data.attributes[*].name` for the path-segment translation.

Path translation: `attributes/Quantity/type` → display the user-readable last-meaningful-segment, which is the attribute name `Quantity`. We strip the leading `attributes/` and the trailing `/type` / `/notes` etc.

### 5.3 Source rewrite on blur

```ts
function applyValue(token: FillableToken, value: string) {
  const safe = value.replace(/[\\}]/g, '');  // drop }, \ to avoid mangling
  if (!safe) return;  // empty stays empty
  const newToken = source.substring(token.start, token.end)
                       .replace(/=\}\}$/, `=${safe}}}`);
  const next = source.substring(0, token.start)
             + newToken
             + source.substring(token.end);
  onsourcechange(next);
}
```

Byte-position rewrite, not string-replace: two identical tokens get disambiguated by index.

### 5.4 Resolved-line preview

Per row, build the rendered text by:
- Replacing tokens of the form `{{element:<id>:name}}` in the **same source line** with the element's name.
- Replacing `{{element:<id>:attr:<path>=<value>}}` with `<value>`.
- Replacing the SAME token currently being edited with the **typed value** (live).
- Leaving other tokens / text as-is.

This is line-local "fake resolution" — enough to give the user a visible cue without re-implementing the full resolver.

## 6. Tokens preview (read-only)

The lower half of the panel renders `<MarkdownView source={content} />` inside a `.preview-muted` wrapper:

```css
.preview-muted { opacity: 0.75; }
.preview-muted :global(*) { color: var(--color-muted); }
```

A small indicator above:

```svelte
<small>{canvasDirty ? '* unsaved — preview shows last save' : '↻ saved'}</small>
```

## 7. Tests

`frontend/tests/unit/smartMarkdownCompanion.test.ts`:

- `FILLABLE_RE` extracts the right tokens.
- `applyValue` rewrites the source at the right byte position; doesn't touch other tokens.
- Two identical fillable tokens are disambiguated by index.
- Empty value is a no-op (doesn't strip the `=`).
- `}` and `\` in the input value are stripped (defensive).

Visual verification post-deploy (manual):
- Open Spaghetti recipe → edit → see the panel right of the textarea with one fillable row for Pork mince's Quantity slot.
- Type "750" → source updates → row preview shows "750 g Pork mince".
- Save → tokens-preview pane refreshes; indicator flips to `↻ Saved`.

## 8. Genericness (ADR-214)

Pure UI logic. No domain terminology. Clean.

## 9. Out of scope (future)

- Live (debounced) full resolved preview of the whole source as you type — needs either backend roundtrip or a JS resolver port.
- Per-token hover tooltips on the textarea itself.
- Editing non-fillable tokens (e.g. swapping which element a `:name` token points at).
- Multi-line fillable values.

## 10. Risk

- One GET per unique element-id on first render. Mitigated by caching; a typical recipe has 5-15 distinct elements. UAT response time is ~50-100ms per element.
- Byte-position rewrite is sensitive to the source changing between regex match and apply. We re-run the regex on every keystroke (the panel re-derives rows from source via $derived), so stale indices don't survive.
