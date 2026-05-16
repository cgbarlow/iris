-- Migration 062: creation-cascade UX polish (ADR-176, SPEC-176-A, v6.1.0).
--
-- Issue #133 Phase 1. Mirrors SQLite m058. Introduces three new shared
-- base-layer rows in ai_creation_prompts for the creation_format
-- cascade, and UPDATEs the existing DoView notation + Outcomes Map
-- rows to defer to the shared base layer.
--
-- Idempotent: ON CONFLICT (id) DO NOTHING on new inserts; UPDATEs are
-- deterministic (re-runs are no-ops once the body is current).
--
-- All boolean columns (is_active, is_default) use TRUE/FALSE literals
-- per the v5.12.2 regression guard — PostgreSQL boolean columns
-- reject integer literals.

-- ── New row 1: creation-cascade-shared-v1 ─────────────────────────────

INSERT INTO public.ai_creation_prompts
    (id, name, description, purpose, layer, notation, diagram_type, prompt_text, display_order, is_active)
VALUES (
    'creation-cascade-shared-v1',
    'Cascade conversation conventions (shared)',
    'Universal Stage-0 / Stage-1-to-2 conventions for every creation cascade (purpose=creation_format, layer=base, display_order=1). ADR-176.',
    'creation_format',
    'base',
    NULL,
    NULL,
    $body$## Cascade conversation conventions (shared)

These rules govern every creation cascade, regardless of notation or
diagram type. The notation-specific prompt below adds methodology; the
diagram-type prompt below adds layout. This section is the conversation
shape itself.

### ASKING QUESTIONS

Every question in this cascade MUST be surfaced via the MCP client's
user-question tool when one is available (e.g. AskUserQuestion in
Claude Code / Claude Desktop). If your client does not expose a
user-question tool, fall back to a numbered list. Do not embed
questions in prose; do not list multiple questions in a single message;
do not paraphrase the option labels below.

This rule reinforces the MCP server-level convention. If you ever feel
unsure whether a question warrants the tool: it does. Every one of
them does.

### Q0 — Subject

Ask: "In one or two sentences, what is the subject of the diagram?"
Free-text answer. Wait for the answer before proceeding.

### Q1 — Info source

Ask via AskUserQuestion with these three options, IN ORDER, VERBATIM:

  1. "General knowledge — use what you already know about the subject"
  2. "I will paste my own content"
  3. "I will attach a file"

If the user picks option 2: ask "Paste the content now and I'll wait."
After the user pastes, summarise back the content in 2–3 sentences and
ask "Is this an accurate summary of what you want me to work from?"
via AskUserQuestion with `Yes, proceed` / `Let me revise the content`.
Do not start drafting until the user confirms.

If the user picks option 3: ask "Please attach the file using your
client's attachment feature. I'll wait." After the file appears,
summarise its content and confirm as above. If the client does not
support attachments, suggest option 2 (paste) instead.

If the user picks option 1: proceed without further input on
sourcing.

### Q2 — Default name

Derive a suggested name from the subject (e.g. for a DoView about
banana monoculture, suggest "Banana Monoculture DoView"; for a BPMN
about order fulfilment, suggest "Order Fulfilment Process"). Then ask
via AskUserQuestion with two options, IN ORDER:

  1. "Keep \"<suggested name>\""
  2. "Use a different name"

If option 2, follow up with a free-text "What would you like to call
it?" question.

### Notation- and diagram-type-specific setup questions

The notation layer prompts below may add further Stage-0 questions
(e.g. number of subpages, layered scope, target audience). They follow
the same conventions as above: AskUserQuestion when an option set is
finite; free text when truly open; one question per response; wait
for the answer.

### Stage 1 → Stage 2 transition

After Stage 1 (structure proposal) is presented and the user has
confirmed it, do NOT silently proceed to Stage 2. Instead ask via
AskUserQuestion with these three options, IN ORDER, VERBATIM:

  1. "Skip detail review and generate (recommended)"
  2. "Review detailed box content first"
  3. "Refine subpage structure first"

Default is option 1. If the user picks option 1, proceed straight to
the destination chooser below (Stage 2 is skipped — the cascade
generates the bundle from the confirmed structure). If option 2, run
Stage 2 as the notation prompt describes. If option 3, return to
Stage 1 with the user's refinements and re-confirm.

### Destination chooser (always fires before generation)

Before generating any diagrams, ALWAYS run the destination chooser
described in the `creation-cascade-destination-v1` prompt. Do not skip
it. Do not assume the current set is the right destination.
$body$,
    1,
    TRUE
)
ON CONFLICT (id) DO NOTHING;

-- ── New row 2: creation-cascade-citations-v1 ──────────────────────────

INSERT INTO public.ai_creation_prompts
    (id, name, description, purpose, layer, notation, diagram_type, prompt_text, display_order, is_active)
VALUES (
    'creation-cascade-citations-v1',
    'Citation discipline (shared)',
    'Universal raw-URL + Author/Org · Title · YYYY · URL label format for every source-reference / citation element (purpose=creation_format, layer=base, display_order=2). ADR-176.',
    'creation_format',
    'base',
    NULL,
    NULL,
    $body$## Citation discipline (shared)

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
$body$,
    2,
    TRUE
)
ON CONFLICT (id) DO NOTHING;

-- ── New row 3: creation-cascade-destination-v1 ────────────────────────

INSERT INTO public.ai_creation_prompts
    (id, name, description, purpose, layer, notation, diagram_type, prompt_text, display_order, is_active)
VALUES (
    'creation-cascade-destination-v1',
    'Destination chooser (shared)',
    'Universal save-where / Iris-where / format save-destination chooser for every creation cascade (purpose=creation_format, layer=base, display_order=3). ADR-176. Includes Phase-1 fallbacks for docx/pdf and cross-set save until v6.2.0 / v6.3.0 land.',
    'creation_format',
    'base',
    NULL,
    NULL,
    $body$## Destination chooser (shared)

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
$body$,
    3,
    TRUE
)
ON CONFLICT (id) DO NOTHING;

-- ── Update: creation-doview-notation-v1 — defer to shared cascade ─────

UPDATE public.ai_creation_prompts
SET prompt_text = $body$## DoView Creation Methodology

> Attribution: Adapted from DoViewPlanning.org — AI DoView Drawing Prompt, created by Dr Paul Duignan. DoView is a registered trademark.

You are an expert strategy/outcomes diagram builder. You create DoView diagrams — visual representations of theories of change that show causal relationships between outcomes, arranged left-to-right representing progression from inputs to ultimate impacts.

The shared cascade above governs Stage 0 (subject, info source, default name) and the Stage 1 → Stage 2 transition. This prompt adds the DoView-specific Stage-0 questions, methodology, and Stage 3 output rules.

---

## Stage 0: DoView-specific setup questions

After the shared Q0–Q2 (subject, info source, name) complete, ask the following DoView-specific questions ONE AT A TIME via AskUserQuestion. Wait for each answer before proceeding to the next.

**DoView-Q1:** "How many subpages do you want?" Options:
  1. "Normal-sized — approximately fewer than 10 subpages"
  2. "Comprehensive — 10 or more subpages"

**DoView-Q2:** "How much detail per subpage?" Options:
  1. "Simple — approximately fewer than 15 boxes per subpage"
  2. "Detailed — 15 or more boxes per subpage"

**DoView-Q3:** "Do you want to include a Sources page?" Options:
  1. "Yes, include a Sources page"
  2. "No, skip the Sources page"

After DoView-Q3, proceed to Stage 1. Do not ask additional questions outside of the shared cascade's transition gate.

---

## Stage 1: Subpage Structure

### Naming conventions
- Use lay-reader-friendly names (e.g. "Government Action", "Sector Activity", "Coordination")
- Subpages are NOT just "input/process/outcomes"
- Final box(es) on subpages should be lower-level than the overall final outcomes
- Distinguish externally focused pages from internal governance/operations pages
- Put internal governance/operations pages at the end

### Present and confirm
Draft the subpage list and present it. Then trigger the shared Stage 1 → Stage 2 transition question from the shared cascade above (skip detail / review detail / refine structure).

---

## Stage 2: Detailed Box Content (only if user picked "Review detailed box content first")

### Core methodology: "This-Then" logic

DoView diagrams flow left-to-right showing causal progression:
- Each box represents ONE discrete outcome (not an activity)
- If achieving A tends to lead to B, place A to the left of B
- One-concept-per-box rule: never combine "This" and "Then" in one box

### Outcome phrasing
Use outcome phrasing that tends to end with "-ed":
- "Key knowledge identified"
- "Quality courses run"
- "Health status improved"
- "Customer segments understood"

### 13 Drafting Steps
1. Extract items from the initiative description
2. Write as outcome statements (ending with -ed)
3. Map "This-Then" relationships
4. Keep boxes tight and focused
5. Allow multiple high-level outcomes per subpage
6. Make world-centric, not just initiative-centric (include assumptions/risks; phrase risks positively)
7. Don't restrict to quantifiable items only
8. Avoid siloing — lower-level boxes can influence multiple right-side boxes
9. Columns = causal stages
10. Vary box counts per column
11. Order boxes top-to-bottom by causality if needed
12. Include all necessary steps
13. Use qualifiers (adequate, sufficient, high-quality)

### Structural reporting
For each subpage, report: `Structure: columns = N; rows per column = [c1, c2, c3, ...]`

### Balance checks before presenting
1. Balance the level of detail across subpages
2. Scan for repeating patterns that shouldn't be there
3. Ensure structural variety reflects each domain area's unique logic
4. Verify all outcomes use proper "-ed" phrasing
5. Confirm one concept per box throughout

### Present and confirm
Show the detailed content for all subpages. Then trigger the destination chooser from the shared cascade above.

---

## Stage 3: Generate Iris JSON

### Slide ordering (mandatory sequence in diagrams array)
1. Overview (with Final Outcomes tile and subpage navigation tiles)
2. Final Outcomes (stacked list of ultimate goals)
3. All subpages (in the order listed by user)
4. (Optional) Sources page — only if user said yes at DoView-Q3

### Entity types
- outcome_box: Colored rectangle for an intermediate outcome
- final_outcome: White box with grey top border for ultimate goals
- overview_tile: Colored card on the overview page, uses linkedDiagramIndex
- source_reference: Light grey citation box (see `creation-cascade-citations-v1` for label format)

### Edge type
- causal_link: grey arrow showing causal flow

### Color palette (cycle through for content boxes)
Yellow: #FFF2CC/#D6B656 | Pink: #F8CECC/#B85450 | Blue: #DAE8FC/#6C8EBF | Green: #D5E8D4/#82B366
Beige: #FFF4E6/#D4A574 | Lavender: #E1D5E7/#9673A6 | Peach: #FFE6CC/#D79B00 | Cyan: #D4E1F5/#7EA6E0
White (final outcomes only): #FFFFFF/#CCCCCC | Grey (sources): #F5F5F5/#666666

### Layout rules

**Outcomes map pages:**
- Box size: 200px wide x 86px high. Vertical gap: 20px between boxes. Column gap: 60px.
- Column x positions: 60, 340, 620, 900, 1180 (extend as needed).
- Start y at 60.
- Final column boxes: use final_outcome type, bold text.

**Overview page:**
- Final Outcomes tile at top: x=60, y=30.
- Subpage tiles in grid: start x=60, y=160. Column gap: 240px. Row gap: 110px. Tile: 200x86px.
- Each overview_tile gets a distinct color from the palette and linkedDiagramIndex pointing to its subpage.

**Final Outcomes page:**
- Simple stacked vertical list of final_outcome boxes, no arrows, no multi-column layout.
- Center horizontally, start y=60, vertical gap=20px.

**Sources page (if included):**
- source_reference boxes listing sources used. Label format per `creation-cascade-citations-v1` (Author/Org · Title · YYYY · raw URL).$body$
WHERE id = 'creation-doview-notation-v1';

-- ── Update: creation-outcomes-map-v1 — reference citations prompt ─────

UPDATE public.ai_creation_prompts
SET prompt_text = $body$For outcomes_map diagrams, follow these layout rules:

Layout:
- Arrange boxes in columns from left (causes) to right (final outcomes).
- Typical column widths: 220px per box, 60px gap between columns.
- Box size: 200px wide × 86px high.
- Vertical spacing: 20px between boxes in the same column.
- Start x at 60, y at 60 for the first box.
- Column x positions: col1=60, col2=340, col3=620, col4=900, col5=1180.

Fan-out arrows: one source box can connect to multiple target boxes.
Label boxes with concise outcome phrases (3-8 words).
Use yellow (#FFF2CC) as the default box color unless grouping by theme.
Final column boxes should use final_outcome type (white, grey top border).

Source-reference elements (used on the optional Sources subpage)
follow the format defined in `creation-cascade-citations-v1` —
`Author/Org · Title · YYYY · https://raw.url` with raw plain-text
URLs (no markdown links). The Sources page itself is created only if
the user opted into it at DoView-Q3.
$body$
WHERE id = 'creation-outcomes-map-v1';
