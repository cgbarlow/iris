# SPEC-243-A: Element Data panel

Implements **[ADR-243](../ADR-243-Element-Data-Panel.md)** (issue #292).

## 1. Row derivation (`frontend/src/lib/utils/elementData.ts`)

```ts
export interface ElementDataEntry {
	key: string;
	kind: 'text' | 'json';
	value: string;
	href?: string;
}
export function extraDataEntries(data: unknown): ElementDataEntry[]
```

| Input | Output |
|-------|--------|
| `data` is `undefined`, `null`, a primitive, or an array | `[]` |
| key `attributes` with an **array** value | skipped (rendered by the Attributes accordion) |
| key `attributes` with any other value | kept, like any other key |
| string that fully matches `/^https?:\/\/\S+$/i` | `{ kind: 'text', value, href: value }` |
| any other string / number / boolean / `null` | `{ kind: 'text', value: String(v) }` |
| object or array | `{ kind: 'json', value: JSON.stringify(v, null, 2) }` |

Rows keep `Object.entries` (authored/insertion) order.

## 2. Element page (`routes/elements/[id]/+page.svelte`)

- A new `Accordion.Item value="data"` is placed immediately **after** Extended,
  inside the same `Accordion.Root` (Details tab).
- Rendered only when `extraDataEntries(entity.data).length > 0`; trigger text is
  `Data ({count})`; collapsed by default like its siblings.
- Body: `<dl class="detail-grid grid gap-3" data-testid="element-data-panel">`, one
  `dt`/`dd` pair per row:
  - `dt` — the raw key, `font-mono break-all`, muted colour.
  - `dd` — `json` → `<pre class="whitespace-pre-wrap break-words …">`;
    `href` → `<a target="_blank" rel="noopener noreferrer" class="break-all underline">`;
    otherwise a `whitespace-pre-wrap break-words` span.
- Read-only in both view and edit mode. No change to the save path: it already does
  `const updatedData = { ...(entity.data ?? {}) }` and only replaces `attributes`,
  so these keys round-trip through an ordinary edit.
- No `{@html}` (Protocol §7).

## 3. Tests (TDD)

- **Unit** `frontend/tests/unit/elementData.test.ts` — empty/invalid input, issue
  #292 payload order and stringification, `attributes` array exclusion vs non-array
  retention, booleans/numbers/null, nested JSON formatting, link rules
  (http/https only; `javascript:`, relative paths, and URL-in-prose are not linked).
- **E2E** `frontend/tests/e2e/element-data-panel.spec.ts` —
  1. issue #292 payload renders `Data (8)` with a scalar row, an external link with
     `rel="noopener noreferrer"`, and a JSON `<pre>`;
  2. an `attributes`-only element shows `Attributes (1)` and no Data group;
  3. edit mode keeps the panel visible, and a Status edit + Save leaves `data`
     byte-identical via `GET /api/elements/{id}`.
- **Mobile** `frontend/tests/e2e/no-overflow.mobile.spec.ts` — an element with a long
  URL, a long key, and nested JSON opens the Data group without horizontal overflow
  (ADR-229).

Run: `npm run test:unit`, `npm run test:e2e`, `npm run test:mobile` (frontend).

## 4. Out of scope (follow-ups per ADR-243)

- Editing non-`attributes` `data` keys in place.
- Element-template-driven labels, ordering, and typed forms for `data`.
