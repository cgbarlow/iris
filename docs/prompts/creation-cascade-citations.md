# Creation-cascade citations base prompt — canonical body

Canonical paste-ready content for the **`creation-cascade-citations-v1`** row at `/admin/settings/ai` (filter `purpose=creation_format`, `layer=base`, `display_order=2`). This text composes into every notation's `creation_format` cascade after the shared conversation rules and before the destination chooser.

This prompt is **notation-agnostic**. Any notation that has a "sources" or "references" concept inherits these rules — DoView outcomes_map's Sources page, BPMN regulatory-references annotations, process_flow source-citation boxes, etc. Notations without source concepts (e.g. a UML class diagram) are unaffected because they never emit `source_reference` elements.

The seed function `seed_creation_prompts` re-applies this body on every backend startup so admin edits are overwritten with the canonical content.

## Content (paste this into the row's `prompt_text` field)

```text
## Citation discipline (shared)

Whenever the diagram you are creating includes any source-reference,
citation, or external-link element (regardless of notation), apply
these rules to every such element. Notations without source elements
are unaffected.

### URL format

Every URL embedded in a source reference, citation, or annotation
MUST be a raw, visible, copy-safe plain-text string beginning with
`https://`. Do NOT use markdown links (`[text](url)`). Do NOT use
reference-style links (`[text][1]`). Do NOT wrap URLs in angle
brackets, square brackets, or parentheses.

### Source reference label format

For every source-reference / citation element, the human-readable
label must follow this pattern:

  Author/Org · Title · YYYY · https://raw.url

Use a middle-dot separator (` · `, U+00B7) between fields. Examples:

  Duignan, P. · DoView Planning Handbook · 2025 · https://doviewplanning.org/book
  WHO · Banana export market overview · 2024 · https://example.org/who-bananas
  OECD · Agricultural Monocultures Report · 2023 · https://oecd.org/ag/mono

If any field is genuinely unknown (e.g. the user supplied content
without attribution), use `Unknown` for that field rather than
omitting the separator. Keep the URL — a label without a URL is not
a citation.

### Where citations go in the diagram

The location of source-reference elements is governed by the
notation- and diagram-type-specific prompts below. For example DoView
outcomes_map places source_references on a dedicated Sources page;
BPMN may inline them as annotation elements adjacent to the step they
inform. The citation FORMAT is universal; the placement is per
notation.

### Source provenance

If the user supplied content directly (via paste or attachment in
Stage 0 Q1), use the user as the author when no clearer attribution
is available:

  User-supplied content · <brief description> · YYYY · (no URL)

Drop the URL field for genuinely uncited user-supplied material —
do not invent one.

### When the user picks "general knowledge"

If the user picked "General knowledge" at Stage 0 Q1 and no specific
sources were mentioned, do NOT fabricate citations. If a Sources page
is required by the notation, populate it with the model's own
identifier and a `(no URL)` marker:

  AI general knowledge · <topic summary> · <current year> · (no URL)

This is preferable to fake URLs and lets the user replace it with
real sources later.
```

## Why this prompt is shared, not outcomes_map-specific

The first round of #133 feedback observed that the `outcomes_map` Sources page contained names without URLs. The fix is easy at the notation level — but the rule (raw URLs, fixed label format) generalises to every diagram type that has any source/citation/reference concept. Encoding it once at `layer=base` means future notations inherit the discipline automatically, and the (markdown, doview_analysis) response-format prompt's URL convention (m051 lines 59–67) is now mirrored at creation time.

## Revision history

- **v6.1.0 (this revision).** Introduced. Issue #133 Phase 1.

## See also

- [ADR-176](../adrs/ADR-176-Cascade-Shared-Base-Prompts.md)
- [SPEC-176-A](../adrs/specs/SPEC-176-A-Cascade-Shared-Base-Prompts.md)
- [creation-cascade-shared.md](./creation-cascade-shared.md) — sibling shared prompt for conversation conventions.
- [creation-cascade-destination.md](./creation-cascade-destination.md) — sibling shared prompt for save-destination.
- Migration `m051_response_format_prompts.py` — the response-format URL rule this prompt mirrors at creation time.
