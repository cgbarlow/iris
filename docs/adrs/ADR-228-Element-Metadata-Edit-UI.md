# ADR-228: Element metadata edit UI (status, extended scalars, tagged values)

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-228 |
| **Initiative** | Close the frontend gap on element metadata editing exposed by the *C&A (alternative name)* incident |
| **Proposed By** | Engineering |
| **Date** | 2026-05-31 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** Iris users editing imported Sparx EA elements via
the `/elements/<id>` page — the GEANZ capability-area elements all
carry a `metadata.status` (Proposed / Approved / …), eleven extended-
section scalars (stereotype, version, scope, abstract, persistence,
author, complexity, phase, EA created+modified dates, gen_type), and a
`metadata.tagged_values` array of `{property, value}` rows that often
encode review notes, maturity levels, and EA tagged-value defaults,

**facing** that the page renders every one of those fields as
**display-only** (`frontend/src/routes/elements/[id]/+page.svelte`
lines 866-953) even though the backend has accepted `metadata` on
`PUT /api/elements/<id>` since v6.36.1 (ADR-184 followup —
`ElementUpdate.metadata` in `backend/app/elements/models.py:36-51`,
persisted by `service.update_element`). MCP / CLI agents can already
write `metadata`; humans can't. The page's `saveEntityMetadata()`
never includes `metadata` in the PUT body and `enterDetailsEdit()`
never seeds edit state for it. The same function also includes
`element_type` in the PUT body even though `ElementUpdate` rejects it
— dead bytes,

**we decided to** mirror the existing `editAttributes` pattern
(`+page.svelte:66, 290-293, 327-332, 781-809`) for the three metadata
buckets:

  - **Status** — free-text `<input list="status-suggestions">` plus a
    `<datalist>` of common Sparx values (Approved, Proposed,
    Implemented, Validated, Mandatory). Doesn't lock the model — the
    backend column accepts any string, and a strict dropdown would
    reject imports from other tools.
  - **Extended-section scalars** — every existing display block gets
    a sibling `<input>` in edit mode. Same Tailwind / `var(--color-…)`
    class set as the Attributes editor.
  - **Tagged values** — the table becomes an editable grid: per-row
    `property`, `value`, `notes` inputs + ✕ delete; footer `+ Add
    Tagged Value` button. The wire format keeps a single string
    `value` per row; the editor splits on the Sparx `#NOTES#` marker
    so the prescriptive description (`"Values: -,0,1,2,3,4,5\nDefault:
    -\nDescription: …"`) can live in its own textarea without
    fat-fingering the meaningful value. A row whose property is blank
    is filtered out on save (matches the Attributes pattern).

  Tagged-value split/join + the "unset" check (matches `_extract_
  tagged_value` in `backend/app/diagrams/smart_markdown.py:139`) are
  factored into `frontend/src/lib/utils/taggedValues.ts` so future
  callers reuse them (DRY §13). The `element_type` key is dropped
  from the PUT body builder while we're in the same function.

**to achieve** human parity with the existing MCP / CLI metadata edit
surface, close the gap the user hit on *C&A (alternative name)*, and
remove the false `element_type` send. Backend untouched.

**accepting** that:
- A tagged-value whose *meaningful* value contains the literal
  substring `#NOTES#` would be split incorrectly. The Sparx
  convention reserves the marker for the description separator;
  treating it as a delimiter is consistent with EA tooling and
  matches what `_extract_tagged_value` already does on the read
  path.
- Long edits that race a concurrent writer (>5 min, edit-then-save)
  hit the existing `If-Match` 409. Surfaced by the existing
  top-of-page `error` div. No new UX work in this ADR.
- Status accepts any string — no enum constraint. The `<datalist>`
  is suggestion-only.
- The Extended scalars are simple `<input>`s (not date pickers for
  the EA dates). Sparx writes dates as `"2023-04-14 09:08:57"` —
  not strict ISO 8601 — so a date picker would mangle the round
  trip. Power users only edit these by hand; the schema is
  preserved.

## Rejected alternatives

- **Strict status dropdown** — would reject values from non-Sparx
  importers. The backend doesn't constrain the column; the UI
  shouldn't either.
- **Single textarea per tagged-value row holding the raw value
  including `#NOTES#…`** — power-user-only, foot-gunny: easy to
  delete the description by accident. The split editor protects the
  description without losing access to it.
- **Raw-JSON metadata editor** — flexible but defers the UX problem
  rather than solving it. The 80% of edits hit status + tagged
  values + a handful of scalars; targeted controls beat a
  textarea-of-JSON for that path. Raw editor is a clean follow-up if
  needed.

## Dependencies

- Backend write surface (`ElementUpdate.metadata`) shipped in v6.36.1.
- Read-side parity: `_extract_tagged_value` in
  `backend/app/diagrams/smart_markdown.py:139` is the canonical "is
  this value unset" check; the new `taggedValues.ts:isUnsetTaggedValue`
  mirrors it.
- Pattern source of truth: the existing Attributes editor on the
  same page. Same DRY §13 idiom applies.

## Consequences

- Spec: SPEC-228-A.
- No backend change, no DB migration, no MCP / CLI surface change
  (Protocol §14 unaffected).
- Closes the user-reported gap on `metadata.status` and Extended.
- Removes the `element_type` false send from the PUT body — minor
  hygiene.
- Establishes `frontend/src/lib/utils/taggedValues.ts` as the
  authoritative place for `#NOTES#` parsing on the frontend. Reused
  by any future caller (export views, search snippets, etc.).
