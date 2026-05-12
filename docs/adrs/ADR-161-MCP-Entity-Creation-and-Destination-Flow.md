# ADR-161: MCP entity-creation tools + destination-confirmation flow

Status: Accepted (2026-05-12)
Extends: [ADR-131](ADR-131-MCP-Server-Architecture.md), [ADR-157](ADR-157-Response-Format-Prompts-and-DoView-Analysis-Artefact.md), [ADR-160](ADR-160-MCP-Pairing-Code-Authentication.md)

## Context

In real Claude Desktop use of v5.15.0, a user asked to save a generated DoView analysis "under a new set called 'DoView Analysis' in the Outcomes Theory collection." Claude correctly identified that the Iris MCP exposes no tool for creating new sets, collections, or packages — only `save_doview_analysis` against an existing `set_id` — and was forced to ask the user to leave the conversation, create the set manually in the web UI, copy its id, and paste it back. That's the same workflow cliff `iris_authenticate` was introduced to remove for the auth side; we now hit the same shape on the **organisation** side.

Two changes are needed, both generic (not tied to `save_doview_analysis`):

1. **MCP can create new sets, collections, and packages** so destination trees can be stitched in-conversation.
2. **Save tools confirm destination up-front** instead of guessing or trapping the user in a late-bound "give me a set_id" loop.

The backend already has the create endpoints (`POST /api/{collections,sets,packages}`) gated behind the same `get_current_user` dependency `save_doview_analysis` uses, so v5.15.0's pairing/PAT flow covers them with **zero backend change**.

## Decision

Add three new MCP tools — `create_collection`, `create_set`, `create_package` — each a thin wrapper over the existing iris-client + backend endpoint. Each new tool catches `IrisAuthError` and returns the same structured `auth_required` payload `save_doview_analysis` uses, so the v5.15.0 pairing-recovery flow handles every write tool uniformly.

Add a **destination-confirmation preamble** to every write tool's `description` (starting with `save_doview_analysis` and the three new create_* tools). The preamble instructs the model to confirm "where do you want this saved?" with the user before the save call, offering: existing set, new set in existing collection, new collection + new set, optionally + new package. AskUserQuestion if the client supports it; numbered list otherwise.

## Why three first-class tools, not a fat `save_doview_analysis(set_name=, collection_name=)` shortcut

- **Separation of concerns.** Saving content and organising containers are different intents. Mixing them couples save semantics to container creation and makes the save endpoint harder to evolve.
- **Reuse for any future write tool.** A future `save_element`, `save_relationship`, or `save_package` benefits from the same primitives without each one re-implementing "find-or-create the container."
- **Cleaner failure mode.** A combined call has two failure modes (container creation failed; save failed); two separate calls leave a clean, recoverable trail — the user can see exactly which step failed.
- **Existing precedent.** v5.15.0's `iris_authenticate` is a first-class tool, not a side-effect of `save_doview_analysis(authenticate=)`. Same shape here.

## Why each tool's description carries the destination preamble, not response_format / mcp_system_context

- **Universality without configuration.** Every MCP client sees tool descriptions; not every client fetches `get_response_prompt` or hits a scope with `mcp_system_context` set.
- **Travels with the tool.** Adding a new write tool in a future release copies the preamble template — no separate doc edit, no risk of drift.
- **Avoids the v5.13.x "context never landed" problem.** The orient instructions in `mcp_system_context` were silently missed when Claude went straight to `search`. Tool descriptions are loaded every session.
- **Trade-off accepted.** Descriptions get longer. Negligible bandwidth cost; vastly outweighed by reliability.

## Why no backend changes

- All three create endpoints already exist (`POST /api/collections`, `POST /api/sets`, `POST /api/packages`) with the right Pydantic shapes (`CollectionCreate`, `SetCreate`, `PackageCreate`) and the same `get_current_user` dependency `save_doview_analysis` uses.
- The PAT issued by the v5.15.0 pairing flow already satisfies that dependency. No new permission model needed.
- Backend tests for the create endpoints already exist and pass.

## Why bundle the `/settings` Default Notation dropdown fix in this release

`frontend/src/routes/settings/+page.svelte`'s Default Notation `<select>` lists only 4 of the 7 notation IDs in the registry (`doview`, `markdown`, `bpmn` are missing). User-spotted in this v5.15.0 → v5.16.0 conversation; small enough to ride along with the entity-creation work. Touches the same `/settings` page area; same release cadence. Avoiding a separate one-line release.

## Consequences

- iris-client gains `create_collection`, `create_set`, `create_package` methods.
- MCP gains three new tools wrapping them, each returning the v5.15.0 `auth_required` payload on 401.
- `save_doview_analysis` description gets the destination-confirmation preamble (no signature change).
- Three new tools' descriptions carry the same preamble + cross-references to each other.
- `docs/prompts/doview-book-mcp-system-context.md` drops the static topic-mapping heuristic (parent_package_id by topic) in favour of "ask the user; create_* if needed."
- `/settings` notation dropdown gains 3 missing options.
- ~17 new tests across iris-client (6), MCP (10), frontend (1).
- No DB migration. No backend change. No frontend route change.

## Out of scope (deferred)

- **Element / relationship creation MCP tools** — addressable by the same pattern; defer to a future release when the demand is real.
- **Bulk container creation** (e.g. "create this whole set with these 5 packages in one shot") — would be a `setup_workspace`-style tool; defer until there's a real workflow asking for it.
- **Server-side find-or-create idempotency** — if a user runs `create_set(name="X")` twice, two sets get created. Idempotency keying is a future enhancement.
- **MCP-side caching of recently-created ids** — Claude tracks them in conversation; explicit caching adds state with no clear win.
- **Container deletion / rename MCP tools** — write-but-not-create; same auth path, but defer until needed.

## See also

- [ADR-131](ADR-131-MCP-Server-Architecture.md) — iris-mcp stdio architecture.
- [ADR-157](ADR-157-Response-Format-Prompts-and-DoView-Analysis-Artefact.md) — response_format mechanism (alternative location for the preamble that was rejected).
- [ADR-160](ADR-160-MCP-Pairing-Code-Authentication.md) — the auth flow these new tools rely on.
- [SPEC-161-A](specs/SPEC-161-A-MCP-Entity-Creation-and-Destination-Flow.md) — method/tool shapes, preamble text, test plan.
