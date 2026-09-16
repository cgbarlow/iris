# ADR-245: Edit element `data` keys in place from the Data panel

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-245 |
| **Initiative** | Let users edit, add, remove, and retype the element `data` keys the Data panel shows |
| **Proposed By** | Engineering |
| **Date** | 2026-09-16 |
| **Status** | Approved |
| **Supersedes** | ADR-243's "read-only in edit mode" clause (the rest of ADR-243 stands) |

---

## ADR (WH(Y) Statement format)

**In the context of** the element page's **Data** accordion (ADR-243, v6.48.0), which
made every non-`attributes` key of an element's free-form `data` blob visible but
deliberately stayed read-only, deferring editing,

**facing** user feedback straight after release that clicking **Edit Details**
leaves the Data section uneditable — content written through MCP or element
templates can be read in Iris but still only changed via the API / MCP / CLI,

**we decided to** make the Data accordion editable inside the existing **Edit
Details** flow. Each key becomes a row of **key**, **type** (Text / Number /
Yes-No / JSON), and **value** (text input; `true`/`false` select; monospace
textarea for JSON), with per-row remove and **+ Add Data Field**. Two pure helpers
in `frontend/src/lib/utils/elementData.ts` own the conversion:
`toDataEditRows(data)` types each existing value (string → Text, number → Number,
boolean → Yes-No, object/array/`null` → JSON) so an untouched save round-trips
exactly, and `applyDataEditRows(rows, { attributesArrayInUse })` rebuilds the
keys, validating live — blank key with a value, duplicate keys, a Data
`attributes` key while the Attributes table owns that key, a non-numeric Number,
a non-boolean Yes-No, and unparseable JSON are errors. The first error shows
inline in the panel and beside Save, and Save is disabled until it's fixed. On
save, `data` = the validated rows plus the Attributes table's array; a removed
row deletes its key. The rows join the page's existing dirty check. Same
`PUT /api/elements/{id}` (with `If-Match` OCC) as every other field,

**and neglected** (1) a single raw-JSON editor for the whole blob — rejected: easy
to break, hostile for non-developers, and it would duplicate the Attributes table's
ownership of `attributes`; (2) inferring type from the typed text (e.g. `"2"` →
number) — rejected: silently changes stored types (a slug `"2025"` would become a
number); an explicit type select keeps intent visible; (3) template-driven labels
and typed forms — still deferred (ADR-243 follow-up), this generic editor is its
fallback; (4) surfacing validation through the page-level `error` state — rejected:
that state replaces the whole page with an alert and would discard the edit view,

**to achieve** a Data section that is both legible and editable, so a collection
populated by an agent can be maintained by the person who owns it,

**accepting that** keys are still raw strings with no schema, a value can be
retyped (e.g. Text → Number) only when its text parses, and nested structures are
edited as JSON text.

---

## Consequences

- **No schema, endpoint, MCP, or CLI change.** `data` was already writable via
  `PUT /api/elements/{id}`; surface parity (§14) and migration parity (§15) are N/A.
- **`{@html}` (§7):** not used; inputs are bound values.
- **DRY (§13):** read rows, edit rows, and parsing share one `panelEntries` filter
  in `elementData.ts`.
- **Behaviour change vs ADR-243:** the save path no longer spreads `entity.data`;
  it rebuilds from the rows (which are seeded from every non-`attributes` key), so
  unedited keys are preserved exactly and removed rows really delete.
- **Mobile (ADR-229):** rows stack below `sm`; covered by the existing Data-panel
  `no-overflow.mobile.spec.ts` case, extended into edit mode.

## Dependencies

- ADR-243 (Data panel — this ADR supersedes its read-only-in-edit-mode clause).
- ADR-228 (element metadata edit UI — the Edit Details flow and dirty check).
- ADR-229 (mobile no-horizontal-overflow invariant).

## References

- Issue #292
- Implementation spec: [SPEC-245-A](./specs/SPEC-245-A-Element-Data-Panel-Editing.md)
