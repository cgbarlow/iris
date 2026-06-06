# ADR-239: Tap-to-tick checklist mode for Markdown & Smart Markdown views

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-239 |
| **Initiative** | Let a Markdown or Smart Markdown view be flipped into "checklist mode" where every list item becomes a tappable checkbox — tap to tick it off (strike-through), tap again to clear |
| **Proposed By** | Engineering |
| **Date** | 2026-06-06 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** Iris's two authorable Markdown surfaces — `text` diagrams
(source stored directly at `diagram.data.content`) and `smart_markdown` diagrams
(user edits `diagram.data.markdown_source`; the backend resolves `{{tokens}}`
into a server-locked `diagram.data.content` on read) — both rendered through the
shared `MarkdownView.svelte`, where lists today are inert HTML and there is no
way to tick items off,

**facing** issue #255's request to "turn lists into checklists — tap a list item
and it gets ticked off, strike through", which needs (a) an enable switch, (b)
interactive checkboxes, and (c) tick state that survives reloads, exports, and
Smart Markdown's compute-on-read resolution,

**we decided to** store tick state as **native GFM task markers** (`- [ ]` /
`- [x]`) inside the markdown **source**, gate the behaviour behind a per-diagram
boolean **`metadata.checklist`** flag (an existing JSON column — no schema
change), and render interactivity as an **opt-in, post-render DOM decoration
pass** in `MarkdownView` that replaces each `<li>` marker with an accessible
`<button role="checkbox">`. A tap maps the rendered checkbox back to its source
list item **by document-order index** and flips the marker via the pure helper
`toggleChecklistItem(source, index)`; the page then saves through the **existing**
`PUT /api/diagrams/{id}` path (OCC preserved). In checklist mode **every** list
item is a checkbox (not only pre-authored `- [ ]` items), and tapping a plain
item ticks it in one action,

**and neglected** (1) a dedicated `checklist_state` column or JSON map keyed by
item index — rejected because it adds schema churn + a Supabase mirror, breaks
markdown export portability, and the index key drifts the moment the list is
edited, whereas a source marker is self-describing and travels with the
document; (2) making only GFM `- [ ]` items interactive — rejected because the
issue asks to "turn lists into checklists", so requiring the user to first
author task syntax misses the intent; (3) relying on `marked`'s own
`<input type=checkbox>` output — rejected because the render pipeline's DOMPurify
pass strips `<input>`, and even un-stripped it ships `disabled` with form
semantics, whereas a `role="checkbox"` button is keyboard-accessible and fully
under our control; (4) a per-user / view-only toggle — rejected (per the issue
owner's choice) because shared, persisted state is the expected behaviour and it
reuses the save/version/OCC path for free,

**to achieve** a portable, export-clean checklist that needs no migration, no new
write endpoint, and no change to the MCP/CLI surface — while leaving the User
Guide (the other `MarkdownView` consumer) byte-for-byte unchanged because the
decoration is strictly opt-in (default off),

**accepting that** (a) the rendered-checkbox→source-line index mapping assumes
Smart Markdown token resolution preserves list-item order and count — true
today because resolution is an inline splice between `{{...}}` matches, and
locked by a regression test, but a token that expanded to a multi-item list
would break the mapping (documented limitation); (b) each tap is a full
save+reload round-trip rather than optimistic local state — acceptable for the
interaction frequency and it keeps OCC honest.

---

## Consequences

- **No schema change.** `metadata.checklist` rides the existing
  `diagram_versions.metadata` JSON column; tick markers are plain text inside the
  existing `data` JSON. No SQLite migration and no Supabase mirror (§15 N/A).
- **No new write surface.** The flag and the markers are persisted by the
  existing `PUT /api/diagrams/{id}`, which already has its MCP tool
  (`update_diagram`, `metadata` + `data` in `_DIAGRAM_UPDATE_FIELDS`) and CLI
  subcommand (`iris update diagram --metadata-json` / `--data-json`). Surface
  parity (§14) is satisfied with no change; `scripts/check_surface_parity.py`
  has nothing new to match.
- **Eligibility.** Only `text` and `smart_markdown` expose the toggle and accept
  taps — their source is user-editable. The synthesised list types
  (`dynamic_list`, `aggregation_list`) are excluded because their content is
  computed and a tap could not persist.
- **Security (§7).** Interactivity is added by a DOM pass over already-sanitised
  output; no new `{@html}` and no widening of the DOMPurify allowlist.

## Alternatives considered

See the **and neglected** clause above: dedicated state column/map, GFM-only
interactivity, reusing marked's `<input>`, and a view-only toggle — each
rejected with rationale.

## Dependencies

- ADR-137 (shared `MarkdownView` + pure `markdownHelpers`).
- ADR-205 (Smart Markdown source/resolved-content split; ADR-187 compute-on-read).

## References

- Implementation spec: [SPEC-239-A](./specs/SPEC-239-A-Markdown-Checklist-Mode.md)
- GitHub issue #255
