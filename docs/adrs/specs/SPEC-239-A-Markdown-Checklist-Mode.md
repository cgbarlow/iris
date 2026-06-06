# SPEC-239-A: Markdown Checklist Mode

Implements **[ADR-239](../ADR-239-Markdown-Checklist-Mode.md)** (issue #255).

## 1. State model

| Concern | Where it lives | Notes |
|---------|----------------|-------|
| Mode on/off | `diagram.metadata.checklist` (boolean) | Existing JSON column; persisted + shared. No schema change. |
| Tick state | GFM task markers in the markdown **source** | `- [ ]` unchecked, `- [x]` checked. Portable, exports cleanly, survives Smart Markdown resolution. |

- **Eligible diagram types:** `text` and `smart_markdown` only. `text` markers
  live in `data.content`; `smart_markdown` markers live in `data.markdown_source`
  (the editable source — *not* the server-locked resolved `data.content`).
- `dynamic_list` / `aggregation_list` are excluded (computed content can't
  persist a tap).

## 2. Pure helpers (`frontend/src/lib/components/markdownHelpers.ts`)

```ts
export function countChecklistItems(source: string): number
export function checklistItemStates(source: string): boolean[]
export function toggleChecklistItem(source: string, index: number): string
export function decorateChecklist(root: ParentNode, states?: boolean[]): void
```

**Line scanner** (shared `eachListItem`, mirrors `extractHeadings` fence
handling):
- Split on `/\r?\n/`; toggle `inFence` on lines matching `/^(```|~~~)/`; skip
  fenced lines so a `- [ ]`-looking line inside a code block is **not** a list
  item.
- List-item line = `/^(\s*)([-*+]|\d+[.)])\s+(.*)$/` → captures indent, bullet,
  remainder. Task marker on the remainder = `/^\[([ xX])\]\s?/`.

**`toggleChecklistItem(source, index)`** — count list items in document order; at
`index` rewrite the remainder:
- existing marker → flip (`[ ]`↔`[x]`; `[X]` recognised), preserving the rest of
  the text verbatim (including any user-authored `~~strike~~`);
- plain item → a tap means "tick it": prepend `[x] `.
- Reconstruct as `indent + bullet + ' ' + remainder`. Out-of-range index
  (negative or past the end) → source returned unchanged.

**`checklistItemStates(source)`** — checked flag per item in document order;
drives the render pass (the pipeline's DOMPurify strips marked's `<input>`, so
checked-state is read from the source markers, which survive resolution).

**`decorateChecklist(root, states)`** — for each rendered `<li>` in document
order: remove any leftover `<input type=checkbox>`; prepend
`<button class="md-check" role="checkbox" aria-checked data-checklist-index=i>`;
add `md-check-checked` to checked items.

### Edge cases (asserted in `tests/unit/markdownChecklist.test.ts`)
nested lists (document order); ordered `1.`/`1)` and unordered `-`/`*`/`+`;
multi-line items (only the bullet line rewritten); fenced code skipped;
pre-existing `~~strike~~` preserved; uppercase `[X]`; out-of-range no-op;
indent/bullet preserved exactly.

## 3. Component contract (`MarkdownView.svelte`)

- New props: `checklist?: boolean` (default `false`) and
  `ontoggle?: (index: number) => void`.
- `$effect` keyed on `html`: when `checklist`, run
  `decorateChecklist(rootEl, checklistItemStates(source))` (re-runs whenever
  `{@html}` replaces content). **Default off ⇒ the User Guide is unaffected.**
- Root `onClick`: a click on `.md-check` reads `data-checklist-index`,
  `preventDefault()`, and calls `ontoggle(index)`; mutually exclusive with the
  iris-link branch.
- CSS (`:global`): `.md-check` square button (checkmark when
  `aria-checked="true"`); `li:has(.md-check)` drops its bullet;
  `li.md-check-checked` → `line-through` + muted colour.

`TextCanvas.svelte` and `SmartMarkdownCanvas.svelte` add the same two props and
pass them straight through to `MarkdownView` in their view branches.

## 4. Page wiring (`routes/views/[id]/+page.svelte`)

- `checklistEligible = diagram_type ∈ {text, smart_markdown}`;
  `checklistMode = checklistEligible && Boolean(diagram.metadata.checklist)`.
- Toolbar (browse mode, eligible types): a **Checklist** toggle button →
  `toggleChecklistMode()` flips `metadata.checklist` and `saveCanvas()`.
- `handleChecklistToggle(index)`: rewrite the editable source
  (`markdown_source` for smart_markdown, else `content`) via
  `toggleChecklistItem`, set `canvasDirty`, `await saveCanvas()` (existing OCC
  `If-Match` + reload; smart_markdown re-resolves with the new marker passing
  through). Passed as `ontoggle` to both canvases.
- `saveCanvas()` already sends `metadata`; the `checklist` key rides along
  through the existing `activeTheme` branch.

## 5. Surface & migration parity

- **§14 (surface parity): N/A.** Only writes are `metadata.checklist` and task
  markers inside existing `data` — both via the existing `PUT /api/diagrams/{id}`
  (existing MCP `update_diagram` + CLI `iris update diagram`). No new endpoint.
- **§15 (SQLite↔Supabase): N/A.** No DDL. `metadata` is an existing JSON column;
  markers are plain text in existing JSON `data`. No migration pair.

## 6. Test matrix

| Layer | File | Asserts |
|-------|------|---------|
| Unit | `frontend/tests/unit/markdownChecklist.test.ts` | helper algorithm + all §2 edge cases; `decorateChecklist` DOM output |
| E2E | `frontend/tests/e2e/checklist-tap.spec.ts` | tap ticks + strikes + persists across reload (PUT/OCC); untap; toggle enables mode; **User Guide has no `.md-check`** |
| Backend | `backend/tests/test_diagrams/test_smart_markdown.py` | task markers + list order/count survive token resolution (the index-mapping invariant) |
