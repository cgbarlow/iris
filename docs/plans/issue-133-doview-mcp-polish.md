# Plan: DoView MCP flow polish + MCP/CLI parity (issue #133)

## Context

Issue #133 captures the first end-to-end UAT of the v6.0.15 DoView creation cascade
(Outcomes Theory Book → Macroeconomics of Banana Monoculture). The flow worked,
but the user surfaced **two classes of feedback** that need a coordinated response:

**Class A — DoView creation cascade UX (turns 1–13 of the transcript at
`https://github.com/user-attachments/files/27839763/banana-monoculture-doview-conversation.md`)**

1. Every cascade question must be asked via the MCP client's user-question tool
   (`AskUserQuestion` in Claude Code / Claude Desktop), not as prose. Currently the
   `_DOVIEW_NOTATION_PROMPT` seeded in
   `backend/app/migrations/m028_ai_creation_prompts.py:117` lists questions in prose
   and the model picks how to surface them. Turn 1 (option menu after orient) and
   turns 3–10 (cascade Q&A) were inconsistent on this.
2. Turn 4 (info-source question) must allow paste-own-info or file upload, not just
   "general / supplied". Today the cascade collapses to a binary.
3. Turn 5 (DoView name) must propose a default derived from the subject and let the
   user accept or override. Today the model asks open-ended.
4. Turn 8 (Sources page) — the `outcomes_map` Sources page in the generated bundle
   contains only names, not URLs. The `(markdown, doview_analysis)` response-format
   prompt already enforces raw-URL citations (m051 lines 59–67) but the
   `(doview, outcomes_map)` creation-format prompt at m028:130 does not.
5. Turn 9 (subpage structure confirmation) must offer three options: **skip detailed
   review (default)**, **proceed to detailed box content review**, **suggest changes
   to subpage structure**. Today the model jumps straight into Stage 2 detail.
6. Turn 11 (save destination) — this is the largest gap. Once content is drafted,
   the cascade must ask:
   - **Save where?** Chat with downloadable artefacts / Iris (source of truth) /
     both.
   - If downloadable: which format(s)? Markdown / Word docx / PDF (multi-select).
     Docx + PDF conversion based on the Anthropic skills at
     `github.com/anthropics/skills/tree/main/skills/docx` and `/skills/pdf`.
   - If Iris: where? **Default = new set beneath the parent collection of the set
     being viewed** / "let me browse" (list root collections) / **current set** /
     "somewhere else" (free-text path or id). These options must be generic across
     any Set being browsed, not Outcomes Theory–specific.
7. Turn 12 — the consequence of #6 not existing: content landed in the wrong set
   (the Outcomes Theory Book). Closing the loop on #6 closes this.
8. Turn 13 — Iris MCP must be able to **move** content between parents (diagram →
   different package/set, package → different parent or set, set → different
   collection). Today MCP exposes no update/move tools; only `create_*` and the
   read tools. Backend already supports most moves (`PUT /packages/{id}/parent`,
   `PUT /sets/{id}` accepts `collection_id`) but diagrams cannot be re-parented.

**Class B — Surface parity & metadata editability**

9. Iris MCP must be able to **edit all entity metadata** (collection, set, package,
   diagram, element). Today MCP has no `update_*` tools. Backend has
   `PUT /collections/{id}`, `PUT /sets/{id}`, `PUT /packages/{id}`,
   `PUT /diagrams/{id}`, plus element updates — all surfaced through the FastAPI
   routers in `backend/app/{collections,sets,packages,diagrams,elements}/router.py`.
10. CLI / API / MCP parity. CLI today (`cli/src/iris_cli/main.py`) is read-only +
    `ask` + `export`. MCP today is `create_*` + read tools (no `update_*`, no
    `move_*`, no `delete_*`). The protocols require CLI ↔ API ↔ MCP parity for
    write operations.
11. Class A #6 ("save options for AI-generated content") must also be available in
    the Iris GUI for any diagram with text content (`outcomes_map` exports,
    `doview_analysis` markdown, etc.) — md/docx/pdf download from the diagram view.

The orient/instructions infrastructure shipped in v5.18.0 (ADR-163) is the right
surface to land the cascade-UX rules. The DRY discipline of protocols §13 means the
docx/pdf renderer used by the GUI export must also be reachable from the MCP
artefact-download path so model and human take the same code path.

## Decisions

| # | Decision |
|---|---|
| 1 | Group the work into **six phases**, each with its own ADR + SPEC + branch + PR, sequenced so each phase is independently shippable. The phases form a single coherent issue-#133 epic but ship as separate releases (v6.1.0–v6.6.0). Plan-time choice over single mega-PR because Class A items are user-visible polish ready now, while Class B (CLI parity, GUI export) is a larger refactor that should not block the polish. |
| 2 | **Class A #1 (use the MCP client's user-question tool)**: encode as an explicit rule inside the `creation_format` cascade prompt itself, NOT inside the MCP `instructions` channel. Reason: the rule is creation-cascade-specific; it should not apply to every MCP turn (e.g. orient menu already lives in the per-scope `mcp_system_context`). The rule lands as a new "ASKING QUESTIONS" section in the `_DOVIEW_NOTATION_PROMPT` seed (m028) and as the first paragraph of a new shared `creation-cascade-shared-v1` base prompt that future notations import. |
| 3 | **Class A #2 (paste/upload at info-source step)**: implement as a three-option AskUserQuestion (`General knowledge` / `I will paste my own content` / `I will attach a file`) plus a follow-up free-text prompt when the user picks paste/upload. File attachment is delegated to the MCP client's native attachment mechanism — the cascade simply instructs "wait until the user has shared the content, then summarise back for confirmation before continuing." No new MCP tool. |
| 4 | **Class A #3 (default DoView name)**: rewrite cascade Q3 to "I'd suggest naming it `<subject> DoView` — keep this, or pick a different name?" with `Keep "<subject> DoView"` as option 1 and `Use a different name` as option 2. |
| 5 | **Class A #4 (Sources URLs)**: extend `_OUTCOMES_MAP_PROMPT` at m028:130 with an explicit Sources subpage rule mirroring m051's URL convention — every `source_reference` box's `data.label` must be `Author/Org · Title · YYYY · <raw https URL>`. Same raw-URL rule, no markdown links. |
| 6 | **Class A #5 (skip-detail branching)**: replace the Stage 1→Stage 2 hand-off in `_DOVIEW_NOTATION_PROMPT` with an explicit three-option AskUserQuestion: `Skip detail review and generate (recommended)` / `Review detailed box content first` / `Refine subpage structure first`. Default is skip. |
| 7 | **Class A #6 (save destination)**: introduce a **destination-chooser sub-cascade** that fires after Stage 2 (or after Stage 1 if user picked skip-detail). It is generic — applies to any `creation_format` cascade for any notation. Encoded once in a new `creation-cascade-destination-v1` base prompt (display_order 1 above the notation-specific prompts). |
| 8 | **Class A #6 (docx/pdf rendering)**: adopt the Anthropic skills' approach (Python — `python-docx` + `markdown-it-py` for docx; `weasyprint` + a markdown CSS template for pdf) and build a single **renderer module** in `backend/app/export/renderers/`. Reachable via (a) new backend endpoints `GET /api/export/diagram/{id}?format={md,docx,pdf}` and `GET /api/export/markdown?format=...` (POST-body markdown source for ad-hoc content), and (b) wrapped MCP read tools `export_diagram(diagram_id, format)` and `render_markdown(markdown, format)` that return base64-encoded blobs. Skill *content* (the prompts) is not vendored — the *capabilities* the skills provide (md → docx, md → pdf) are reimplemented as first-party Iris code so they're available to non-MCP surfaces (GUI, CLI). |
| 9 | **Class A #8 / B #9 (update + move tools)**: every entity gets `update_*` and `move_*` MCP tools. Add backend endpoints where missing: `PATCH /diagrams/{id}` already supports `package_id` and `set_id` changes (verify in spec); add `PUT /sets/{id}/collection` if not already present (`PUT /sets/{id}` already accepts `collection_id` per backend router — verify). New endpoint: none expected for elements (already covered by `PUT /elements/{id}`). |
| 10 | **Class B #10 (CLI parity)**: extend `cli/src/iris_cli/main.py` with `create`, `update`, `move`, `delete` subcommand groups for each entity type. Share the iris-client SDK (`iris_client` package or equivalent) between CLI, MCP, and AI so all three surfaces hit the same service code. |
| 11 | **Class B #11 (GUI export options)**: add an "Export…" menu to any diagram view that exposes Markdown / Docx / PDF for markdown-content diagrams, and Markdown / Docx / PDF / SVG / PNG for visual diagrams. Reuse the renderer endpoint from decision #8. Replace the ad-hoc `frontend/src/lib/utils/export.ts` PDF path (jsPDF — visual rasterisation only) with a unified two-track flow: visual diagrams continue using client-side rasterisation for SVG/PNG; markdown/docx/pdf-of-text always go through the backend renderer. |
| 12 | **Cascade prompt strategy**: the `creation_format` ladder fetched by `get_response_prompt(notation='doview', diagram_type='outcomes_map', purpose='creation_format')` composes BASE + NOTATION + DIAGRAM_TYPE in order (m028 already supports this layering). New `creation-cascade-shared-v1` (base) and `creation-cascade-destination-v1` (base, display_order 1) prompts are added at the base layer so they apply to all notations, not just DoView. |
| 13 | **TDD ordering** per protocols §3: each phase's failing tests written first against the SPEC's acceptance criteria, then the implementation. For prompt seeds, the test is a query of the composed prompt asserting the new sections appear; for renderer endpoints, the test is fixture-md → fixture-docx round-trip via `python-docx` reader; for MCP `update_/move_` tools, the test creates an entity, mutates it, and asserts via the read tool. |
| 14 | **Versioning**: bump minor on each phase: v6.1.0 (cascade prompt polish), v6.2.0 (move/update MCP tools), v6.3.0 (renderer + destination-chooser), v6.4.0 (CLI parity), v6.5.0 (GUI export options), v6.6.0 (parity ADR + reconciliation). Each release follows `feedback_release_workflow` memory — GitHub release published on every version bump. |
| 15 | **README & CHANGELOG updates**: every phase updates its surface's README (mcp/README.md, cli/README.md, frontend not applicable, backend not applicable) and adds entries under `[Unreleased]` → versioned section. Protocols §5, §12. |
| 16 | **No `delete_*` MCP tools yet**: out of scope for #133. The user's "move content" need is fully covered by update + move. Delete-via-MCP is a separate decision (audit trail, undo, etc.) and gets its own ADR later if asked. |
| 17 | **Element metadata edit scope**: "all element metadata" interpreted as the full element JSON payload (name, description, data, metadata) excluding identity (id, diagram_id). Element re-parenting between diagrams is rejected — elements live within their diagram. |

## ADRs to create

| ADR | Title | Phase | Supersedes |
|-----|-------|-------|------------|
| ADR-176 | Generic creation-cascade destination chooser | A1 | extends ADR-162 |
| ADR-177 | AskUserQuestion convention in creation cascades | A1 | extends ADR-167 |
| ADR-178 | MCP update_* and move_* tool surface | A2 | extends ADR-161 |
| ADR-179 | Server-side md → docx + md → pdf renderer | A3 | new capability |
| ADR-180 | CLI write-tool parity with MCP | A4 | new capability |
| ADR-181 | Unified diagram export options in the GUI | A5 | supersedes the export-utils-only path in `frontend/src/lib/utils/export.ts` |
| ADR-182 | CLI/API/MCP parity discipline | A6 | meta-ADR cross-referencing 178/180/181 |

## SPECs to create

`docs/adrs/specs/SPEC-176-A-Cascade-Destination-Chooser.md`,
`SPEC-177-A-AskUserQuestion-In-Cascades.md`,
`SPEC-178-A-MCP-Update-Move-Tools.md`,
`SPEC-179-A-Markdown-Docx-Pdf-Renderer.md`,
`SPEC-180-A-CLI-Write-Parity.md`,
`SPEC-181-A-Unified-Diagram-Export-GUI.md`,
`SPEC-182-A-Surface-Parity-Discipline.md`.

## Phases & files

### Phase 1 — Creation-cascade UX polish (v6.1.0)

**Branch:** `feature/issue-133-cascade-polish`

**Scope:** Class A items #1–#5 plus the destination-chooser scaffolding from #6
(prompt-only — actual rendering and Iris-write of artefacts lands in Phase 3).

**Create:**

- `docs/adrs/ADR-176-Generic-Cascade-Destination-Chooser.md`
- `docs/adrs/ADR-177-AskUserQuestion-In-Creation-Cascades.md`
- `docs/adrs/specs/SPEC-176-A-Cascade-Destination-Chooser.md`
- `docs/adrs/specs/SPEC-177-A-AskUserQuestion-In-Cascades.md`
- `backend/app/migrations/m054_cascade_ux_polish.py` —
  - INSERTs new base-layer row `creation-cascade-shared-v1` (`layer=base`,
    `notation=NULL`, `diagram_type=NULL`, `display_order=1`, `purpose='creation_format'`)
    with content from decision #2 (the "ASKING QUESTIONS" rule) + paste/upload affordance
    text (decision #3) + skip-detail branching template (decision #6) + destination-chooser
    template (decision #7 prompt-side only — instructs the model to ask the
    save-where/format-which/iris-where questions, but the iris-write moves and
    docx/pdf rendering are no-ops until Phase 2 + Phase 3 land).
  - UPDATEs `creation-doview-notation-v1` `prompt_text` — rewrites the "Guided
    conversation" block to defer to the shared cascade, add the default-name
    suggestion at Q2/Q3, and remove the now-shared bits.
  - UPDATEs `creation-outcomes-map-v1` `prompt_text` — adds the Sources URL rule
    (decision #5) as a new "Sources subpage requirements" section.
- `backend/app/migrations/supabase/m058_cascade_ux_polish.sql` — Supabase mirror of
  the SQLite migration. Same row inserts/updates.
- `backend/tests/migrations/test_m054_cascade_ux_polish.py` — TDD red:
  - Asserts composed `creation_format` prompt for `(doview, outcomes_map)`
    contains `"AskUserQuestion"` (or the equivalent client-tool token —
    `creation-cascade-shared-v1` body), the paste-own-content rule, the
    skip-detail template, the destination-chooser template, the default-name
    template, and the Sources URL rule.
  - Asserts the composed prompt for any other notation (e.g. `bpmn`,
    `process_flow`) also contains the shared cascade rules (paste/upload,
    AskUserQuestion convention, destination chooser) — proving the prompt is
    generic, not DoView-specific.
- `docs/prompts/doview-book-creation-cascade-shared.md` — paste-ready canonical
  body for the new shared base prompt (admin recovery doc, mirrors the
  `mcp-server-instructions.md` pattern).

**Modify:**

- `mcp/README.md` — document the new cascade behaviour and the destination chooser
  flow.
- `CHANGELOG.md` — add `[6.1.0]` section under Added/Changed.

**Tests:**

- Red-first: `test_m054_cascade_ux_polish.py` (above) fails before the migration runs.
- Green: migration applied, all assertions pass.
- Manual UAT replay against UAT environment: re-run the banana-monoculture flow,
  confirm Q3 proposes default name, Q4 offers paste/upload, Q9 offers skip-detail,
  Q11 offers destination chooser. (Phase 1 only verifies the prompt surfaces the
  questions — answering "save to Iris elsewhere" still won't actually move/save
  until Phase 2.)

**Acceptance gates:**

- All m054 tests green.
- `get_response_prompt(notation='doview', diagram_type='outcomes_map', purpose='creation_format')`
  body contains every new section.
- Existing `test_outcomes_map_layout` (if it exists — verify) still green.

### Phase 2 — MCP update_* + move_* tools (v6.2.0)

**Branch:** `feature/issue-133-mcp-update-move`

**Scope:** Class A #8 and Class B #9.

**Create:**

- `docs/adrs/ADR-178-MCP-Update-Move-Tools.md`
- `docs/adrs/specs/SPEC-178-A-MCP-Update-Move-Tools.md`
- New MCP tool definitions in `mcp/src/iris_mcp/tools.py`:
  - `update_collection(collection_id, name?, description?, thumbnail_source?, thumbnail_diagram_id?, system_prompt?, mcp_system_context?)` — wraps `PUT /collections/{id}`.
  - `update_set(set_id, name?, description?, system_prompt?, mcp_system_context?)` — wraps `PUT /sets/{id}` (without `collection_id`; moves are separate).
  - `update_package(package_id, name?, description?, metadata?, if_match?)` — wraps `PUT /packages/{id}`.
  - `update_diagram(diagram_id, name?, description?, data?, metadata?)` — wraps `PUT /diagrams/{id}`.
  - `update_element(element_id, name?, description?, data?, metadata?)` — wraps `PUT /elements/{id}`.
  - `move_diagram(diagram_id, target_package_id?, target_set_id?)` — wraps either `PATCH /diagrams/{id}/parent` (new) or composes via existing `PUT /diagrams/{id}` if those fields are mutable.
  - `move_package(package_id, target_parent_package_id?, target_set_id?)` — wraps existing `PUT /packages/{id}/parent` (cross-set move needs new backend support; see below).
  - `move_set(set_id, target_collection_id)` — wraps `PUT /sets/{id}` `collection_id`.
- New backend endpoints where missing:
  - `PATCH /diagrams/{id}/parent` in `backend/app/diagrams/router.py` if the
    existing `PUT /diagrams/{id}` does not already accept `package_id` and
    `set_id` changes. Spec-time investigation will resolve which is current.
  - `PUT /packages/{id}/parent` extended to accept `target_set_id` for
    cross-set moves (today it cycle-checks within a single set).
- Tests:
  - `mcp/tests/test_update_tools.py` — create entity → call `update_*` → assert
    via `get_*` that fields changed; assert MCP-side response includes the
    decorated `web_url` (ADR-175 compliance).
  - `mcp/tests/test_move_tools.py` — fixture multi-collection + multi-set graph
    → `move_diagram` / `move_package` / `move_set` → assert via
    `package_hierarchy` that the tree updated correctly.
  - `backend/tests/diagrams/test_move.py` — direct REST test of `PATCH
    /diagrams/{id}/parent`.
  - `backend/tests/packages/test_cross_set_move.py` — direct REST test of
    `PUT /packages/{id}/parent` with `target_set_id`.

**Modify:**

- `mcp/src/iris_mcp/tools.py` — tool registration + handlers.
- `mcp/src/iris_mcp/links.py` — extend `with_web_url` decoration to
  `update_*` returns and `move_*` returns (consistency with ADR-175).
- `mcp/src/iris_mcp/server_instructions.py` — add a paragraph in the
  `_FALLBACK_INSTRUCTIONS` explaining update_* / move_* tools.
- `backend/app/diagrams/router.py` if new endpoint needed.
- `backend/app/packages/router.py` for cross-set move support.
- `backend/app/migrations/m053_mcp_server_instructions_seed.py` — refresh the
  seeded body so the WORKFLOW GUIDANCE section names the new tools.
- `backend/app/migrations/supabase/m057_mcp_server_instructions_seed.sql` — mirror.
- `docs/prompts/mcp-server-instructions.md` — refresh.
- `CHANGELOG.md` — `[6.2.0]` section.

**Acceptance gates:**

- All Phase 2 tests green.
- Manual UAT: from Claude Code, after Phase 1's destination-chooser surfaces the
  "save to current set" or "save to different set" choice, Phase 2's move tool
  successfully relocates the just-created bundle.

### Phase 3 — Renderer + destination-chooser actuation (v6.3.0)

**Branch:** `feature/issue-133-renderer`

**Scope:** Class A #6 backend half.

**Create:**

- `docs/adrs/ADR-179-Server-Side-Md-Docx-Pdf-Renderer.md`
- `docs/adrs/specs/SPEC-179-A-Markdown-Docx-Pdf-Renderer.md`
- `backend/app/export/renderers/__init__.py`
- `backend/app/export/renderers/markdown.py` — passthrough (md is already md, just
  ensure stable normalisation).
- `backend/app/export/renderers/docx.py` — md → docx via `python-docx` +
  `markdown-it-py`. Recipe modelled on
  `github.com/anthropics/skills/tree/main/skills/docx` (read at spec time and
  reimplement the conversion logic).
- `backend/app/export/renderers/pdf.py` — md → pdf via `weasyprint` + a default
  CSS template (matches the `anthropics/skills/pdf` skill's
  approach). Iris-branded CSS lives in `backend/app/export/renderers/styles/iris.css`.
- Backend endpoint `GET /api/export/diagram/{id}?format={md,docx,pdf}` in
  `backend/app/export/router.py`. For markdown-content diagrams: take
  `data.content`. For visual diagrams (e.g. outcomes_map): export the existing
  markdown summary or refuse with 400 + message ("visual diagram — use SVG/PNG
  client export instead").
- Backend endpoint `POST /api/export/markdown?format=...` — body: `{markdown:
  str, title: str}`. For ad-hoc rendering of AI-generated content that hasn't
  been saved.
- MCP tools `export_diagram(diagram_id, format)` and `render_markdown(markdown,
  title, format)` in `mcp/src/iris_mcp/tools.py`. Returns
  `{filename, mime_type, base64_content}`. MCP client decodes and writes to the
  user's download path.
- Update `_DOVIEW_NOTATION_PROMPT` or shared cascade prompt (m054) to instruct
  the model: when the user picks "downloadable artefacts" at Q11, call
  `render_markdown` for each selected format; when user picks "Iris + download",
  do both.

**Tests:**

- `backend/tests/export/test_md_to_docx.py` — fixture md → render → parse with
  `python-docx` → assert structure (headings, lists, code blocks, embedded
  mermaid passes through as code block).
- `backend/tests/export/test_md_to_pdf.py` — fixture md → render → assert PDF
  byte-header valid + page count.
- `mcp/tests/test_export_tools.py` — MCP tool round-trip.

**Modify:**

- `backend/pyproject.toml` — add `python-docx`, `markdown-it-py`, `weasyprint`.
  Per protocols §11, pin latest stable as of implementation date and document
  versions in commit message.
- `backend/app/export/router.py` for new endpoints.
- `CHANGELOG.md` — `[6.3.0]` section.

**Acceptance gates:**

- Renderer tests green.
- Manual UAT: replay banana flow, pick "both", select md+docx+pdf, receive three
  files; pick "current set" for Iris save, see content in the right place.

### Phase 4 — CLI parity (v6.4.0)

**Branch:** `feature/issue-133-cli-parity`

**Scope:** Class B #10.

**Create:**

- `docs/adrs/ADR-180-CLI-Write-Tool-Parity.md`
- `docs/adrs/specs/SPEC-180-A-CLI-Write-Parity.md`
- New CLI subcommand groups in `cli/src/iris_cli/main.py`:
  - `iris create {collection|set|package|diagram}` mirroring MCP create_* args.
  - `iris update {collection|set|package|diagram|element}` mirroring update_*.
  - `iris move {diagram|package|set}` mirroring move_*.
  - `iris export {diagram|markdown}` for the new renderer (extends existing
    `iris export` group).
- Shared client helper: confirm `iris-client` SDK (Python) is the shared layer.
  If MCP and CLI today re-implement against `httpx` directly, factor a
  `iris_client.write` module and reuse. DRY (protocols §13).

**Tests:**

- `cli/tests/test_create_commands.py`
- `cli/tests/test_update_commands.py`
- `cli/tests/test_move_commands.py`
- `cli/tests/test_export_commands.py` — fetch then write to a tempfile.

**Modify:**

- `cli/README.md` — document new subcommands.
- `CHANGELOG.md` — `[6.4.0]`.

**Acceptance gates:**

- CLI tests green.
- `iris create set --name X --collection-id Y` succeeds; `iris move diagram
  <id> --to-package <pkg>` succeeds; `iris export diagram <id> --format docx
  --output ./out.docx` writes a valid docx file.

### Phase 5 — GUI export options (v6.5.0)

**Branch:** `feature/issue-133-gui-export`

**Scope:** Class A #6 GUI / Class B #11.

**Create:**

- `docs/adrs/ADR-181-Unified-Diagram-Export-GUI.md`
- `docs/adrs/specs/SPEC-181-A-Unified-Diagram-Export-GUI.md`
- New `frontend/src/lib/components/DiagramExportMenu.svelte` — dropdown with
  Markdown / Docx / PDF / SVG / PNG. Shown on every diagram view. For
  markdown-content diagrams hides SVG/PNG; for visual diagrams hides
  Markdown/Docx unless a markdown summary exists.
- Frontend tests in `frontend/tests/e2e/diagram-export.spec.ts` — visit a
  markdown-content diagram, click Export → Docx, intercept the download,
  validate it's a real docx (server returns valid bytes).

**Modify:**

- `frontend/src/lib/utils/export.ts` — keep client-side SVG/PNG path; route
  Markdown/Docx/PDF to the new backend endpoint. Remove the jsPDF visual-pdf
  path (it's a rasterised picture, superseded by the renderer's actual pdf).
- `frontend/src/routes/.../+page.svelte` for every diagram view that currently
  imports the old export menu.
- `CHANGELOG.md` — `[6.5.0]`.

**Acceptance gates:**

- E2E export test green.
- Manual UAT: open any markdown diagram → Export → Docx → file opens in Word.
  Same for PDF.

### Phase 6 — Parity ADR + reconciliation (v6.6.0)

**Branch:** `docs/issue-133-parity-discipline`

**Scope:** Class B #10 follow-up. Cement the parity rule so future MCP/CLI/API
work doesn't drift again.

**Create:**

- `docs/adrs/ADR-182-Surface-Parity-Discipline.md` — the meta-ADR. Establishes:
  every backend write endpoint MUST have a matching MCP tool AND a matching CLI
  subcommand. Every MCP tool MUST have a corresponding CLI subcommand and a
  spec'd backend endpoint. Etc. Includes a parity matrix as living
  documentation.
- `docs/adrs/specs/SPEC-182-A-Surface-Parity-Discipline.md` — codifies the
  matrix, defines the audit script, defines the CI gate.
- `scripts/check_surface_parity.py` — scans backend routers, MCP tool defs, CLI
  commands; emits diffs. Wired into CI as a soft gate first, hard gate in
  v6.7.0.

**Modify:**

- `docs/protocols.md` — add §14 "Surface Parity" with one-line reference to
  ADR-182.
- `CLAUDE.md` — same reference.
- `CHANGELOG.md` — `[6.6.0]`.

**Acceptance gates:**

- `scripts/check_surface_parity.py` returns clean.
- CI runs the check.

## Implementation order

1. **Phase 1** (v6.1.0) — prompt-only; lowest risk; unblocks Phase 3 acceptance.
2. **Phase 2** (v6.2.0) — independent; can run in parallel with Phase 1 but
   merges second so Phase 1's destination-chooser has live move tools to call.
3. **Phase 3** (v6.3.0) — depends on Phase 2 (the destination-chooser actuator
   calls Phase 2's `move_*` tools when user picks "save in different Iris
   location"). The renderer half of Phase 3 is independent and could ship
   earlier as v6.2.0+ if Phase 2 slips.
4. **Phase 4** (v6.4.0) — depends on Phases 2 + 3 (renderer for `export`,
   `update_*`/`move_*` patterns established).
5. **Phase 5** (v6.5.0) — depends on Phase 3 renderer endpoint.
6. **Phase 6** (v6.6.0) — runs last; ratifies the parity established by Phases
   2–5.

## Verification (cross-phase)

- Replay the banana-monoculture flow at the end of each phase; expected behaviour
  at each phase:
  - Post-Phase 1: cascade asks all six new questions correctly via
    AskUserQuestion; destination-chooser appears but choosing "different set"
    falls back gracefully ("I can describe what should be created but cannot
    move it yet — Phase 2 ships v6.2.0").
  - Post-Phase 2: destination-chooser actually moves bundle to chosen
    set/collection.
  - Post-Phase 3: "downloadable artefacts" works — receive valid md/docx/pdf.
  - Post-Phase 4: same operations reproducible from CLI.
  - Post-Phase 5: GUI Export menu produces the same docx/pdf bytes the CLI/MCP do.
  - Post-Phase 6: parity check script clean.
- Each phase ships its own release per `feedback_release_workflow`: GitHub
  release published, tag pushed, CHANGELOG section moved out of `[Unreleased]`.

## Risks & mitigations

| Risk | Mitigation |
|------|------------|
| `weasyprint` adds heavy system deps to backend image | Vendor as optional via PyPI extra `iris[pdf]`; degrade gracefully if missing — return 503 with hint. Tested at Dockerfile level in Phase 3. |
| `python-docx` produces inconsistent layout across editions | Use Anthropic skill recipe verbatim as starting point; add golden-file tests against a stable fixture. |
| Cross-set package move could orphan diagrams referencing packages by id | Phase 2 spec lists invariants: same-tenant only, diagram.set_id must match new package.set_id post-move, atomic transaction. Failing tests written first. |
| MCP `update_diagram` with `data:` payload could corrupt large diagrams | Reuse the same JSON-schema validation `create_diagram` already runs; reject anything that fails. |
| Cascade prompt grows too long, exceeds context budget on small models | Shared cascade prompt is ~600 tokens; existing notation prompt is ~400 tokens; combined still under typical 8k budget. Audit at Phase 1 close — if over 1500 tokens, split into mandatory-rules + optional-tips sections. |
| GUI Export menu UX conflicts with existing per-diagram-type controls | Phase 5 spec includes UX review checkpoint; menu replaces, not augments, the existing controls. |
| Parity check script over-fires on read-only tools | Script restricts parity rule to write tools (`create_*`, `update_*`, `move_*`, `delete_*` if/when added). |

## Open questions parked for individual SPECs

- **SPEC-178:** does `PUT /diagrams/{id}` today accept `package_id` /
  `set_id` changes, or do we need a dedicated `PATCH /diagrams/{id}/parent`?
  Investigate at SPEC-178-A drafting time. (Backend exploration found no
  evidence either way.)
- **SPEC-179:** does Anthropic's docx skill produce OOXML directly or via
  python-docx? Read both skills at SPEC-179-A drafting time and pick the
  cleaner integration.
- **SPEC-180:** is there an existing `iris_client` SDK shared between MCP and
  the AI runtime, or does each surface re-implement against `httpx`?
  Investigate; if the answer is "re-implements", factor the shared client as
  part of Phase 4.
- **SPEC-181:** what does a markdown-content diagram look like in the current
  diagram-view component? Spec investigation: read
  `frontend/src/routes/.../+page.svelte` and identify whether markdown
  diagrams (`notation=markdown`) render in a different component from visual
  diagrams; the Export menu visibility logic depends on that.
