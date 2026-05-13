# DoView and Outcomes Theory in Iris

*A complete map of how Dr Paul Duignan's outcomes theory and DoView methodology have been implemented in Iris, intended as a single-page reference for Dr Duignan and anyone else who wants to understand the implementation.*

> **Attribution.** Outcomes theory and DoView Planning are the work of Dr Paul W Duignan. Iris implements these methodologies as a software system; the underlying intellectual framework is Dr Duignan's. The handbook *DoView Planning and Outcomes Theory Handbook: 100+ Innovative, Integrated Tools for Solving Key Issues in Planning, Implementation, Contracting, Measurement, Evaluation and Reporting (for Humans and AI Agents)* (Duignan, 2025, [DoViewPlanning.org](https://doviewplanning.org/book)) is the authoritative source. Where Iris's behaviour or vocabulary diverges from the handbook, the handbook wins; this document is descriptive, not normative.

---

## 1. What Iris does for DoView, in one paragraph

Iris is an architectural-modelling and AI-collaboration platform that treats DoView as a **first-class notation** alongside UML, ArchiMate, C4, BPMN, and Markdown. A user can **author DoView outcomes maps directly in Iris** (visually or with AI-assisted creation), **store the DoView Book handbook content** (questions, tools, mermaid diagrams) as Iris diagrams the AI can search and cite, **generate formal handbook-grounded outcomes-theory analyses** (Prompt-C-shaped: Summary + Full + Diagrams) either in Iris's own AI flows or via MCP from external clients like Claude Desktop, and **save those analyses back** as a new Iris artefact type. The same admin-editable prompt machinery governs both diagram generation and response shaping; the cascade resolves at runtime so editing a single layered prompt updates behaviour across creation and response paths.

---

## 2. Where things live (quick map)

| Concept | Iris implementation | Code path |
|---|---|---|
| DoView as a notation | One of 7 registered notations | `backend/app/migrations/m027_doview_notation.py` |
| Outcomes-map diagram type | `notation=doview, diagram_type=outcomes_map` | `m027` registration; SPEC-094-A |
| Overview-page diagram type | `notation=doview, diagram_type=overview` | `m027` registration; SPEC-094-A |
| **Written analysis** artefact type | `notation=markdown, diagram_type=doview_analysis` | `backend/app/migrations/m051_response_format_prompts.py` |
| DoView creation methodology (the AI prompt) | Layered prompt seeded into the database | `backend/app/seed/creation_prompts.py:DOVIEW_NOTATION_PROMPT` |
| DoView-specific layout & color rules | Diagram-type-layer prompt for `outcomes_map` / `overview` | `backend/app/seed/creation_prompts.py` (rows `creation-doview-outcomes_map-v1`, `creation-doview-overview-v1`) |
| Composer that assembles the layered prompt | `build_creation_system_prompt(notation, diagram_type)` | `backend/app/ai/creation.py` |
| Response-format composer (formal analyses) | `build_response_system_prompt(notation, diagram_type)` | same file (added v5.12.0, ADR-157) |
| Materialisation of AI-generated JSON into Iris diagrams | `create_diagrams_from_ai(...)` | `backend/app/ai/creation.py` |
| DoView visual theme | Default theme registered alongside the notation | `m027` `themes` insert |
| Handbook content (the DoView Book set) | One Iris Set, ~230 diagrams, top-level packages A–J | UAT set_id `33032180-d77a-4ce4-88cf-b49cd643e093` |
| Admin GUI for editing all of the above | `/admin/settings/ai` (AI Prompts section) | `frontend/src/routes/admin/settings/ai/+page.svelte` (rewritten v5.13.0) |
| MCP tool surface for external AI clients | `iris-mcp` server | `mcp/src/iris_mcp/tools.py` |
| Per-scope authoring guidance | `mcp_system_context` field on Set / Collection | `backend/app/sets/models.py`, `m050` |
| Saved canonical mcp_system_context for the DoView Book | Reference doc | `docs/prompts/doview-book-mcp-system-context.md` |

---

## 3. DoView as a notation

DoView is one of seven notations in Iris's registry (Simple, UML, ArchiMate, C4, DoView, Markdown, BPMN). All seven share the same diagram engine, theming layer, persistence model, and AI scaffolding. DoView's distinguishing characteristics:

### 3.1 Element types

These are the boxes the user can draw or the AI can generate. Defined in `m027`.

| Type | Purpose | Default fill / border |
|---|---|---|
| `outcome_box` | A single achieved outcome in causal flow (an "-ed" outcome statement) | Pastel yellow `#FFF2CC` / `#D6B656` |
| `final_outcome` | Ultimate impact — visually distinct (white with grey top rule) so it reads as a destination | White `#FFFFFF` / `#CCCCCC` |
| `overview_tile` | A navigation card on the Overview page that points to a subpage | Cycling 10-color palette |
| `source_reference` | A citation / source URL on the Sources page | Light grey `#F5F5F5` / `#666666` |

### 3.2 Relationship type

| Type | Visual |
|---|---|
| `causal_link` | Grey edge `#C8C8C8`, 2px, step routing, no markers — represents "this then that" causal flow |

### 3.3 Diagram types

| Diagram type | Purpose |
|---|---|
| `outcomes_map` | A subpage of the DoView model (the workhorse — most diagrams in a DoView model are this type) |
| `overview` | The cover page of a DoView model (Final Outcomes tile + subpage navigation tiles) |
| **`doview_analysis`** *(under `notation=markdown`)* | A formal handbook-grounded written analysis of an outcomes question — text + embedded mermaid diagrams from referenced handbook tool pages. Added v5.12.0 (ADR-157); not a visual diagram but a sibling artefact type |

### 3.4 Visual conventions (cycling color palette)

For content boxes the renderer cycles through:

```
Yellow  #FFF2CC / #D6B656     Pink     #F8CECC / #B85450
Blue    #DAE8FC / #6C8EBF     Green    #D5E8D4 / #82B366
Beige   #FFF4E6 / #D4A574     Lavender #E1D5E7 / #9673A6
Peach   #FFE6CC / #D79B00     Cyan     #D4E1F5 / #7EA6E0
White (final outcomes only) #FFFFFF / #CCCCCC
Grey  (sources only)        #F5F5F5 / #666666
```

### 3.5 Layout rules

DoView diagrams flow **left-to-right** showing causal progression — `A` to the left of `B` if achieving `A` tends to lead to `B`. Specifics:

- Box size: 200 px wide × 86 px high.
- Vertical gap: 20 px between boxes; column gap: 60 px.
- Column x positions: `60, 340, 620, 900, 1180` (extend as needed).
- Final-column boxes use `final_outcome` type, bold text.
- Overview page: Final Outcomes tile at top (x=60, y=30); subpage tiles in a grid (start x=60, y=160, column gap 240px, row gap 110px, tile 200×86 px). Each `overview_tile` carries `linkedDiagramIndex` to the subpage it points to.
- Sources page: simple stacked vertical list of `source_reference` boxes, centered, no arrows.
- Final Outcomes page: stacked vertical list of `final_outcome` boxes, centered, start y=60, vertical gap 20 px.

These rules are encoded both in the AI creation prompt body (so the AI generates conformant diagrams) and in the SvelteKit renderer (so user-drawn diagrams snap to the same conventions).

---

## 4. The DoView creation methodology in code

Iris encodes Dr Duignan's question-driven creation methodology directly. Each stage maps to a stage in the AI conversation; the user is led through the same flow as the handbook prescribes.

### 4.1 Stage 0 — Setup questions (one at a time)

The AI asks these six questions, one at a time, waiting for each answer before proceeding:

1. "Describe in a couple of lines or less what you want a DoView of."
2. "Will you supply all the information yourself, or should I use my general knowledge about this topic?"
3. "What do you want the DoView called? (e.g. 'The Something Initiative DoView')"
4. "How many subpages do you want: a normal-sized DoView (approximately fewer than 10 subpages) or a more comprehensive DoView?"
5. "How much detail do you want on the subpages: simple (approximately fewer than 15 boxes per subpage) or more detailed?"
6. "Do you want to include a Sources page?"

After Q6, the AI proceeds to Stage 1 without asking additional questions.

### 4.2 Stage 1 — Subpage structure

The AI drafts the subpage list and presents it for confirmation. Naming conventions enforced by the prompt:

- Lay-reader-friendly names ("Government Action", "Sector Activity", "Coordination") rather than "input/process/outcomes" generics.
- Subpages are NOT just input/process/outcomes — they reflect the domain.
- Final box(es) on subpages should be lower-level than the overall final outcomes.
- Externally focused pages distinguished from internal governance/operations pages; internal ones at the end.

The AI then asks for confirmation: "Do you want fewer/more pages, new pages added, specific pages renamed, or are you happy with this structure?" — and does not proceed until the user confirms.

### 4.3 Stage 2 — Detailed box content ("This-Then" logic)

This is the methodological heart. Each box represents **one** discrete outcome (not an activity); if achieving A tends to lead to B, place A to the left of B; never combine "This" and "Then" in one box.

**Outcome phrasing.** Outcomes end with "-ed" wherever natural: "Key knowledge identified", "Quality courses run", "Health status improved", "Customer segments understood".

**The 13 drafting steps** (from the handbook, encoded verbatim in the prompt):

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

**Structural reporting** (per subpage): `Structure: columns = N; rows per column = [c1, c2, c3, ...]`.

**Balance checks before presenting** (the AI runs these before showing the user):

1. Balance the level of detail across subpages
2. Scan for repeating patterns that shouldn't be there
3. Ensure structural variety reflects each domain area's unique logic
4. Verify all outcomes use proper "-ed" phrasing
5. Confirm one concept per box throughout

The AI then presents the full content and asks: "If you're happy with this, I'll generate the diagrams." — and does not proceed until the user confirms.

### 4.4 Stage 3 — Generate Iris JSON

The AI emits a single JSON document with the canonical Iris diagram shape. The slide ordering is mandatory:

1. Overview (with Final Outcomes tile and subpage navigation tiles)
2. Final Outcomes (stacked list of ultimate goals)
3. All subpages (in the user-confirmed order from Stage 1)
4. (Optional) Sources page — only if the user said yes to Q6

The Iris backend then **materialises** that JSON into actual diagrams (`backend/app/ai/creation.py:create_diagrams_from_ai`): one row per diagram, child elements + causal_links inserted, themes attached, parent_package wired up.

### 4.5 Where the methodology lives in code

The full prompt body — including the "Adapted from DoViewPlanning.org — AI DoView Drawing Prompt, created by Dr Paul Duignan" attribution at the top — is at `backend/app/seed/creation_prompts.py:DOVIEW_NOTATION_PROMPT`. It is loaded into the database by `m028_ai_creation_prompts.py` (initial seed) and `m040_expanded_ai_creation_prompts.py` (expansion). Subsequent migrations have not touched the body itself — admins can edit it via the GUI without migration churn.

---

## 5. The DoView Book handbook content in Iris

Dr Duignan's handbook content is loaded into Iris as a regular Iris Set. On the UAT instance:

| Property | Value |
|---|---|
| Set ID | `33032180-d77a-4ce4-88cf-b49cd643e093` |
| Set name | "DoView Book" |
| Diagram count | ~230 |
| Top-level packages | Chapters A through J (each chapter is a top-level Iris package) |
| Per-tool structure | A pair of diagrams: one "question" diagram + one "tool" diagram |
| Tool-page format | `notation=markdown, diagram_type=text` — markdown body with one embedded ```mermaid``` flowchart |

The pair convention lets the AI distinguish "what is this tool asking?" (the question diagram) from "how does it work?" (the tool diagram with its mermaid flowchart). In the diagram description: `kind: question · pair: <code>` vs `kind: tool · pair: <code>`. Iris's MCP `get_diagram` tool returns this whole markdown body as `data.content`, so an external AI can both quote the prose and embed the mermaid flowchart verbatim in a response. **Verbatim** is important — the system explicitly forbids redrawing or simplifying handbook diagrams.

The chapter packages organise tools by section (J = AI applications, I = introducing DoView into organisations, H = reporting frameworks, G = evaluation methods, F = performance improvement, E = social investment, D and below = earlier chapters of the handbook). When an external client calls `package_hierarchy(set_id)`, it gets the entire chapter tree in one response (ADR-158).

---

## 6. AI scaffolding for DoView and outcomes theory

Iris's AI subsystem has three layers that work together for DoView. Each layer is **admin-editable from the GUI** (`/admin/settings/ai`), so prompt iteration doesn't require code changes.

### 6.1 Layered creation prompts (cascade)

When a user creates a new DoView model in Iris's web UI, the system composes a single system prompt by stacking layers:

```
override (if any active for the notation, replaces all)
  └─ base                 (universal Iris JSON contract, stage discipline)
     └─ notation          (DoView Creation Methodology — section 4 above)
        └─ diagram_type   (outcomes_map layout / overview layout)
```

This composition is in `backend/app/ai/creation.py:build_creation_system_prompt(notation, diagram_type)`. The DoView-specific rows are seeded as `creation-doview-notation-v1`, `creation-doview-outcomes_map-v1`, `creation-doview-overview-v1` plus the universal `creation-base-v1`.

### 6.2 Response-format prompts (formal analyses)

Added v5.12.0 (ADR-157). The same layered mechanism, with a new `purpose` discriminator (`creation_format` vs `response_format`), governs the **shape of formal text+diagram analyses** of outcomes-theory questions. When asked "what does outcomes theory say about siloing program steps?", a properly configured client fetches the cascade for `(notation=markdown, diagram_type=doview_analysis)` and produces the three-section response:

1. **Summary response** — concise outcomes-theory answer with handbook citation
2. **Full response** — longer formal analysis with the outcomes-system definition (when relevant), the DoView "This-Then" model framing, principles invoked, and citations
3. **Diagrams from the handbook** — verbatim mermaid blocks from the referenced tool pages, each with its `https://doviewplanning.org/<paircode>doviewtool` URL

The seeded prompt rows for this are `response-format-base-v1`, `response-format-doview-notation-v1`, `response-format-doview-analysis-v1`.

### 6.3 Per-scope context (mcp_system_context)

The DoView Book Set carries an MCP-side context field (ADR-156) that tells external AI clients how to navigate this specific set: which response_format to fetch, how to find chapters, conventions for offering save options. The canonical content is at `docs/prompts/doview-book-mcp-system-context.md` and is copy-pasted into the Set's `mcp_system_context` field on UAT.

---

## 7. The MCP surface — how external AI clients access DoView content

Iris ships an MCP server (`iris-mcp`) so external AI clients (Claude Desktop, Claude Code, etc.) can browse and reason about DoView content in conversation. The DoView-relevant tools:

| MCP tool | Purpose |
|---|---|
| `get_set` | Returns set metadata. Includes `package_count` and `package_count_root` (added v5.13.0) so clients see structural breadth upfront. The DoView Book Set's `mcp_system_context` arrives in this response too — it's the AI client's first orientation. |
| `package_hierarchy` *(v5.13.0)* | Returns the complete chapter tree for a set in one call — preferred over `list_packages` for "give me the table of contents". Fixes a v5.12.x issue where pagination caused older chapters to be missed. |
| `list_packages` | Paginated package list (extended v5.13.0 with `page`, `page_size`, `parent_package_id` filters). |
| `get_diagram` | Returns a single tool-page diagram including its `data.content` (markdown body with embedded mermaid). |
| `search` | Full-text search across the set — used to find tool pages relevant to a user's outcomes-theory question. |
| `get_response_prompt` *(v5.12.0)* | Returns the composed `response_format` cascade for a `(notation, diagram_type)` pair. The client fetches this and follows it as the rules for shaping the response. |
| `list_response_format_types` *(v5.12.0)* | Lets the client discover what response formats are available (`(markdown, doview_analysis)` for the DoView use case). |
| `save_doview_analysis` *(v5.12.0)* | Persists a generated analysis as a new `doview_analysis` diagram in the chosen Iris Set. Auth-required (uses the MCP server's `IRIS_TOKEN`). Useful for an authenticated user who wants their analysis saved alongside the handbook. |
| `apply_diagram_creation` | Pre-existing — applies an AI-generated DoView model JSON (Stage 3 output from section 4.4) to a Set, materialising the diagrams in Iris. |

---

## 8. End-to-end flows you should see working

### 8.1 A user creates a brand-new DoView model in Iris's web UI

1. User: "Create new diagram → notation: DoView → diagram type: outcomes_map".
2. Iris's AI composes the layered creation prompt (override → base → DoView notation → outcomes_map layout) and starts the conversation at Stage 0.
3. AI walks the user through Q1–Q6 (one question at a time), then Stage 1 (subpage structure with confirmation), Stage 2 (detailed boxes with the 13 drafting steps + balance checks), and Stage 3 (Iris JSON output).
4. Backend materialises the JSON into an Overview page + Final Outcomes page + N subpages + (optional) Sources page in the chosen Iris Set.

### 8.2 A user asks Claude Desktop a DoView question via Iris MCP

1. User in Claude Desktop: "Give me an outcomes-theory analysis of siloing program steps."
2. Claude calls `get_set` on the DoView Book Set → sees `package_count_root=10` and the `mcp_system_context` pointer.
3. Claude calls `get_response_prompt(notation='markdown', diagram_type='doview_analysis')` → gets the formal three-section rules.
4. Claude calls `search` and `get_diagram` against the set to find the relevant tool pages (e.g. B16 "Do Not Silo Steps Under Outcomes Explainer") and extract the mermaid blocks from `data.content`.
5. Claude composes the formal three-section response (Summary + Full + Diagrams), with handbook citations and verbatim mermaid blocks.
6. Claude offers two save paths: persist as a `doview_analysis` diagram in Iris (via `save_doview_analysis`), or present as a markdown artefact in chat for the user to copy.

### 8.3 An admin tunes the DoView creation methodology

1. Navigate to `/admin/settings/ai` → AI Prompts section.
2. Filter `purpose=creation_format`, `notation=doview`. The DoView creation rows appear.
3. Edit `creation-doview-notation-v1` body. Save.
4. Next user who creates a DoView model gets the updated methodology immediately — no redeploy.

---

## 9. Architectural decisions (ADRs and SPECs)

The full design history is in `docs/adrs/`. The DoView-and-outcomes-theory line of work spans:

| ADR / SPEC | Decision |
|---|---|
| [ADR-094](adrs/ADR-094-DoView-Notation-AI-Creation.md) | Add DoView as a fifth notation; build modular AI diagram creation system with database-stored layered prompts |
| [SPEC-094-A](adrs/specs/SPEC-094-A-DoView-Notation.md) | DoView notation: element types, relationship type, diagram types, theme, renderer |
| [SPEC-094-B](adrs/specs/SPEC-094-B-AI-Diagram-Creation.md) | AI creation system: schema, composer, materialiser, endpoints |
| [ADR-103](adrs/ADR-103-Extensions-Framework.md) | Extensions framework (Mnemos plugs into this) |
| [ADR-111](adrs/ADR-111-MNEMOS-Semantic-Retrieval.md) | Mnemos semantic-retrieval extension (vector index for Ask AI; not used directly for DoView structure but available for handbook-content search ranking) |
| [ADR-132](adrs/ADR-132-Expanded-AI-Creation-Notations.md) | Layered creation prompts cascade (Simple, UML, ArchiMate, C4 added; same layering DoView already used) |
| [SPEC-132-A](adrs/specs/SPEC-132-A-Expanded-AI-Creation-Notations.md) | Layered prompt schema and seeds |
| [ADR-150](adrs/ADR-150-Scope-Level-System-Prompts.md) | Per-scope `system_prompt` (used for Iris's own AI flows about a set) |
| [ADR-151](adrs/ADR-151-MCP-Boundary-Strips-Scope-System-Prompts.md) | MCP boundary strips `system_prompt` (anti-injection) |
| [ADR-152](adrs/ADR-152-MCP-Prompts-Capability-for-Scope-System-Prompts.md) | MCP `prompts` channel for scope content |
| [ADR-153](adrs/ADR-153-Drop-Redundant-iris-Prefix-From-MCP-Prompt-Names.md) | MCP prompt naming convention |
| [ADR-154](adrs/ADR-154-Multiple-Named-Prompts-per-Scope.md) | Multiple named prompts per scope |
| [ADR-155](adrs/ADR-155-Strict-Split-Iris-AI-vs-MCP-Scope-Prompts.md) | (Superseded in part) split scope prompts into Iris-AI and MCP |
| [ADR-156](adrs/ADR-156-MCP-System-Context-Data-Passthrough.md) | `mcp_system_context` as data passthrough on `get_set` / `get_collection` |
| [ADR-157](adrs/ADR-157-Response-Format-Prompts-and-DoView-Analysis-Artefact.md) | Response-format prompts + `doview_analysis` artefact type |
| [SPEC-157-A](adrs/specs/SPEC-157-A-Response-Format-Prompts.md) | Response-format schema, endpoints, MCP wiring |
| [ADR-158](adrs/ADR-158-Admin-Prompts-Management-and-MCP-Set-Structure.md) | Admin AI prompts CRUD + MCP set-structure overview |
| [SPEC-158-A](adrs/specs/SPEC-158-A-Admin-Prompts-Management-and-MCP-Set-Structure.md) | Admin GUI redesign + `package_hierarchy` MCP tool |

The accumulation pattern: ADR-094 introduced DoView as a notation and the AI creation infrastructure; ADR-132 generalised the prompt layering to other notations (proving DoView's pattern was reusable); ADR-150–158 built the *response* counterpart so DoView-grounded analyses can be produced and saved through the same admin-editable mechanism — and exposed via MCP for external AI clients.

---

## 10. Where Iris diverges from the handbook (and where it doesn't)

Iris is deliberately implementation; the methodology is the handbook's. Conscious choices Iris has made:

- **Structured stage discipline.** The setup-questions-then-confirm-subpages-then-confirm-content cadence is enforced by the prompt body, not by the underlying methodology. The handbook describes the methodology; Iris insists on the conversational rhythm so users get consistent guided creation.
- **Iris JSON output schema.** Stage 3 emits a specific JSON shape so the backend can materialise it into actual diagrams. This is purely a technical contract; the conceptual content matches the handbook.
- **`doview_analysis` as a markdown artefact under `notation=markdown`** (rather than under `notation=doview`). The output is text + embedded mermaid, not a visual outcomes map; classifying it under markdown matches its actual medium. The DoView/outcomes-theory framing is in the body.
- **Cycling colour palette.** The handbook describes box colour as a visual differentiator; Iris standardises a 10-colour palette that cycles deterministically per subpage. Visual consistency, no methodological change.
- **Verbatim-mermaid rule** when reproducing handbook diagrams in formal analyses. Iris explicitly forbids the AI from redrawing, simplifying, or relabelling tool-page diagrams. Faithfulness to the handbook source over editorial polish.

Where Iris has *not* diverged: the 13 drafting steps, the "-ed" outcome phrasing, the "This-Then" causal logic, the slide ordering (Overview → Final Outcomes → subpages → optional Sources), the prohibition on conflating "This" and "Then" in one box, the world-centric rather than initiative-centric framing, the wording "DoView Board, a specific type of outcomes model that is drawn to conform to the principles of outcomes theory", and the requirement to present DoView as the practical applied form of outcomes theory rather than a primary theory in itself. These are encoded in the prompt bodies verbatim from the handbook and are not editorialised.

---

## 11. External references

- **DoView Planning Org** — https://doviewplanning.org/
- **The handbook** — Duignan, P. (2025). *DoView Planning and Outcomes Theory Handbook: 100+ Innovative, Integrated Tools for Solving Key Issues in Planning, Implementation, Contracting, Measurement, Evaluation and Reporting (for Humans and AI Agents)*. DoViewPlanning.Org. https://doviewplanning.org/book
- **Tool pages** — `https://doviewplanning.org/<paircode>doviewtool` (e.g. `b16doviewtool`, `j07doviewtool`)
- **AI DoView Drawing Prompt** — the source from which Iris's DoView creation methodology prompt is adapted (with attribution preserved at the top of the prompt body)

DoView is a registered trademark of Dr Paul W Duignan.

---

## 12. For Dr Duignan, in plain terms

If you read only one section: **section 4** describes how Iris implements your creation methodology. The relevant code file is `backend/app/seed/creation_prompts.py` (look for `DOVIEW_NOTATION_PROMPT`); your attribution is at the top of that prompt body, where it has been since v3.x of Iris. The prompt is editable through Iris's `/admin/settings/ai` page without redeployment, so when the handbook evolves, the implementation can keep pace.

The handbook content itself lives as a regular Iris dataset (the "DoView Book" set, 230 diagrams across chapters A–J). External AI tools — Claude Desktop being the primary one we've tested — can browse, search, and cite this content via Iris's MCP server. When an outcomes-theory question is asked through Claude Desktop, the AI fetches the formal-response rules from Iris (these are also editable through the same admin GUI), composes a three-section response (Summary + Full + Diagrams with verbatim mermaid extracts), and offers to save the result back into Iris as a `doview_analysis` artefact.

The architecture aims to honour two principles you've emphasised in the handbook: that **outcomes theory is the primary frame and DoView is the applied practical form**; and that **the handbook's content is the canonical source** — Iris does not try to substitute general AI knowledge for the handbook's specific tools and methodology. Both are enforced in the prompt bodies.

If anything in the implementation appears to misrepresent your work, the right path to fix it is: edit the relevant prompt body in `/admin/settings/ai`, save, and the change takes effect on next interaction. No engineering change is required for editorial corrections to the methodology. If something in the underlying notation, schema, or diagram engine needs to change, the maintainers will be glad to engage — open an issue at https://github.com/cgbarlow/iris/issues or email the project team.
