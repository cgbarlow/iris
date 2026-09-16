# SPEC-245-A: Element Data panel editing

Implements **[ADR-245](../ADR-245-Element-Data-Panel-Editing.md)** (issue #292).
Builds on [SPEC-243-A](./SPEC-243-A-Element-Data-Panel.md).

## 1. Helpers (`frontend/src/lib/utils/elementData.ts`)

```ts
export type DataValueType = 'text' | 'number' | 'boolean' | 'json';
export interface DataEditRow { key: string; type: DataValueType; value: string }
export type ApplyDataEditResult =
	| { ok: true; data: Record<string, unknown> }
	| { ok: false; error: string };

export function toDataEditRows(data: unknown): DataEditRow[]
export function applyDataEditRows(
	rows: DataEditRow[],
	opts: { attributesArrayInUse: boolean },
): ApplyDataEditResult
```

Both helpers and `extraDataEntries` share `panelEntries(data)`: `Object.entries`
of a plain object, minus an `attributes` **array**.

### `toDataEditRows`

| Stored value | Row `type` | Row `value` |
|--------------|-----------|-------------|
| string | `text` | the string |
| number | `number` | `String(n)` |
| boolean | `boolean` | `'true'` / `'false'` |
| object, array, `null` | `json` | `JSON.stringify(v, null, 2)` |

### `applyDataEditRows` (rows in order; first error wins)

1. Key is trimmed. Blank key **and** blank value → row skipped. Blank key with a
   value → `Data row {n} needs a key` (1-based).
2. Repeated key → `Data key "{k}" is used more than once`.
3. Key `attributes` while `attributesArrayInUse` →
   `Data key "attributes" is reserved for the Attributes table`.
4. Parse by type:
   - `text` → value verbatim (empty string allowed).
   - `number` → `Number(trimmed)`; blank or non-finite → `Data "{k}" must be a number`.
   - `boolean` → trimmed `true`/`false`; else `Data "{k}" must be true or false`.
   - `json` → `JSON.parse(trimmed)`; throws → `Data "{k}" is not valid JSON`.

Invariant: `applyDataEditRows(toDataEditRows(d), { attributesArrayInUse: false })`
returns `d` minus any `attributes` array.

## 2. Element page (`routes/elements/[id]/+page.svelte`)

- State: `editDataRows: DataEditRow[]`, seeded in `enterDetailsEdit()` with
  `toDataEditRows(entity.data)`.
- `dataEditResult = $derived(applyDataEditRows(editDataRows, { attributesArrayInUse: editAttributes.length > 0 }))`.
- Dirty check: `JSON.stringify(editDataRows) !== JSON.stringify(toDataEditRows(entity.data))`
  is OR-ed into `detailsDirty`.
- Toolbar: Save is also disabled while `!dataEditResult.ok`; the error text renders
  beside it (`role="alert"`).
- Accordion shows when `dataEntries.length > 0 || editingDetails`; the count reads
  `editDataRows.length` in edit mode.
- Edit body (`data-testid="element-data-editor"`), per row `i` (1-based labels):
  - key input — `aria-label="Data field {i} key"`
  - type select (Text / Number / Yes / No / JSON) — `Data field {i} type`
  - value — `Data field {i} value`: textarea (json, 3–10 rows, monospace), select
    `true`/`false` (boolean), text input (text; number with `inputmode="decimal"`)
  - remove button — `aria-label="Remove data field {i}"`
  - rows are `flex-col` on mobile, `sm:flex-row` above
  - inline `role="alert"` error under the rows; `+ Add Data Field` appends
    `{ key: '', type: 'text', value: '' }`.
- Save: if `!dataEditResult.ok` return early; else
  `updatedData = { ...dataEditResult.data }`, then
  `updatedData.attributes = editAttributes.filter(a => a.name.trim())` when
  `editAttributes.length > 0`. Sent as `data` in the existing PUT.
- View mode is unchanged from SPEC-243-A.

## 3. Tests (TDD)

- **Unit** `frontend/tests/unit/elementData.test.ts` — `toDataEditRows` typing and
  `attributes` handling; `applyDataEditRows` round-trip, trimming/blank rows/order,
  empty text, missing key, duplicates, reserved `attributes`, invalid
  number/boolean/JSON.
- **E2E** `frontend/tests/e2e/element-data-panel.spec.ts` — edit text and number
  values, invalid JSON shows the inline error and disables Save, fix it, remove a
  row, add a boolean row, save; `GET /api/elements/{id}` matches exactly with the
  attributes array untouched; view mode shows the new key. The existing
  "survive an ordinary edit" case now asserts the editor is seeded.
- **Mobile** `no-overflow.mobile.spec.ts` — the Data-panel case also enters edit
  mode and asserts no horizontal overflow.

## 4. Out of scope

- Template-driven labels, ordering, and typed forms for `data`.
