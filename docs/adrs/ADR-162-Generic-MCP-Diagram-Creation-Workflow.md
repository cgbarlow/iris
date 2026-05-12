# ADR-162: Generic MCP diagram-creation workflow

Status: Accepted (2026-05-12)
Extends: [ADR-131](ADR-131-MCP-Server-Architecture.md), [ADR-156](ADR-156-MCP-System-Context-Data-Passthrough.md), [ADR-157](ADR-157-Response-Format-Prompts-and-DoView-Analysis-Artefact.md), [ADR-160](ADR-160-MCP-Pairing-Code-Authentication.md), [ADR-161](ADR-161-MCP-Entity-Creation-and-Destination-Flow.md)

## Context

Real Claude Desktop testing of v5.16.0 surfaced a class of issue: the *specific* DoView analysis save flow worked, but creating a *new visual* DoView diagram still required handing the user off to the Iris web UI. The canonical `mcp_system_context` for the Outcomes Theory Book set explicitly routed those requests to the web UI's "guided creation flow."

Investigation showed there is no Svelte wizard — the web UI just opens the canvas and calls `ask(mode='creation', notation='doview')`. The "guided conversation" the user sees is just Iris AI being driven by the existing creation_format prompt cascade (`creation-base-v1` + `creation-doview-notation-v1` + `creation-outcomes-map-v1`). A local model in an MCP client (Claude Desktop / Claude Code) could run the same conversation if it could fetch the same cascade and persist the result.

Two gaps:

1. **The MCP can fetch response_format cascades, but not creation_format cascades.** Both endpoints (`/api/ai/response-prompts/types`, `/api/ai/response-prompts/composed`) hardcode `purpose='response_format'`. The underlying `_build_layered_prompt` already accepts a `purpose` parameter — only the HTTP surface is restrictive.
2. **There is no generic `create_diagram` MCP tool.** v5.16.0 shipped `create_collection / create_set / create_package` (containers), and v5.12.0 shipped `save_doview_analysis` (markdown doview_analysis only). No tool exists for creating diagrams of any (notation, diagram_type) pair generically.

The user explicitly asked: this should be a **standard workflow pattern for diagram creation via MCP, not specific to DoView**.

In the same release cycle the v5.16.0 testing surfaced four small UX bugs that block the new workflow: cross-tab auth doesn't carry (sessionStorage-only read); login bounces to dashboard instead of back; `/admin/settings/ai` filter dropdowns don't constrain each other; same admin page's row-inclusion logic exact-matches notation and hides legitimate diagram_type-layer rows. They're bundled into this release because they affect the same workflow surface.

## Decision

**Generic diagram-creation workflow** (the headline change):

1. **Backend** — extend both `/api/ai/response-prompts/types` and `/api/ai/response-prompts/composed` with a `?purpose=` query parameter, defaulting to `response_format` for back-compat. When `purpose=creation_format`, the existing `build_creation_system_prompt` is called instead of `build_response_system_prompt`.
2. **iris-client** — add a `purpose='response_format'` kwarg to `list_response_format_types` and `get_response_prompt`. Both methods pass through to the backend.
3. **MCP** — three new tools and two extensions:
   - `create_diagram(set_id, name, notation, diagram_type, data, parent_package_id?, description?)` — generic. Wraps existing `client.create_diagram`. Carries the `_DESTINATION_PREAMBLE` (v5.16.0) plus a new `_CREATION_FLOW_PREAMBLE` describing the discover → fetch → guided conversation → compose → confirm-destination → save flow.
   - `list_notations` / `list_diagram_types` — discoverability. Wrap the existing `/api/registry/{notations,diagram-types}` endpoints.
   - `get_response_prompt` / `list_response_format_types` — gain a `purpose` argument, defaulting to `response_format`.
4. **`save_doview_analysis` deprecation** — two-stage retirement. v5.17.0 keeps the tool working but prefixes its description with a deprecation notice pointing at `create_diagram(notation='markdown', diagram_type='doview_analysis', ...)`. v6.0.0 removes it.

**Workflow logic lives in tool descriptions, not in scope context.** The `_CREATION_FLOW_PREAMBLE` is in the `create_diagram` tool description (universal, every MCP client sees it on every session). The canonical `docs/prompts/doview-book-mcp-system-context.md` is trimmed: it no longer contains the diagram-creation step-by-step — it just orients to the Outcomes Theory Book set's purpose and points at `create_diagram` for any new-diagram request.

**Bundled v5.16.0 follow-up fixes:**
- `auth.svelte.ts` `loadFromSession` falls back to localStorage and re-seeds sessionStorage (fixes cross-tab auth).
- `/login` accepts `?redirect=` and honours same-origin paths (fixes login dropping users on dashboard).
- `/admin/settings/ai` filter dropdowns cascade via `DiagramTypeRegistry.notations` (fixes "incompatible combos picker"). Layer=base disables notation/diagram_type fields.
- `/admin/settings/ai` row-inclusion predicate matches notation directly OR via `diagram_type_notations` mapping (fixes "selecting doview shows only 1 prompt").
- New regression test exercising the v5.15.0 symptom: `iris_authenticate` → `create_set` in one session must propagate the new bearer to the second call's outgoing header.

## Why workflow logic lives in tool descriptions, not in mcp_system_context

The v5.13.x → v5.16.x evolution surfaced a clear failure mode: workflow guidance duplicated in per-scope `mcp_system_context` drifts and gets stale. Every time we add or change a write tool, every scope's context that mentions the workflow has to be re-pasted. Worse, contexts only fire when their specific scope is in play — workflow guidance doesn't reach other scopes.

Tool descriptions are universal — every MCP client sees them on every session. A single shared constant (`_CREATION_FLOW_PREAMBLE`, `_DESTINATION_PREAMBLE`) injected into every relevant tool's description gives one source of truth. New write tools in future releases inherit by copy-paste.

`mcp_system_context` keeps its proper role: per-scope orientation. "This set is the Outcomes Theory Book; here are the four options of what you can do here" — but no embedded workflow. Reduces ~30 lines of duplication from the canonical content.

## Why extend `get_response_prompt` with `purpose=`, not add a parallel `get_creation_prompt`

- The underlying composer (`_build_layered_prompt`) is already purpose-aware. The HTTP and client layers are the only places where purpose is hardcoded. Surfacing it as a parameter is a one-line server change and a kwarg on the client.
- Same name, same shape, same return type — only the data dimension changes. A parallel `get_creation_prompt` would duplicate the request/response handling for no benefit.
- The tool stays semantically accurate: it's fetching a *prompt cascade* for a (notation, diagram_type) pair; whether that cascade is for shaping a response or composing a creation is just a dimension.
- Trade-off accepted: the tool name `get_response_prompt` is now slightly misleading (it does both response and creation now). Rename deferred to v6.0.0 alongside the `save_doview_analysis` removal.

## Why `create_diagram`, not `save_diagram`

Matches the v5.16.0 `create_collection / create_set / create_package` family. Same prefix means "create a new entity." `save_doview_analysis` was named differently because v5.12.0 chose "save" for its workflow — that choice doesn't generalise. The deprecation path is clean: keep the legacy name working until v6.0.0, point new workflows at `create_diagram`.

## Why two-stage deprecation of `save_doview_analysis`

- Behaviour is preserved end-to-end through `create_diagram(notation='markdown', diagram_type='doview_analysis', ...)`. From the user's seat, identical.
- External references (Iris's own canonical `mcp_system_context`, any user-authored prompts that mention `save_doview_analysis` by name) need a window to migrate.
- Two-stage retirement matches `iris://` URI scheme migrations and SDK API changes in mature codebases. Avoids breaking changes in a minor release.
- Removal in v6.0.0 (next major) gives a clear signal.

## Consequences

- 60 LOC backend (purpose param routing), 30 LOC iris-client (kwargs), 150 LOC MCP (3 new tools + 2 extensions + preambles + deprecation), 30 LOC frontend (4 fixes), zero DB migration.
- Tool count in iris-mcp: 22 → 26 (`create_diagram`, `list_notations`, `list_diagram_types`, plus the extended `get_response_prompt` / `list_response_format_types`).
- `mcp_system_context` for the Outcomes Theory Book set drops ~30 lines of duplicated workflow guidance; admin must paste the new trimmed content into the field on UAT.
- 38 new tests across all layers.
- The v5.15.0 in-session token-propagation symptom now has a guarding regression test.

## Out of scope (deferred)

- **Removing `save_doview_analysis`.** v6.0.0 alongside the `get_response_prompt` rename.
- **Renaming `get_response_prompt` to `get_diagram_prompt`.** v6.0.0.
- **A JSON-Schema-based data shape endpoint** (`iris_get_diagram_schema(notation, diagram_type)`). The creation_format prompt describes the shape in prose; a formal schema is a future enhancement.
- **`create_element` / `create_relationship` MCP tools.** Same pattern would extend; defer until demand.
- **A `validate_outcomes_map(data)` server-side balance-check tool.** The creation_format prompt embeds rules; a dedicated validator is a future enhancement.
- **Auto-migration of stored `mcp_system_context` values.** The trimmed content for the Outcomes Theory Book set is manually pasted by an admin on UAT (same pattern as v5.13.x and v5.14.x).

## See also

- [ADR-131](ADR-131-MCP-Server-Architecture.md) — iris-mcp stdio architecture.
- [ADR-156](ADR-156-MCP-System-Context-Data-Passthrough.md) — what scope context is for (now without workflow duplication).
- [ADR-157](ADR-157-Response-Format-Prompts-and-DoView-Analysis-Artefact.md) — response_format / creation_format mechanism this ADR extends to MCP.
- [ADR-160](ADR-160-MCP-Pairing-Code-Authentication.md) — auth flow that covers every write tool unchanged.
- [ADR-161](ADR-161-MCP-Entity-Creation-and-Destination-Flow.md) — container creation tools `create_diagram` complements.
- [SPEC-162-A](specs/SPEC-162-A-Generic-MCP-Diagram-Creation-Workflow.md) — endpoint shapes, tool input schemas, frontend fix details, test plan.
