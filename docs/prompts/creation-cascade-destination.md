# Creation-cascade destination chooser base prompt — canonical body

Canonical paste-ready content for the **`creation-cascade-destination-v1`** row at `/admin/settings/ai` (filter `purpose=creation_format`, `layer=base`, `display_order=3`). This text composes into every notation's `creation_format` cascade after the shared conversation rules and the citations rules.

This prompt is **notation-agnostic** and **scope-agnostic** — it codifies the save-destination chooser that fires before any diagram is created, regardless of which Set the user is browsing when the cascade starts.

The seed function `seed_creation_prompts` re-applies this body on every backend startup so admin edits are overwritten with the canonical content.

## Phase 1 caveat

Phase 1 of issue #133 ships **prompt-only**. The cascade asks the user where they want the bundle saved and in which formats — but the renderer (md/docx/pdf → artefact store) and the move tools (for fixing wrong-location bundles) land in Phase 2 (v6.2.0) and Phase 3 (v6.3.0) respectively. Until then, if the user picks "Iris (different location)" or "downloadable artefacts other than markdown", the cascade explains the gap and offers a fallback.

## Content (paste this into the row's `prompt_text` field)

```text
## Destination chooser (shared)

Before generating ANY diagrams, run this chooser. Do not skip it. Do
not assume the current set is the right destination. This applies to
every notation and every diagram type.

### Q-Dest1 — Save where?

Ask via AskUserQuestion with these three options, IN ORDER, VERBATIM:

  1. "Iris (source of truth) — save into a set so the bundle is queryable, linkable, and shareable"
  2. "Chat with downloadable artefacts — render the bundle as files (md / docx / pdf) and return links"
  3. "Both — save into Iris AND return downloadable artefacts"

### Q-Dest2 — Iris destination (only if Q-Dest1 includes Iris)

If the user picked option 1 or option 3, ask via AskUserQuestion with
these four options, IN ORDER, VERBATIM:

  1. "New set under the parent collection of the set being viewed (default)"
  2. "Browse — show me the root collections so I can pick"
  3. "Current set — save into the set we're currently in"
  4. "Somewhere else — I'll type a collection or set id"

If the user picked option 1: identify the parent collection of the
current set via `get_set` then `get_collection` (or directly from the
set's collection_id field), then proceed.

If the user picked option 2: call `list_collections` and surface the
results to the user as a follow-up AskUserQuestion. Once they pick a
collection, drill down with `list_sets` + AskUserQuestion if needed.

If the user picked option 3: use the current set as the destination.

If the user picked option 4: ask a free-text follow-up "Paste the
collection id or set id you want to save into." Validate that the id
resolves (via `get_collection` or `get_set`) before proceeding.

### Q-Dest3 — Format(s) (only if Q-Dest1 includes downloadable artefacts)

If the user picked option 2 or option 3 at Q-Dest1, ask via
AskUserQuestion with multi-select enabled:

  1. "Markdown (.md)"
  2. "Word document (.docx)"
  3. "PDF (.pdf)"

At least one option must be selected.

### Phase-1 fallback (cascade-prompt only, no renderer yet)

This prompt-side cascade is shipping in v6.1.0 ahead of the renderer
and move tools that actuate it. Until v6.2.0 and v6.3.0 land:

- If the user picks "Chat with downloadable artefacts" and selects
  docx or pdf at Q-Dest3, respond: "Docx and PDF generation ships in
  v6.2.0 (Phase 2 of issue #133). For now I can produce a markdown
  artefact in the chat and create the Iris bundle if you'd like."
  Then offer AskUserQuestion with options "Yes, markdown + Iris save",
  "Just the Iris save", "Cancel and wait for v6.2.0".

- If the user picks "Somewhere else" or "Browse" at Q-Dest2 and the
  chosen destination differs from the current set, respond: "I can
  draft the bundle and save it into the current set now, then move it
  to your chosen destination after v6.3.0 ships move_* tools. Or I
  can describe what I'd save without actually saving, and you can
  re-run after v6.3.0." Then offer AskUserQuestion with these two
  fallbacks.

These fallbacks are temporary. When Phase 2 and Phase 3 ship, the
seed will be updated to drop them and the cascade will actuate the
chosen destination directly.

### Confirm and generate

Once the chooser has resolved (destination identified, formats
selected if applicable), summarise the user's choices back in one
sentence — "OK, I'll generate the bundle as Markdown and PDF and save
it into the 'Banana Studies' collection as a new set" — and ask via
AskUserQuestion with `Proceed` / `Let me change something`. Generate
only after the user confirms.
```

## Why this prompt is shared and generic

The first round of #133 feedback observed that the cascade saved the bundle into the wrong set (the Outcomes Theory Book) because no destination question was ever asked. The fix is the chooser above. But every option in the chooser is generic — "new set under the parent collection of the set being viewed" works regardless of whether the current set is Outcomes Theory, a BPMN process library, or a UML model catalogue.

Encoding the chooser once at `layer=base` means every notation's cascade gets it for free.

## Revision history

- **v6.1.0 (this revision).** Introduced. Issue #133 Phase 1. Includes Phase 1 fallbacks for docx/pdf rendering and cross-set saves; the fallbacks are dropped when Phase 2 (v6.2.0) and Phase 3 (v6.3.0) ship.

## See also

- [ADR-176](../adrs/ADR-176-Cascade-Shared-Base-Prompts.md)
- [SPEC-176-A](../adrs/specs/SPEC-176-A-Cascade-Shared-Base-Prompts.md)
- [creation-cascade-shared.md](./creation-cascade-shared.md)
- [creation-cascade-citations.md](./creation-cascade-citations.md)
