# ADR-243: Read-only Data panel for arbitrary element `data` keys

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-243 |
| **Initiative** | Make every key in an element's `data` blob visible on the element page, not just `data.attributes` (issue #292) |
| **Proposed By** | Engineering |
| **Date** | 2026-09-16 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** the element detail page (`routes/elements/[id]/+page.svelte`),
which surfaces an element's payload in exactly two places — the **Attributes**
accordion (only a UML `data.attributes[]` array) and the **Extended** accordion
(only the eleven named `metadata` scalars plus tagged values from ADR-228) — while
the `data` blob itself is free-form: MCP `create_element` / `create_elements`
accept arbitrary keys, element templates pre-fill arbitrary `template_data`, and
the collection export carries `data` verbatim (whereas it strips `metadata`),

**facing** issue #292: an agent-populated collection can be complete and export
cleanly while every non-`attributes` key is stored, exported, and **invisible** in
the UI — the owner sees "No extended metadata available." on elements that carry a
full content payload, and `metadata` is no workaround because the export drops it,

**we decided to** add a read-only, collapsed **Data (N)** accordion directly after
Extended that lists every `data` key the page does not already render — i.e.
everything except an `attributes` **array** — in authored order. Row
derivation lives in one pure helper, `extraDataEntries()` in
`frontend/src/lib/utils/elementData.ts`: scalars (string / number / boolean /
null) render as text, nested objects and arrays render as pretty-printed JSON in a
`<pre>`, and a string whose **whole value** is an `http(s)://` URL renders as an
external link (`target="_blank" rel="noopener noreferrer"`). A non-array
`attributes` value is kept in the panel, since the Attributes accordion cannot
show it. The accordion is omitted when there are no rows, stays visible (and
read-only) in edit mode, and everything is rendered through Svelte's escaping
`{expressions}` — no `{@html}`,

**and neglected** (1) moving the content to `metadata` — rejected because the
collection export strips `metadata`, so build-time consumers would lose it;
(2) making the values editable in place — deferred: the existing save path already
spreads `entity.data` and only replaces `attributes`, so unrecognised keys survive
an ordinary edit today, and a generic editor needs its own decision on typing and
preserving that property; (3) template-driven labels/ordering (letting an element
template describe how its `data` renders) — deferred as a follow-up that builds on
this panel; (4) folding the rows into the Extended accordion — rejected because
Extended is `metadata`-backed and editable, and mixing a read-only `data` view into
it would blur which store a value lives in; (5) linkifying any string containing a
URL or any scheme — rejected: whole-value `http(s)` only, so `javascript:` and
prose never become links,

**to achieve** UI legibility for every value an element carries, so a collection
written through MCP or templates can be reviewed by the person who owns it,

**accepting that** keys are shown raw (no humanised labels or per-type forms), nested
structures appear as JSON rather than a bespoke tree, and editing `data` other than
`attributes` still requires the API / MCP / CLI.

---

## Consequences

- **No schema, endpoint, MCP, or CLI change.** Read-only frontend rendering of a
  field every surface already returns. Surface parity (§14) and SQLite↔Supabase
  parity (§15) are N/A.
- **`{@html}` (§7):** not used; values are escaped text, links are limited to
  whole-value `http(s)` URLs.
- **DRY (§13):** row derivation is a single pure helper shared by the page and its
  unit tests; the accordion reuses the page's existing `Accordion.Item` /
  `detail-grid` idiom.
- **Imported models are unaffected:** the Sparx / ArchiMate / PPTX importers write
  only `data.attributes` (or `{}`) to elements, so no Data group appears on them.
- **Mobile (ADR-229):** keys break-all and JSON wraps; covered by a
  `no-overflow.mobile.spec.ts` case.

## Alternatives considered

See the **and neglected** clause.

## Dependencies

- ADR-208 (element tabs — the accordions live under the Details tab).
- ADR-228 (element metadata edit UI — the Extended accordion this sits beside, and
  the `data`-spreading save path that preserves these keys).
- ADR-229 (mobile no-horizontal-overflow invariant).

## References

- Issue #292
- Implementation spec: [SPEC-243-A](./specs/SPEC-243-A-Element-Data-Panel.md)
