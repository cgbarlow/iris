# ADR-163: Centralised, admin-editable MCP server instructions

Status: Accepted (2026-05-13)
Extends: [ADR-156](ADR-156-MCP-System-Context-Data-Passthrough.md), [ADR-157](ADR-157-Response-Format-Prompts-and-DoView-Analysis-Artefact.md), [ADR-162](ADR-162-Generic-MCP-Diagram-Creation-Workflow.md)

## Context

v5.17.0 (ADR-162) moved diagram-creation workflow logic out of per-scope `mcp_system_context` into the `create_diagram` tool's description. Good progress, but the canonical content for the Outcomes Theory Book set still embedded two universal mechanisms that any authored scope would duplicate:

- **ORIENT-FIRST protocol** — "describe the scope, call the structural-overview command, present the menu verbatim, AskUserQuestion or numbered list". Identical for every scope; only the menu differs.
- **DISCOVERY catalogue** — the list of universal tools (`list_response_format_types`, `iris_package_hierarchy`, etc.). Not scope-specific at all.

Real testing of v5.17.0 surfaced the question: can the universal mechanism be lifted out so that authoring a new scope just means writing the scope-specific menu + a one-sentence description, not re-pasting the protocol boilerplate?

The MCP spec has the exact channel for this: `Server(name, instructions=...)`. The instructions are returned in the InitializeResult and loaded by every compliant MCP client (Claude Desktop / Claude Code / Cursor) on every session. Universal across every scope, every tool call.

The same testing surfaced a corollary requirement: the content must be **admin-editable from `/admin/settings/ai`**, consistent with every other prompt-shape concern in Iris (creation_format prompts, response_format prompts, per-scope `mcp_system_context`). Hardcoding the instructions in iris-mcp Python code would be the lone exception, and would create a friction every time the protocol needs to evolve.

## Decision

Introduce a third `purpose` value on `ai_creation_prompts`: `mcp_server_instructions`. Singleton row at `layer='base'`, `notation=NULL`, `diagram_type=NULL`. Seeded in v5.18.0 with the orient-first protocol + discovery catalogue + auth-recovery + workflow-pointers text.

Backend exposes the row body via `GET /api/ai/server-instructions` (anonymous-readable; no auth required because the instructions describe how to use the MCP server, not its data).

iris-mcp fetches the body once at startup and passes it to `Server(name=..., instructions=...)`. The MCP SDK already accepts the `instructions` constructor parameter (verified via signature inspection); the InitializeResult surfaces it on every session.

`/admin/settings/ai` surfaces the new purpose in its existing filter/edit machinery — extend the `PURPOSES` Svelte const and the `appliesToLabel()` helper. No new UI components.

iris-mcp keeps a **hardcoded fallback baseline** in `iris_mcp/server_instructions.py`. The fallback fires only when the backend is unreachable at startup, so iris-mcp stays functional in degraded states. The fallback text matches the seeded body on day one (acceptable DRY trade-off — the fallback is a frozen safe baseline, not a live mirror).

## Three layers of prompt content (after v5.18.0)

| Layer | Where | Edit cadence | Scope |
|---|---|---|---|
| Per-tool workflow guidance | MCP tool descriptions (code constants) | code change + release | per tool, universal |
| Server-wide orient + discovery | `ai_creation_prompts` singleton, surfaced via MCP `instructions` | edit in `/admin/settings/ai`; next session sees it | server, universal |
| Scope-specific menu | per-scope `mcp_system_context` on Set/Collection | edit per scope | per scope |

The canonical Outcomes Theory Book `mcp_system_context` drops from ~30 lines (v5.17.0) to ~12 lines (v5.18.0). New scopes only need to author the scope-specific menu + a description + a structural-overview-call name.

## Why store as a singleton in `ai_creation_prompts` (not a new table)

- Same shape as creation_format and response_format prompts: a single text body, admin-editable, version-comparable via the existing prompts machinery.
- `purpose` discriminator already exists; adding a third value is a one-line Pydantic Literal extension + one-line `_VALID_PURPOSES` tuple extension.
- The admin UI's existing filter/edit dialog handles the new row without changes — `layer='base'` already disables notation/diagram_type pickers (v5.17.0 Fix #3).
- Audit, deactivate, edit-history all come for free via the existing CRUD.

## Why a dedicated `GET /api/ai/server-instructions` endpoint (not reusing `/response-prompts/composed?purpose=mcp_server_instructions`)

- The composed endpoint requires `notation=` and `diagram_type=` query parameters (cascade-shaped). `mcp_server_instructions` is a singleton — those parameters have no meaning.
- A dedicated endpoint reads cleaner from the iris-mcp side and from the OpenAPI surface.
- 25 LOC vs. the alternative's "special-case purpose value in two cascade endpoints". Worth the focused endpoint.

## Why anonymous-readable

- iris-mcp fetches at startup with no token. Adding auth would force every iris-mcp install to be authenticated before any MCP client could use it.
- The body describes mechanism, not data. Same posture as the existing `/response-prompts/composed` endpoint (also anonymous-readable).
- Self-hosting users who don't want this exposed can revoke anonymous access to the endpoint via existing CSP / proxy controls.

## Consequences

- One new purpose value in `_VALID_PURPOSES` and the Pydantic Literal.
- One new endpoint `GET /api/ai/server-instructions`.
- One new SQLite migration (m053) + one Supabase migration (m057) seeding the singleton row.
- New iris-mcp `server_instructions.py` module (~40 LOC) with fetch helper + hardcoded fallback.
- `build_server()` gains an `instructions: str | None = None` argument forwarded to `Server(...)`.
- `__main__.py:run()` fetches instructions before constructing the server.
- Frontend `PURPOSES` const gains one entry; `appliesToLabel()` gains one branch.
- Canonical `doview-book-mcp-system-context.md` trimmed to ~12 lines. Admin must paste the trimmed content into the set's `mcp_system_context` field on UAT.
- Three copies of the same body on day one (seeded row, hardcoded fallback, canonical doc). Acceptable; see SPEC for rationale.
- ~13 new tests across backend, MCP, frontend, migrations.

## Out of scope (deferred)

- Reading the canonical doc text at migration / fallback time to deduplicate the three copies — defer to v6.0.0.
- Versioning the instructions ("this body is older than the iris-mcp build expects") — no real case yet.
- Cascading multiple `mcp_server_instructions` rows (e.g. base + scope-override). Singleton works; revisit if multi-tenancy or per-deployment-fork needs surface.
- Renaming `ai_creation_prompts` to `ai_prompts` — cosmetic; v6.0.0.
- Admin-UI authoring metadata for the singleton row ("loaded by iris-mcp at startup; restart your MCP client to see changes"). UX polish; v5.19+.

## See also

- [ADR-156](ADR-156-MCP-System-Context-Data-Passthrough.md) — what `mcp_system_context` is for (per-scope data passthrough; now narrower).
- [ADR-157](ADR-157-Response-Format-Prompts-and-DoView-Analysis-Artefact.md) — the `purpose` discriminator on `ai_creation_prompts` this ADR extends.
- [ADR-162](ADR-162-Generic-MCP-Diagram-Creation-Workflow.md) — generic create_diagram + the workflow-in-tool-descriptions principle this ADR generalises.
- [SPEC-163-A](specs/SPEC-163-A-Centralised-MCP-Server-Instructions.md) — schema extension, endpoint shape, MCP wiring, admin UI changes, test plan.
