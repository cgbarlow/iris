# SPEC-228-A: Element metadata edit UI

Implements **[ADR-228](../ADR-228-Element-Metadata-Edit-UI.md)**.

## Helper module

`frontend/src/lib/utils/taggedValues.ts` (new):

```ts
/** Split a Sparx tagged-value `value` string on the `#NOTES#` marker.
 *  Returns the meaningful value and the prescriptive notes separately
 *  so the UI can edit each in its own control. */
export function splitTaggedValue(
  raw: string | null | undefined,
): { value: string; notes: string } {
  if (raw == null || raw === '' || raw === '-') {
    return { value: '', notes: '' };
  }
  const idx = raw.indexOf('#NOTES#');
  if (idx < 0) return { value: raw, notes: '' };
  return {
    value: raw.slice(0, idx),
    notes: raw.slice(idx + '#NOTES#'.length),
  };
}

/** Reassemble a tagged-value string from the editor's split form.
 *  Empty notes → omit the `#NOTES#` marker entirely. */
export function joinTaggedValue(value: string, notes: string): string {
  if (!notes) return value;
  return `${value}#NOTES#${notes}`;
}

/** Match `_extract_tagged_value` in
 *  backend/app/diagrams/smart_markdown.py:139 — treat `null`, `""`,
 *  `"-"`, and `"-#NOTES#…"` all as unset. */
export function isUnsetTaggedValue(
  raw: string | null | undefined,
): boolean {
  if (raw == null || raw === '' || raw === '-') return true;
  const { value } = splitTaggedValue(raw);
  return value === '' || value === '-';
}
```

Pure functions — no I/O, no DOM. Co-located vitest at `taggedValues.test.ts`.

## Page wiring

Mirror the `editAttributes` pattern in
`frontend/src/routes/elements/[id]/+page.svelte`.

### State (declare alongside `editAttributes` near line 66)

```ts
let editStatus = $state('');
let editStereotype = $state('');
let editMetaVersion = $state('');
let editScope = $state('');
let editAbstract = $state('');
let editPersistence = $state('');
let editAuthor = $state('');
let editComplexity = $state('');
let editPhase = $state('');
let editCreatedDate = $state('');
let editModifiedDate = $state('');
let editGenType = $state('');
let editTaggedValues = $state<
  { property: string; value: string; notes: string }[]
>([]);
```

### Seed (`enterDetailsEdit`, ~line 284)

```ts
const m = (entity.metadata ?? {}) as Record<string, unknown>;
editStatus = (m.status as string | undefined) ?? '';
editStereotype = (m.stereotype as string | undefined) ?? '';
editMetaVersion = (m.version as string | undefined) ?? '';
editScope = (m.scope as string | undefined) ?? '';
editAbstract = (m.abstract as string | undefined) ?? '';
editPersistence = (m.persistence as string | undefined) ?? '';
editAuthor = (m.author as string | undefined) ?? '';
editComplexity = (m.complexity as string | undefined) ?? '';
editPhase = (m.phase as string | undefined) ?? '';
editCreatedDate = (m.created_date as string | undefined) ?? '';
editModifiedDate = (m.modified_date as string | undefined) ?? '';
editGenType = (m.gen_type as string | undefined) ?? '';
const tvs = Array.isArray(m.tagged_values) ? m.tagged_values : [];
editTaggedValues = (tvs as Array<{ property?: string; value?: string | null }>)
  .map(tv => ({
    property: tv.property ?? '',
    ...splitTaggedValue(tv.value),
  }));
```

### Save (`saveEntityMetadata`, ~line 315)

```ts
const m = (entity.metadata ?? {}) as Record<string, unknown>;
const updatedMeta: Record<string, unknown> = { ...m };
const setOrDelete = (k: string, v: string) => {
  if (v.trim()) updatedMeta[k] = v;
  else delete updatedMeta[k];
};
setOrDelete('status', editStatus);
setOrDelete('stereotype', editStereotype);
setOrDelete('version', editMetaVersion);
setOrDelete('scope', editScope);
setOrDelete('abstract', editAbstract);
setOrDelete('persistence', editPersistence);
setOrDelete('author', editAuthor);
setOrDelete('complexity', editComplexity);
setOrDelete('phase', editPhase);
setOrDelete('created_date', editCreatedDate);
setOrDelete('modified_date', editModifiedDate);
setOrDelete('gen_type', editGenType);

const rebuiltTV = editTaggedValues
  .filter(r => r.property.trim())
  .map(r => ({
    property: r.property,
    value: joinTaggedValue(r.value, r.notes) || null,
  }));
if (rebuiltTV.length) updatedMeta.tagged_values = rebuiltTV;
else delete updatedMeta.tagged_values;

putBody.metadata = updatedMeta;
// v6.39.0: drop element_type — ElementUpdate doesn't accept it.
// (was line 335 before this PR)
```

### Render (Details + Extended display blocks, ~lines 866-953)

Each existing `{#if meta?.field}<dd>{value}</dd>{/if}` block becomes:

```svelte
<dt>Status</dt>
<dd>
  {#if editingDetails}
    <input
      type="text"
      list="status-suggestions"
      bind:value={editStatus}
      aria-label="Status"
      class="w-full rounded border px-2 py-1 text-sm"
      style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
    />
  {:else if (entity.metadata as Record<string, unknown> | null | undefined)?.status}
    {(entity.metadata as Record<string, unknown>).status}
  {/if}
</dd>
```

One `<datalist id="status-suggestions">` declared near the top of the
template:

```svelte
<datalist id="status-suggestions">
  <option value="Approved" />
  <option value="Proposed" />
  <option value="Implemented" />
  <option value="Validated" />
  <option value="Mandatory" />
</datalist>
```

Tagged-values table (replacing the read-only block ~932-953) — three
columns + delete + add-row, same Tailwind classes as the Attributes
table at lines 781-809.

## Acceptance criteria

1. In view mode, every metadata field renders exactly as today (no
   regression in the display layout).
2. In edit mode, every field listed in *Scope* has a writable
   control bound to a `$state` initialised from `entity.metadata`.
3. The Status input has `aria-label="Status"` (so the Playwright
   locator `getByLabel('Status')` finds it).
4. Tagged-values table: `+ Add Tagged Value` button appends a fresh
   `{ property: '', value: '', notes: '' }`; per-row `✕` removes
   the row.
5. On save, the PUT body's `metadata` field is the merged object:
   pre-existing `metadata` keys are preserved; edited keys are
   overwritten; blanked scalars are deleted from `metadata`;
   `tagged_values` reflects the edited rows (blank-property rows
   dropped, `joinTaggedValue` reapplied per row).
6. On save, the PUT body MUST NOT contain `element_type` (regression
   guard: when the page loads, no `element_type` key on the next
   request payload).
7. Concurrency: 409 surfaces via the existing `error` div — no
   silent state loss.

## Tests

### Unit — `frontend/src/lib/utils/taggedValues.test.ts`

```
test('splitTaggedValue: plain value', …)        → { value: '3', notes: '' }
test('splitTaggedValue: value + #NOTES# block') → { value, notes }
test('splitTaggedValue: null / "" / "-"')       → { value: '', notes: '' }
test('joinTaggedValue: empty notes')            → returns just value
test('joinTaggedValue: multi-line notes')       → 'v#NOTES#l1\nl2'
test('round-trip: join(split(x)) === x')        → for non-unset x
test('isUnsetTaggedValue: all four unset forms') → true; '3' / '3#NOTES#…' → false
```

### E2E — `frontend/tests/e2e/element-metadata-edit.spec.ts`

```
test('edit metadata round-trip', async ({ page }) => {
  // fixture: API-create a Set + Element with status = 'Proposed' and one tagged value
  await page.goto(`/elements/${id}?edit=true`);
  await page.getByLabel('Status').fill('Validated');
  await page.getByRole('button', { name: '+ Add Tagged Value' }).click();
  // fill the new row's three inputs by their aria-labels
  // (Property / Value / Notes scoped to the last row)
  await page.getByRole('button', { name: /^Save$/ }).click();
  await page.waitForResponse(r =>
    r.url().includes(`/api/elements/${id}`) && r.request().method() === 'PUT'
  );
  await page.reload();
  // status now displays 'Validated'; tagged-values table contains Reviewer / Alice
});
```

Plus a follow-up assertion: re-enter edit, click ✕ on the new tagged
value, save, reload, assert the row is gone.

### Regression

`cd frontend && npm run test` (vitest) + `npx playwright test
element-metadata-edit element-package-membership` — green before merge.

## Code anchors

- `frontend/src/routes/elements/[id]/+page.svelte`
  - State near line 66 (next to `editAttributes`).
  - Init in `enterDetailsEdit` ~284-313.
  - Save in `saveEntityMetadata` ~315-378, including `element_type` drop.
  - Display blocks ~866-953.
- `frontend/src/lib/utils/taggedValues.ts` (new).
- `frontend/src/lib/utils/taggedValues.test.ts` (new).
- `frontend/tests/e2e/element-metadata-edit.spec.ts` (new).
