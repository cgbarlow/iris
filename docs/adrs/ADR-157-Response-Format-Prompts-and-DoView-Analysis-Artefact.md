# ADR-157: Response-format prompts (layered, admin-editable) and the `doview_analysis` artefact

Status: Accepted (2026-05-12)
Extends: [ADR-094-B](ADR-094-B-AI-Creation-Service.md), [ADR-132](ADR-132-Layered-Creation-Prompts.md)
Amends: [ADR-156](ADR-156-MCP-System-Context-Data-Passthrough.md) (in part — see Decision below)

## Context

ADR-094-B and ADR-132 gave Iris a layered, admin-editable system for **diagram creation** prompts (`ai_creation_prompts` table; `build_creation_system_prompt` composer; Admin Settings / AI page). When a user creates a DoView outcomes map in Iris, those layered prompts steer the LLM through a structured interview and produce JSON the backend materialises into canvas diagrams.

What was missing: the symmetric mechanism for **response formatting** — a layered, admin-editable system that governs the *shape* of formal text+diagram analyses produced both by Iris's server-side AI (Ask Iris discuss / creation modes; `mcp__iris__ask`) and by MCP-side client models (Claude Desktop / Claude Code in conversation).

The user-facing trigger was the DoView Book scope on UAT. The author wants natural-conversation UX in Claude Desktop where asking "what does outcomes theory say about X?" produces a strict three-section formal analysis (Summary + Full + Diagrams with embedded mermaid) that is copy-pasteable into emails / reports. That structure is documented in `docs/prompts/doview-book-prompt-c-iris.md` ("Prompt C") and contains rules — required opening sentence, raw URLs only, formal style, source restriction to handbook tools — that need to live somewhere admin-editable.

ADR-156 (v5.11.0) gave us `mcp_system_context` as a per-scope passthrough field. That is the right shape for *scope-specific* context but the wrong home for response-format rules, which are **universal to a notation/diagram_type pair**: any conversation about DoView content uses the same shape regardless of which scope hosts it. Centralised storage in the existing layered-prompts mechanism is the architecturally honest home.

## Decision

Three changes, all in v5.12.0.

### 1. Add a `purpose` discriminator to the existing layered-prompts mechanism

Extend `ai_creation_prompts` with a `purpose TEXT NOT NULL DEFAULT 'creation_format'` column. Values:

- `creation_format` — used when CREATING a diagram (existing v5.8.x behaviour; backfilled to this for all pre-v5.12.0 rows).
- `response_format` — used when RESPONDING to a question, both server-side in Iris AI and client-side via MCP (new in v5.12.0).

The composer was split into a generic `_build_layered_prompt(purpose, notation, diagram_type)` inner function, with `build_creation_system_prompt` and the new `build_response_system_prompt` as thin wrappers — same cascade logic (override → base → notation → diagram_type), filtered by `purpose`. DRY (protocol §13).

The existing layer enum (`base`, `notation`, `diagram_type`, `override`) is unchanged and applies under both purposes.

### 2. Register `(notation=markdown, diagram_type=doview_analysis)` as a first-class artefact type

A `doview_analysis` is "a formal handbook-grounded outcomes-theory analysis (markdown text with embedded mermaid diagrams from referenced handbook tool pages)". Sibling to `(notation=doview, diagram_type=outcomes_map)`: same governance pattern, different output medium (text instead of visual).

This registration enables both:
- **Live conversational use**: client model fetches `response_format` for `(markdown, doview_analysis)` and applies it.
- **Persistence**: users (or MCP clients, via the new save tool) can write a generated analysis back as a regular Iris diagram of this type. Symmetric to how an outcomes map is saved.

### 3. Seed Prompt C content as three layered response_format prompt rows

- `response-format-base-v1` — universal output-structure rules (any notation).
- `response-format-doview-notation-v1` — outcomes-theory framing, source restriction, tool URL convention, handbook reference. Keyed under `notation=markdown` because the artefact is markdown text; the DoView subject matter is encoded in the body.
- `response-format-doview-analysis-v1` — three-section structure (opening sentence, Summary, Full, Diagrams), compliance check, per-Prompt C.

### MCP surface

- **`list_response_format_types`** (anonymous) — returns available `(notation, diagram_type, label, description)` pairs.
- **`get_response_prompt`** (anonymous) — returns the composed cascade body for a given pair.
- **`save_doview_analysis`** (authenticated — wraps `POST /api/diagrams`) — persists a generated analysis as a `doview_analysis` diagram. Reuses existing IRIS_TOKEN-on-server auth model; no new auth surface.

### Iris AI surface

`build_response_system_prompt(db, notation, diagram_type)` is the server-side composer; `GET /api/ai/response-prompts/composed?notation=&diagram_type=` is the HTTP surface for client-side fetch. Both consume the same rows from the same table.

Wiring of `build_response_system_prompt` into Iris's `Ask Iris` request path is deferred to a follow-up (see "Out of scope" below) — the mechanism exists; explicit invocation by client model is the v5.12.0 path.

## Amendment to ADR-156

ADR-156's `mcp_system_context` field stays: it is the right home for **per-scope** context that the model sees when browsing the scope (e.g. "this set is about NZISM; cite the control number"). It is **no longer** intended as the home for response-format rules, because those rules are universal across scopes that share a notation+diagram_type. The DoView Book Set's `mcp_system_context` becomes a short pointer to the new mechanism (manual edit on UAT, not code).

## Why split via a `purpose` column rather than a separate table

- **DRY (§13)**: the composer cascade, the admin CRUD endpoints, the seed mechanism, and the layer semantics are identical for creation_format and response_format prompts. One table + a discriminator keeps a single source of truth for the cascade logic.
- **Smaller blast radius**: backfill on a single column versus dual-table maintenance, two sets of indexes, and parallel admin UI plumbing.
- **No semantic conflict**: a row never legitimately participates in both creation and response simultaneously — it's authored for one purpose.

## Why register `doview_analysis` as a creatable artefact (not just a response shape)

- **Symmetry** with `outcomes_map`: an outcomes map is a stored visual artefact governed by a creation_format prompt; a doview_analysis is a stored text artefact governed by both a `response_format` prompt (for live composition) and — if and when creation_format rows are seeded — a creation_format prompt (for the in-Iris "Create new doview_analysis" UI workflow).
- **Persistence path**: the MCP `save_doview_analysis` tool needs a valid `(notation, diagram_type)` to write under. The diagram_type registration is not optional — without it the writes would fail.
- **First-class type**: avoids fragmenting analyses into generic `markdown / text` documents; reporting and filtering at the Set level naturally pick up "all DoView analyses".

## Why surface response prompts via MCP `tools` rather than the `prompts` channel

- ADR-152's `prompts` channel is user-controlled by spec — Claude Desktop in particular does not yet expose MCP prompts as natural conversation triggers. Surfacing through `tools` lets the client model auto-discover and fetch when relevant.
- The `tools` channel is the same one used for `list_response_format_types` (auto-discovery) and `save_doview_analysis` (write back). Coherent surface for the whole flow.

## Why a save tool, not file-save

- An MCP server cannot write to the client's local filesystem. Local persistence is the client's concern (manual copy, separate filesystem MCP, or the client's chat-export UI).
- "Saving to Iris" is a meaningful service-level action: persists the artefact alongside other DoView content in the set so other users can browse it later. That is the operation Iris is positioned to provide.

## Consequences

- One new SQLite migration `m051_response_format_prompts.py` and Supabase mirror `m055_response_format_prompts.sql`. Both idempotent. m051's registry inserts (markdown notation, doview_analysis diagram_type) skip gracefully when those tables aren't present (test isolation).
- `app/ai/creation.py` refactored to extract `_build_layered_prompt`; both `build_creation_system_prompt` and the new `build_response_system_prompt` use it.
- Backend gains two new endpoints under `/api/ai/response-prompts/*` (anonymous-readable).
- The existing `/api/ai/creation-prompts` list endpoint gains an optional `?purpose=` filter and returns the new `purpose` field; the `CreationPromptResponse` model gains the field with a default of `creation_format` (backwards-compat).
- iris-client gains `list_response_format_types()`, `get_response_prompt(notation, diagram_type=None)`, and `create_diagram(...)` methods plus `ResponseFormatType` and `ResponsePromptComposed` models.
- MCP server gains `list_response_format_types`, `get_response_prompt`, and `save_doview_analysis` tools. `save_doview_analysis` requires `IRIS_TOKEN` for the MCP server instance.
- No changes to the existing MCP `prompts` channel (ADR-152, ADR-153, ADR-156). Named prompts (ADR-154) continue to flow there.

## Out of scope (deferred to v5.13+)

- **Wire `build_response_system_prompt` into the Iris Ask Iris pipeline** (`app/ai/service.py`). For v5.12.0, the response_format mechanism is invoked explicitly by clients (fetch via MCP tool, apply as reference). Auto-application server-side during `mcp__iris__ask` requires a trigger signal (request flag, scope mcp_system_context hint, or heuristic) — design left for a follow-up ADR.
- **`applicable_response_types` field** on Set / Collection MCP tool responses. The same data is already exposed via the `list_response_format_types` tool; embedding it in scope responses is a UX improvement, not a capability gap.
- **Admin Settings / AI GUI extension** for editing response_format prompts. Authoring works via the existing `PUT /api/ai/creation-prompts/{id}` endpoint with the new `purpose` field round-tripping correctly; explicit GUI rendering of response_format rows is a follow-up.
- **Inheritance for response_format prompts** beyond the existing layer cascade (override → base → notation → diagram_type). Per-scope overrides remain `mcp_system_context`'s job.
- **Argument templating** (`{{set.name}}`) on prompt bodies.
- **Auto-detection** of when a response_format prompt should apply.
- **Additional notations / diagram_types** under response_format — only `(markdown, doview_analysis)` is seeded in v5.12.0; other notations get response_format prompts when there's demand.
- **Creation-format companion for `doview_analysis`** — registering the diagram_type does not require seeding a creation_format prompt for it. When someone wants the in-Iris "Create new doview_analysis" UI flow with a guided LLM interview (mirroring outcomes_map's creation flow), seed that creation_format prompt then.

## See also

- [ADR-094-B](ADR-094-B-AI-Creation-Service.md) — the original AI creation service this extends.
- [ADR-132](ADR-132-Layered-Creation-Prompts.md) — the layered creation-prompt cascade reused here for response prompts.
- [ADR-150](ADR-150-Scope-Level-System-Prompts.md) — scope `system_prompt` (Iris AI auto-apply; stripped from MCP per ADR-151).
- [ADR-151](ADR-151-MCP-Boundary-Strips-Scope-System-Prompts.md) — strip rule unchanged.
- [ADR-152](ADR-152-MCP-Prompts-Capability-for-Scope-System-Prompts.md) — MCP prompts channel for scope system_prompt.
- [ADR-154](ADR-154-Multiple-Named-Prompts-per-Scope.md) — picker-only named prompts; orthogonal.
- [ADR-156](ADR-156-MCP-System-Context-Data-Passthrough.md) — `mcp_system_context` for per-scope passthrough; complementary, scope-specific where response_format is universal.
- [SPEC-157-A](specs/SPEC-157-A-Response-Format-Prompts.md) — schema, endpoint shapes, MCP tool signatures, test plan.
- `docs/prompts/doview-book-prompt-c-iris.md` — source content for the seeded response_format rules.
