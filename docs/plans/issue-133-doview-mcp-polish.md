# Plan: DoView MCP flow polish + MCP/CLI parity (issue #133)

> Rewritten 2026-05-16 after a review of v1. The four clarifying questions
> raised by the review were resolved by the user in chat (one MCP-wide
> AskUserQuestion rule; citations get their own shared base prompt; renderer
> decoupled from move tools; rendered artefacts stored in Iris and returned
> as URLs).

## Context

Issue #133 captures the first end-to-end UAT of the v6.0.15 DoView creation
cascade (Outcomes Theory Book → Macroeconomics of Banana Monoculture). The
flow worked, but the user surfaced two classes of feedback:

- **Class A — DoView creation cascade UX (turns 1–13 of the transcript at
  `https://github.com/user-attachments/files/27839763/banana-monoculture-doview-conversation.md`)**.
  Inconsistent use of the MCP client's question tool, an info-source step
  that collapses to a binary instead of paste/upload, no default DoView name,
  Sources subpage with no URLs, no skip-detail branching at Stage 1→2, no
  save-destination chooser, no `move_*` recovery if the cascade saved in the
  wrong place.
- **Class B — Surface parity & metadata editability**. Iris MCP has no
  `update_*` or `move_*` tools; CLI is read-only + `ask` + `export`; GUI
  export options are limited (jsPDF rasterisation only). CLI ↔ API ↔ MCP
  parity has drifted.

The orient/instructions infrastructure shipped in v5.18.0 (ADR-163) and
extended in ADR-167 is the right surface for cross-cutting conversational
rules. The DRY discipline of protocols §13 means the docx/pdf renderer used
by the GUI must be reachable from the MCP artefact-download path so model
and human take the same code path.

## Updates relative to v1 of the plan

| Item | v1 | v2 | Reason |
|------|----|----|--------|
| Migration numbers | `m054_cascade_ux_polish.py` / `m058…sql` | recomputed at drafting time — Python is at `m057_…`, Supabase at `m061_…`, so next free pair is `m058 + m062`. Re-check at each phase open. | v1 numbers collide with the existing `m054_oauth_tables` / `m058_oauth_tables`. |
| AskUserQuestion rule | Cascade-prompt only | Promoted to **MCP-wide convention** (refresh `m053_mcp_server_instructions_seed` + `m057_…sql`). Cascade prompts inherit; only add nuance (default-name, paste/upload). | User answer Q1: one rule, one place to drift. Reframes ADR-177 to supersede the user-question half of ADR-167. |
| Sources-URL citation rule | Only patched into `_OUTCOMES_MAP_PROMPT` | **New shared base prompt `creation-cascade-citations-v1`** at `layer=base`, opt-in by any notation. `_OUTCOMES_MAP_PROMPT` references it instead of restating. | User answer Q2: dedicated reusable prompt; other notations with citation needs (BPMN regulatory refs, process_flow source links) inherit for free. |
| Phase ordering | Phase 2 = move_* tools, Phase 3 = renderer (3 depended on 2) | **Renderer becomes Phase 2** (v6.2.0). **Move/update tools become Phase 3** (v6.3.0). Decoupled. | User answer Q3: destination chooser at Q11 uses `create_*` (already shipped) — `move_*` is only the recovery path. Renderer + storage can ship sooner. |
| Large-payload return | Inline base64 from MCP | **All rendered artefacts (md/docx/pdf) stored in Iris** via an extension of the existing `backend/app/images/` store (generalised to "artefacts") and returned to the model + user as a download URL. Default for every render, not just large ones. | User answer Q4: reuse image store, return a link. Consistent with the `web_url` decoration of ADR-175. |
| Element re-parenting | v1 decision #17 rejected cross-diagram element moves | Removed as a separate decision. Elements travel with their diagram via `move_diagram`. Not a feature, not a parity gap. | User clarification: never intended; the "move" requirement is at diagram / package / set level only. |
| CLI `ask` | Implied removable for parity | **Kept**. Documented in ADR-180 / ADR-182 as a deliberate asymmetry — MCP clients bring their own LLM, CLI users don't. | User answer Q3 (CLI). |
| Phase 1 acceptance | Banana flow only | Adds a **second UAT against a BPMN notation** to prove the shared cascade isn't accidentally Outcomes-Theory-shaped. | User answer Q4 (UAT). |
| DRY enforcement | Mentioned, not measurable | **Phase 6 parity script** asserts no md→docx or md→pdf implementation exists outside `backend/app/export/renderers/`. | Closes the protocols §13 loop. |
| Token-budget risk | "Under 8k budget" framing | Reframed as **prompt-clarity audit at Phase 1 close** (the UAT clients have huge context — clarity, not budget, is the real risk). | Review item. |
| WeasyPrint Render risk | Not mentioned | Added: verify Render image build includes Pango / Cairo / GDK-PixBuf before merging Phase 2; verify by direct curl per `feedback_render_deploy_verification` memory, **not** the deployments API. | Review item. |
| Parity matrix scope | Implied writes-only | Made explicit: **CI gate enforces write-tool parity**; matrix tracks read parity manually for visibility. | Review item. |

## Final decisions

| # | Decision |
|---|---|
| 1 | Group the work into **six phases**, each with its own ADR + SPEC + branch + PR, sequenced so each phase is independently shippable. Phases ship as separate minor releases v6.1.0–v6.6.0 per `feedback_release_workflow` memory. |
| 2 | **AskUserQuestion is an MCP-wide convention.** Encoded in the MCP server-instructions seed (`m053_mcp_server_instructions_seed.py` refresh + `m057_mcp_server_instructions_seed.sql` mirror). Cascades inherit; cascade prompts only add nuance (default-name suggestion pattern, paste/upload affordance). ADR-177 reframes the rule and supersedes the user-question half of ADR-167. |
| 3 | **Paste/upload at info-source step.** Implemented as a three-option AskUserQuestion (`General knowledge` / `I will paste my own content` / `I will attach a file`) plus a free-text follow-up. File attachment delegates to the MCP client's native mechanism. Cascade waits for content + echoes a summary for confirmation before continuing. Encoded in `creation-cascade-shared-v1`. |
| 4 | **Default DoView name.** Cascade Q rewrites to "I'd suggest naming it `<subject> DoView` — keep this, or pick a different name?" with `Keep "<subject> DoView"` as option 1 and `Use a different name` as option 2. Encoded as a default-name template in `creation-cascade-shared-v1` so any notation inherits. |
| 5 | **Sources URLs as a shared base prompt.** New row `creation-cascade-citations-v1` at `layer=base`, `notation=NULL`, `diagram_type=NULL`, `display_order=2`, `purpose='creation_format'`. Body: every source_reference must use the format `Author/Org · Title · YYYY · <raw https URL>` (mirrors m051's `(markdown, doview_analysis)` rule). `_OUTCOMES_MAP_PROMPT` removes its inline Sources rule and points at this prompt. Other notations opt in by referencing the same prompt id. |
| 6 | **Skip-detail branching at Stage 1→2.** Replace the implicit Stage 2 jump with an explicit three-option AskUserQuestion: `Skip detail review and generate (recommended)` / `Review detailed box content first` / `Refine subpage structure first`. Default skip. Encoded in `creation-cascade-shared-v1`. |
| 7 | **Generic destination chooser.** Fires after Stage 2 (or after Stage 1 if user picked skip-detail). Save-where: `Chat with downloadable artefacts` / `Iris (source of truth)` / `Both`. If Iris: `New set under the parent collection (default)` / `Browse root collections` / `Current set` / `Somewhere else (free text)`. Encoded once in `creation-cascade-destination-v1` at `layer=base`, `display_order=3`. Generic across notations. |
| 8 | **Renderer + artefact storage.** Adopt the Anthropic skills' approach (Python: `python-docx` + `markdown-it-py` for docx; `weasyprint` + a markdown CSS template for pdf) and build a single renderer module in `backend/app/export/renderers/`. **All rendered artefacts persist in Iris** via an extension of `backend/app/images/` generalised to a generic `artefacts` store (mime-typed binary + retrieval endpoint + auth). MCP `export_diagram` / `render_markdown` return `{artefact_id, web_url, mime_type, filename}` — never inline base64. The same renderer endpoints back the GUI Export menu and the CLI `iris export`. |
| 9 | **MCP update_* tools** for every entity type wrap the existing backend PUT endpoints (`collections`, `sets`, `packages`, `diagrams`, `elements`). MCP **move_*** tools target diagram / package / set re-parenting only — elements travel with their diagram. Backend gaps to close: `PATCH /diagrams/{id}/parent` (verify whether existing `PUT /diagrams/{id}` accepts `package_id` / `set_id` changes at SPEC-178 drafting time); `PUT /packages/{id}/parent` extended for cross-set moves (today it cycle-checks within one set). |
| 10 | **CLI parity.** Extend `cli/src/iris_cli/main.py` with `create`, `update`, `move` subcommand groups for every entity (delete deferred — see #16). Share an `iris_client` Python SDK between CLI, MCP, and AI runtime — factor out at SPEC-180 drafting time if today each surface re-implements against `httpx`. **`iris ask` stays** — documented as a deliberate asymmetry in ADR-180 / ADR-182. |
| 11 | **GUI export options.** Add a `DiagramExportMenu.svelte` to every diagram view. For markdown-content diagrams: Markdown / Docx / PDF (server-rendered via Phase 2 endpoints). For visual diagrams: SVG / PNG (client-side, retained) + Markdown / Docx / PDF (server-rendered if a markdown summary exists). Removes the jsPDF rasterised-pdf path in `frontend/src/lib/utils/export.ts`. |
| 12 | **Cascade prompt composition.** The `creation_format` ladder fetched by `get_response_prompt(notation, diagram_type, purpose='creation_format')` composes BASE + NOTATION + DIAGRAM_TYPE in `display_order` ascending. New base-layer prompts in order: `creation-cascade-shared-v1` (1), `creation-cascade-citations-v1` (2), `creation-cascade-destination-v1` (3). |
| 13 | **TDD ordering** per protocols §3. Each phase's failing tests written first against the SPEC acceptance criteria, then implementation. For prompt seeds: assert composed prompt contains the new sections AND that a non-DoView notation also receives the shared rules. For renderer endpoints: fixture-md → fixture-docx round-trip via `python-docx` reader; PDF byte-header + page count. For MCP `update_/move_`: create → mutate → assert via the read tool. For storage: upload → URL → re-download → byte equality. |
| 14 | **Versioning** per phase: v6.1.0 (cascade prompt polish + MCP-wide AskUserQuestion rule), v6.2.0 (renderer + artefact store + destination chooser actuation), v6.3.0 (MCP update + move tools), v6.4.0 (CLI parity), v6.5.0 (GUI export options), v6.6.0 (parity ADR + reconciliation). GitHub release published on each tag per `feedback_release_workflow`. |
| 15 | **README + CHANGELOG** updated in the same branch as the change per protocols §5 and §12. Surfaces: `mcp/README.md` (phases 1, 3, 4), `cli/README.md` (phase 4), `frontend/README.md` (phase 5 if present), root `README.md` for the parity rule (phase 6), `CHANGELOG.md` every phase. |
| 16 | **No `delete_*` MCP tools yet.** Out of scope; tracked in Phase 6 parity matrix as `deferred — needs separate ADR (audit trail, undo)`. |
| 17 | **No element re-parenting.** Not a feature; not in the parity matrix. Elements are owned by their parent diagram and move with it. Documented in ADR-178 body as a design invariant. |

## ADRs to create

| ADR | Title | Phase | Supersedes / extends |
|-----|-------|-------|----------------------|
| ADR-176 | Generic creation-cascade shared base prompts (shared / citations / destination) | 1 | extends ADR-162 |
| ADR-177 | AskUserQuestion as MCP-wide user-question convention | 1 | supersedes the user-question half of ADR-167 |
| ADR-178 | MCP update_* and move_* tool surface | 3 | extends ADR-161 |
| ADR-179 | Server-side md→docx/pdf renderer + Iris artefact store | 2 | new capability; extends `backend/app/images/` |
| ADR-180 | CLI write-tool parity with MCP (plus `ask` asymmetry) | 4 | new capability |
| ADR-181 | Unified diagram export options in the GUI | 5 | supersedes `frontend/src/lib/utils/export.ts` jsPDF path |
| ADR-182 | CLI / API / MCP surface parity discipline (meta-ADR) | 6 | cross-references 178 / 179 / 180 / 181 |

## SPECs to create

`docs/adrs/specs/SPEC-176-A-Cascade-Shared-Base-Prompts.md`,
`SPEC-177-A-AskUserQuestion-MCP-Convention.md`,
`SPEC-178-A-MCP-Update-Move-Tools.md`,
`SPEC-179-A-Renderer-And-Artefact-Store.md`,
`SPEC-180-A-CLI-Write-Parity.md`,
`SPEC-181-A-Unified-Diagram-Export-GUI.md`,
`SPEC-182-A-Surface-Parity-Discipline.md`.

## Phases & files

> Migration filenames below assume next free pair `m058.py + m062.sql` at
> Phase 1 open. **Re-verify at each phase open** with
> `ls backend/app/migrations/ | tail -5 && ls backend/app/migrations/supabase/ | tail -5`
> and bump accordingly. The plan calls out *content*, not the literal id.

### Phase 1 — Creation-cascade UX polish (v6.1.0)

**Branch:** `feature/issue-133-cascade-polish`

**Scope:** Class A items #1–#5 plus the destination-chooser scaffolding for
#6 (prompt-only — actuation lands in Phase 2). Plus the MCP-wide
AskUserQuestion rule promotion.

**Create:**

- `docs/adrs/ADR-176-Cascade-Shared-Base-Prompts.md`
- `docs/adrs/ADR-177-AskUserQuestion-MCP-Convention.md`
- `docs/adrs/specs/SPEC-176-A-Cascade-Shared-Base-Prompts.md`
- `docs/adrs/specs/SPEC-177-A-AskUserQuestion-MCP-Convention.md`
- `backend/app/migrations/m{next}_cascade_ux_polish.py` —
  - INSERT `creation-cascade-shared-v1` (`layer=base`, `notation=NULL`,
    `diagram_type=NULL`, `display_order=1`, `purpose='creation_format'`) —
    body: paste/upload affordance (decision #3), default-name template
    (decision #4), skip-detail branching template (decision #6).
  - INSERT `creation-cascade-citations-v1` (`layer=base`,
    `display_order=2`) — body: raw-URL citation rule mirroring m051.
  - INSERT `creation-cascade-destination-v1` (`layer=base`,
    `display_order=3`) — body: destination-chooser template (decision #7,
    prompt-side only — actuation no-ops in Phase 1 with a fallback message
    "I can describe what should be created but cannot move it yet — Phase 2
    ships v6.2.0").
  - UPDATE `creation-doview-notation-v1` — defer to the shared cascade,
    remove duplicated content, retain only DoView-specific guidance.
  - UPDATE `creation-outcomes-map-v1` — remove its inline Sources rule and
    reference `creation-cascade-citations-v1` instead.
- `backend/app/migrations/m{next}_mcp_user_question_rule.py` —
  - UPDATE `mcp-server-instructions-v1` seed (the body refreshed by m053):
    add a top-level "ASKING QUESTIONS" section stating that any user-facing
    question MUST use the MCP client's question tool (or numbered list
    fallback). Section sits alongside ORIENT-FIRST PROTOCOL and DISCOVERY
    TOOLS. Body documented in `docs/prompts/mcp-server-instructions.md`.
- `backend/app/migrations/supabase/m{next}_cascade_ux_polish.sql` and
  `m{next}_mcp_user_question_rule.sql` — Supabase mirrors.
- `backend/tests/migrations/test_m{next}_cascade_ux_polish.py` — TDD red:
  - Composed `creation_format` for `(doview, outcomes_map)` contains
    AskUserQuestion convention reference, paste-content rule, skip-detail
    template, destination template, default-name template, citation rule.
  - Composed `creation_format` for `(bpmn, *)` and `(process_flow, *)` ALSO
    contains the shared base-prompt rules — proving generality.
- `backend/tests/migrations/test_m{next}_mcp_user_question_rule.py` —
  assertion that the MCP server-instructions seed contains the new
  "ASKING QUESTIONS" section.
- `docs/prompts/creation-cascade-shared.md`,
  `docs/prompts/creation-cascade-citations.md`,
  `docs/prompts/creation-cascade-destination.md` — admin-recovery docs
  mirroring the `mcp-server-instructions.md` pattern.

**Modify:**

- `docs/prompts/mcp-server-instructions.md` — append "ASKING QUESTIONS".
- `mcp/README.md` — document the cascade behaviour + destination chooser.
- `CHANGELOG.md` — `[6.1.0]` Added / Changed.

**Acceptance gates:**

- All Phase 1 tests green.
- `get_response_prompt(notation='doview', diagram_type='outcomes_map',
  purpose='creation_format')` body contains every new section.
- `get_response_prompt(notation='bpmn', diagram_type=<any>, purpose='creation_format')`
  body contains the same shared sections (cascade-generality proof).
- **Manual UAT 1 (regression):** replay banana-monoculture flow; confirm
  Q3 proposes default name, Q4 offers paste/upload, Q9 offers skip-detail,
  Q11 offers destination chooser (with Phase-1 fallback message), every
  question uses AskUserQuestion.
- **Manual UAT 2 (generality):** create a fresh BPMN diagram via the
  cascade and confirm the same shared questions fire. Without this, we
  ship a "generic" prompt that only happens to work on DoView.
- Existing `test_outcomes_map_layout` (verify presence) still green.

### Phase 2 — Renderer + artefact store + destination actuation (v6.2.0)

**Branch:** `feature/issue-133-renderer`

**Scope:** Class A #6 (backend half). Phase 1's destination chooser stops
returning the fallback and starts producing real artefacts + saving to
Iris locations chosen by the user.

**Create:**

- `docs/adrs/ADR-179-Renderer-And-Artefact-Store.md`
- `docs/adrs/specs/SPEC-179-A-Renderer-And-Artefact-Store.md`
- `backend/app/export/renderers/__init__.py`
- `backend/app/export/renderers/markdown.py` — passthrough + stable
  normalisation.
- `backend/app/export/renderers/docx.py` — md → docx via
  `python-docx` + `markdown-it-py`. Recipe modelled on
  `github.com/anthropics/skills/tree/main/skills/docx`.
- `backend/app/export/renderers/pdf.py` — md → pdf via `weasyprint` +
  Iris-branded CSS at `backend/app/export/renderers/styles/iris.css`.
  Recipe modelled on `github.com/anthropics/skills/tree/main/skills/pdf`.
- Generalisation of `backend/app/images/` into a generic artefact store.
  Two implementation paths to pick at SPEC-179 drafting time:
  (a) extend the existing `images` module with a `category` enum
  (`image | rendered_doc | …`) and broaden the mime allowlist;
  (b) factor a shared `backend/app/artefacts/` module with `images` and
  `renders` as thin facades. Decision recorded in the SPEC; default leans
  (a) for minimum churn.
- New backend endpoints in `backend/app/export/router.py`:
  - `POST /api/export/diagram/{id}` body `{format: md|docx|pdf}` —
    renders, stores artefact, returns `{artefact_id, web_url,
    mime_type, filename}`.
  - `POST /api/export/markdown` body `{markdown, title, format}` — same
    return shape; for ad-hoc rendering of cascade-generated content not
    yet saved to a diagram.
  - `GET /api/artefacts/{artefact_id}` — auth-gated download. (If using
    path (b), this is the generalised image-retrieval endpoint at a new
    path; if path (a), it's `GET /api/images/{id}` with broader mimes.)
- MCP tools in `mcp/src/iris_mcp/tools.py`:
  - `export_diagram(diagram_id, format)` — returns
    `{artefact_id, web_url, mime_type, filename}`. Decorated by
    `links.with_web_url` (ADR-175).
  - `render_markdown(markdown, title, format)` — same return shape.
- UPDATE `creation-cascade-destination-v1` (via new migration
  `m{next}_destination_actuation.py` + supabase mirror) to drop the Phase
  1 fallback and instead instruct the model to call `render_markdown` /
  `export_diagram` for each selected format and to call `create_set` /
  `create_diagram` for the Iris destination chosen.

**Tests:**

- `backend/tests/export/test_md_to_docx.py` — fixture → render → parse
  with `python-docx` → assert headings/lists/code blocks/mermaid passes
  through.
- `backend/tests/export/test_md_to_pdf.py` — fixture → render → assert
  PDF byte-header + page count.
- `backend/tests/artefacts/test_store_roundtrip.py` — upload → URL →
  re-download → byte equality + auth required.
- `mcp/tests/test_export_tools.py` — MCP tool returns URL, URL resolves,
  content matches the fixture.
- `backend/tests/migrations/test_m{next}_destination_actuation.py` —
  composed cascade body no longer contains the Phase 1 fallback string.

**Modify:**

- `backend/pyproject.toml` — add `python-docx`, `markdown-it-py`,
  `weasyprint`. Per protocols §11 pin latest stable at implementation date
  and document in commit message; verify with `pip index versions`.
- `backend/app/images/{models,service,router}.py` — generalise per the
  path chosen in SPEC-179.
- `mcp/src/iris_mcp/links.py` — extend `with_web_url` to cover
  `export_*` / `render_*` returns.
- `mcp/src/iris_mcp/server_instructions.py` — append a paragraph in
  `_FALLBACK_INSTRUCTIONS` naming the new export tools.
- `CHANGELOG.md` — `[6.2.0]`.

**Acceptance gates:**

- Renderer + storage tests green.
- **Manual UAT (banana replay):** pick "Both" + md+docx+pdf → receive
  three links to Iris-stored artefacts that all download correctly. Pick
  "Current set" → bundle lands in the correct set.
- **Render deployment verification per `feedback_render_deploy_verification`:**
  curl the new endpoint against the deployed Render env to verify
  WeasyPrint system deps (Pango / Cairo / GDK-PixBuf) are present in the
  image. Do NOT trust the deployments API; verify by hitting the live
  endpoint. If the image is missing deps, update the Render Dockerfile
  before tagging the release.

### Phase 3 — MCP update_* + move_* tools (v6.3.0)

**Branch:** `feature/issue-133-mcp-update-move`

**Scope:** Class A #8 and Class B #9. Adds the recovery path for users
who chose the wrong destination in Phase 2.

**Create:**

- `docs/adrs/ADR-178-MCP-Update-Move-Tools.md`
- `docs/adrs/specs/SPEC-178-A-MCP-Update-Move-Tools.md`
- New MCP tools in `mcp/src/iris_mcp/tools.py`:
  - `update_collection(collection_id, name?, description?, thumbnail_source?, thumbnail_diagram_id?, system_prompt?, mcp_system_context?)`
    → `PUT /collections/{id}`.
  - `update_set(set_id, name?, description?, system_prompt?, mcp_system_context?)`
    → `PUT /sets/{id}` (excluding `collection_id`; moves are separate).
  - `update_package(package_id, name?, description?, metadata?, if_match?)`
    → `PUT /packages/{id}`.
  - `update_diagram(diagram_id, name?, description?, data?, metadata?)`
    → `PUT /diagrams/{id}`.
  - `update_element(element_id, name?, description?, data?, metadata?)`
    → `PUT /elements/{id}`.
  - `move_diagram(diagram_id, target_package_id?, target_set_id?)` →
    either `PATCH /diagrams/{id}/parent` (new) or existing
    `PUT /diagrams/{id}` if those fields are already mutable. Investigate
    at SPEC-178 drafting time.
  - `move_package(package_id, target_parent_package_id?, target_set_id?)` →
    existing `PUT /packages/{id}/parent`; needs cross-set support
    (see backend gap below).
  - `move_set(set_id, target_collection_id)` → `PUT /sets/{id}`
    `collection_id` change.
- Backend gap-closers (only if SPEC-178 finds them missing):
  - `PATCH /diagrams/{id}/parent` in `backend/app/diagrams/router.py`.
  - `PUT /packages/{id}/parent` extended to accept `target_set_id` for
    cross-set moves (today it cycle-checks within one set only).
- Tests:
  - `mcp/tests/test_update_tools.py` — create → update → assert via
    `get_*` + assert MCP response carries `web_url` (ADR-175).
  - `mcp/tests/test_move_tools.py` — fixture multi-collection +
    multi-set graph → `move_diagram` / `move_package` / `move_set` →
    assert via `package_hierarchy` the tree updated.
  - `backend/tests/diagrams/test_move.py` — REST test of move endpoint.
  - `backend/tests/packages/test_cross_set_move.py` — REST test of
    cross-set package move.

**Modify:**

- `mcp/src/iris_mcp/tools.py` — registration + handlers.
- `mcp/src/iris_mcp/links.py` — `with_web_url` covers `update_*` and
  `move_*`.
- `mcp/src/iris_mcp/server_instructions.py` — `_FALLBACK_INSTRUCTIONS`
  WORKFLOW GUIDANCE mentions the new tools.
- `backend/app/migrations/m{next}_mcp_server_instructions_refresh.py`
  + supabase mirror — refresh the seeded MCP instructions body so live
  servers pick up the new tool names. `docs/prompts/mcp-server-instructions.md`
  updated in lockstep.
- `backend/app/diagrams/router.py` and/or `backend/app/packages/router.py`
  per gap analysis.
- `CHANGELOG.md` — `[6.3.0]`.

**Acceptance gates:**

- All Phase 3 tests green.
- **Manual UAT:** with Phase 2's destination chooser, deliberately pick
  the wrong set; then ask the model to relocate the bundle. Verify
  `move_*` does it without re-creating content.

### Phase 4 — CLI parity (v6.4.0)

**Branch:** `feature/issue-133-cli-parity`

**Scope:** Class B #10.

**Create:**

- `docs/adrs/ADR-180-CLI-Write-Tool-Parity.md` — including the
  documented `iris ask` asymmetry (MCP clients bring their own LLM, CLI
  users don't).
- `docs/adrs/specs/SPEC-180-A-CLI-Write-Parity.md`
- CLI subcommand groups in `cli/src/iris_cli/main.py`:
  - `iris create {collection|set|package|diagram}` — mirrors MCP
    `create_*`.
  - `iris update {collection|set|package|diagram|element}` — mirrors
    MCP `update_*`.
  - `iris move {diagram|package|set}` — mirrors MCP `move_*`.
  - `iris export {diagram|markdown}` — extends the existing `export`
    group with the Phase 2 renderer.
- Shared client SDK confirmation: SPEC-180 first checks whether
  `iris_client` exists as a shared package between CLI / MCP / AI
  runtime. If yes, reuse. If no, factor a `iris_client.write` module
  this phase (DRY per protocols §13). The existence question is parked
  for SPEC-180 drafting.

**Tests:**

- `cli/tests/test_create_commands.py`
- `cli/tests/test_update_commands.py`
- `cli/tests/test_move_commands.py`
- `cli/tests/test_export_commands.py` — fetch, write to tempfile,
  validate the bytes.

**Modify:**

- `cli/README.md` — document new subcommands + note that `ask` stays.
- `CHANGELOG.md` — `[6.4.0]`.

**Acceptance gates:**

- CLI tests green.
- `iris create set --name X --collection-id Y` succeeds; `iris move
  diagram <id> --to-package <pkg>` succeeds; `iris export diagram <id>
  --format docx --output ./out.docx` writes a valid docx.
- `iris ask` still works (regression check on the deliberate asymmetry).

### Phase 5 — GUI export options (v6.5.0)

**Branch:** `feature/issue-133-gui-export`

**Scope:** Class A #6 GUI half / Class B #11.

**Create:**

- `docs/adrs/ADR-181-Unified-Diagram-Export-GUI.md`
- `docs/adrs/specs/SPEC-181-A-Unified-Diagram-Export-GUI.md`
- `frontend/src/lib/components/DiagramExportMenu.svelte` — dropdown
  with Markdown / Docx / PDF (server-rendered via Phase 2 endpoint) and
  SVG / PNG (client-rasterised, retained). Markdown / Docx / PDF
  visibility depends on whether the diagram has markdown content
  (markdown-content diagrams: always shown; visual diagrams: only if
  a markdown summary exists).
- `frontend/tests/e2e/diagram-export.spec.ts` — open a markdown
  diagram → Export → Docx → intercept the download → assert it's a
  valid docx (real bytes via the server, not a stub).

**Modify:**

- `frontend/src/lib/utils/export.ts` — keep the client-side SVG/PNG
  path. Replace the jsPDF rasterised-pdf path (line 8, line 193) by
  calling the Phase 2 backend endpoint. The new GUI path uses real PDF
  not a screenshot of the SVG.
- Each diagram-view `+page.svelte` route — import the new menu.
- `CHANGELOG.md` — `[6.5.0]`.

**Acceptance gates:**

- E2E export test green.
- **Manual UAT:** any markdown diagram → Export → Docx → opens in Word.
  Same for PDF. SVG / PNG still work via the client path.
- Byte-equality check: GUI-downloaded docx == CLI-downloaded docx ==
  MCP-fetched-via-URL docx for the same source diagram. (Quick way to
  prove DRY — same renderer code path.)

### Phase 6 — Parity ADR + reconciliation (v6.6.0)

**Branch:** `docs/issue-133-parity-discipline`

**Scope:** Class B #10 follow-up. Cement the parity rule so future MCP /
CLI / API work doesn't drift again.

**Create:**

- `docs/adrs/ADR-182-Surface-Parity-Discipline.md` — meta-ADR. Every
  backend write endpoint MUST have a matching MCP tool AND a matching
  CLI subcommand. Every MCP write tool MUST have a corresponding CLI
  subcommand and a backed API endpoint. Documented asymmetries (CLI
  `ask`, no `delete_*` MCP tools, no element re-parenting) recorded
  with rationale. Includes a parity matrix as living documentation.
- `docs/adrs/specs/SPEC-182-A-Surface-Parity-Discipline.md` — codifies
  the matrix, defines the audit script, defines the CI gate.
- `scripts/check_surface_parity.py` — scans
  `backend/app/*/router.py`, `mcp/src/iris_mcp/tools.py`,
  `cli/src/iris_cli/main.py`. Reports diffs. CI gate (hard-fail) covers
  **write tools only** (`create_*`, `update_*`, `move_*`); read parity
  is reported but not gated. Also asserts no md→docx / md→pdf
  implementation exists outside `backend/app/export/renderers/` (the
  DRY check that closes the protocols §13 loop).

**Modify:**

- `docs/protocols.md` — add §14 "Surface Parity" with one-line
  reference to ADR-182.
- `CLAUDE.md` — append the same reference.
- `.github/workflows/<ci>.yml` — wire the parity check.
- `CHANGELOG.md` — `[6.6.0]`.

**Acceptance gates:**

- `scripts/check_surface_parity.py` returns clean against the current
  tree.
- CI run on a deliberately-broken PR (e.g. add an MCP write tool with
  no CLI counterpart) fails as expected. Revert before merge.

## Implementation order

1. **Phase 1** (v6.1.0) — prompt-only; lowest risk; unblocks every later
   phase by establishing the shared cascade base prompts and the MCP-wide
   AskUserQuestion rule.
2. **Phase 2** (v6.2.0) — renderer + artefact store + destination actuation.
   Independent of Phase 3. Releases the user-visible "download my DoView as
   PDF" capability.
3. **Phase 3** (v6.3.0) — MCP update + move tools. Independent of Phase 2;
   could ship in parallel branches. Provides the post-hoc recovery path.
4. **Phase 4** (v6.4.0) — depends on Phases 2 + 3 (renderer for export,
   update/move patterns established).
5. **Phase 5** (v6.5.0) — depends on Phase 2 renderer endpoint.
6. **Phase 6** (v6.6.0) — runs last; ratifies the parity established by
   Phases 2 – 5.

## Verification (cross-phase)

After each phase tag, replay both UATs:

- **Banana UAT** (DoView regression).
- **BPMN UAT** (cascade-generality proof, introduced Phase 1).

Expected state at each phase:

- **Post-Phase 1:** every cascade question via AskUserQuestion; six new
  question types appear; destination chooser asks but cannot yet
  actuate (returns Phase-1 fallback).
- **Post-Phase 2:** destination chooser actually creates artefacts in
  Iris store and saves bundles to the chosen location. Render endpoint
  works on Render — verified by direct curl, not deployments API.
- **Post-Phase 3:** move_* successfully relocates a misplaced bundle.
- **Post-Phase 4:** every operation reproducible from `iris` CLI;
  `iris ask` still works (asymmetry intact).
- **Post-Phase 5:** GUI Export menu produces byte-identical docx/pdf to
  CLI and MCP (DRY proof).
- **Post-Phase 6:** parity check CI gate active and clean.

Each phase ships its own GitHub release per `feedback_release_workflow`
(tag pushed, CHANGELOG section moved out of `[Unreleased]`, release
notes reference the relevant ADRs).

## Risks & mitigations

| Risk | Mitigation |
|------|------------|
| Migration ids drift between Phase 1 drafting and Phase 1 merge | Each phase open re-checks `ls backend/app/migrations \| tail -5` and bumps. The plan calls out *content*, never the literal id. |
| `weasyprint` system deps missing from Render base image | Phase 2 acceptance gate explicitly curls the deployed endpoint per `feedback_render_deploy_verification`. If 500s, update Dockerfile (Pango / Cairo / GDK-PixBuf) before tagging. Also vendor as optional PyPI extra `iris[pdf]` and degrade with 503 + hint if missing. |
| `python-docx` inconsistent layout across editions | Use Anthropic skill recipe as the starting point; add golden-file tests against a stable fixture. |
| Cross-set package move orphans diagrams referencing packages by id | SPEC-178 lists invariants: same-tenant only; diagram.set_id must match new package.set_id post-move; atomic transaction. Failing tests written first. |
| MCP `update_diagram` `data:` payload corrupts large diagrams | Reuse `create_diagram` JSON-schema validation; reject anything that fails. |
| Cascade prompt clarity (not budget) degrades as shared layer grows | Audit at Phase 1 close — if the model is dropping or merging sections during UAT, split mandatory-rules from optional-tips. (Budget itself is a non-issue on UAT clients.) |
| GUI Export menu UX conflicts with existing per-diagram-type controls | Phase 5 spec includes a UX review checkpoint; menu *replaces* the existing controls, doesn't augment. |
| Parity check script over-fires on read-only tools | Script restricts the CI gate to write tools; read parity is reported only. |
| Artefact store grows unbounded | Phase 2 SPEC includes a retention policy: default 90 days, configurable per env. Tracked by a separate maintenance task; not blocking #133 acceptance. |
| Sensitive content stored in artefacts (PDFs of pasted user material) | Artefact endpoint auth-gated by the same JWT/OAuth path as the rest of the API. Phase 2 test asserts unauthenticated GET returns 401. |

## Open questions parked for individual SPECs

- **SPEC-178:** does `PUT /diagrams/{id}` today accept `package_id` /
  `set_id` changes, or do we need a dedicated `PATCH
  /diagrams/{id}/parent`? Investigate at drafting time.
- **SPEC-179:** path (a) extend `images` module vs path (b) factor a
  shared `artefacts` module. Decision recorded in the spec, default
  leans (a) for minimum churn.
- **SPEC-179:** Anthropic docx skill — produces OOXML directly or via
  `python-docx`? Read both skills at drafting time and pick the cleaner
  integration.
- **SPEC-180:** is there an existing `iris_client` SDK shared between
  MCP and the AI runtime, or does each surface re-implement against
  `httpx`? If "re-implements", factor the shared client as part of
  Phase 4.
- **SPEC-181:** how does a markdown-content diagram render in the
  current diagram-view component, and where does the visibility-logic
  branch live? Read `frontend/src/routes/.../+page.svelte` at drafting
  time.
- **SPEC-182:** which CI surface runs the parity check (GitHub Actions
  job already exists vs new job)? Confirm at drafting.

## Protocols compliance check

| Protocol | How this plan complies |
|----------|------------------------|
| §1 ADRs | 7 new ADRs (176–182), each with rejected-alternatives section |
| §2 Specs | 7 new specs, one per ADR, `SPEC-{N}-A-{Title}` naming |
| §3 TDD | Every phase lists red-first tests before implementation |
| §4 Feature branches | Each phase has its own `feature/issue-133-{slug}` branch |
| §5 Changelog | Every phase updates `CHANGELOG.md` |
| §6 Releases | v6.1.0–v6.6.0 tagged per phase + GH release per `feedback_release_workflow` |
| §7 `{@html}` | Phase 5 GUI changes touch no `{@html}` (server-rendered artefacts only) |
| §8 Context7 | SPEC drafting for renderer / GUI consults Context7 for `weasyprint`, `python-docx`, Svelte 5 patterns |
| §9 Production-ready | No mocks/stubs; Phase 1's destination chooser ships a real fallback message, not a stub |
| §10 Agent teams | Phase 1 + Phase 2 can be parallel branches (independent) once Phase 1's prompt seeds land |
| §11 Latest stable deps | Phase 2 verifies `weasyprint` / `python-docx` / `markdown-it-py` against PyPI at install time, version logged in commit |
| §12 README | Every phase updates the relevant surface README in the same branch |
| §13 DRY | Renderer is the single code path; Phase 6 parity script asserts it |
