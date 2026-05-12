# ADR-159: Scope `mcp_system_context` in search results

Status: Accepted (2026-05-12)
Extends: [ADR-125](ADR-125-Search-Across-Sets-Collections.md), [ADR-156](ADR-156-MCP-System-Context-Data-Passthrough.md)

## Context

ADR-156 (v5.11.0) established `mcp_system_context` as a per-scope data passthrough field — Set / Collection orient guidance that flows through MCP tool responses on `get_set` / `get_collection` (and `list_sets` / `list_collections`). The intent: a model browsing a scope sees the scope's context as part of the entity payload, no separate prompt-fetch round-trip.

In real Claude Desktop testing of v5.13.x, the orient instructions were not landing. Diagnosis: when a user said "open the outcomes theory book in iris", Claude's natural flow was `search('outcomes theory book')` → returned the matched Set with id, name, deep_link → reply with the URL and a brief follow-up question. **Claude never called `get_set`.** The `mcp_system_context` content — no matter how rigid or well-worded — never reached Claude's context, so the orient-first-with-menu pattern didn't fire.

The fix has to be at the search response shape, not at the content. Otherwise the orient instructions only land on a `get_set` call that may never happen.

## Decision

Extend search results for `result_type=set` and `result_type=collection` hits to include the matching scope's `mcp_system_context` field. Specifically:

- `backend/app/search/models.py:SearchResult` gains `mcp_system_context: str | None = None`. Only populated for `set` / `collection` hits; `None` (or absent) on element / diagram / package / other hits.
- `backend/app/search/service.py` updates the SQLite and Postgres SET / COLLECTION result branches to SELECT the `mcp_system_context` column and include it in the result dict.
- `iris-client.SearchResult` model gains the same field for type access.
- The MCP layer requires no changes — `mcp_system_context` is not in `_STRIPPED_KEYS` (per ADR-156), so it flows through search responses as data the same way it does for `get_set`.

## Why include it in search results, not in some other channel

- **Search is the natural entry point.** "Open the outcomes theory book" → `search`. The orient guidance has to be present in the response Claude actually receives.
- **A separate `iris_get_scope_context(set_id)` MCP tool would help only if Claude knew to call it** — same trigger problem one level deeper. Putting the content directly on the search hit removes the need for any additional tool call.
- **Bandwidth cost is negligible.** A `mcp_system_context` is at most ~1 KB; even a search returning 20 hits adds <20 KB total. Models tolerate this easily; the alternative (an entirely missed orient) is worse.
- **No new strip rule needed.** ADR-156 already established that `mcp_system_context` is intentionally pass-through data (in contrast to `system_prompt`, which is server-side-only and stripped at the MCP boundary). Search results are tool data; the same rules apply.

## Why not also include `package_count` / `package_count_root` / other ScopeResponse fields

- **Search hits are intentionally lean.** Adding count fields would inflate every search response with metadata most calls don't need. `mcp_system_context` is justified specifically because it's the orient-instruction channel — it has to land on first contact. Counts are nice-to-have and can come from a follow-up `get_set` if the model wants them.
- **`get_set` already returns `package_count` / `package_count_root`** (ADR-158). If a model wants the structural breadth signal, `get_set` is one tool call away.

## Why not extend `iris-client.search()` signature

The signature stays as-is. The new field is purely additive on the response payload. Existing callers that only access `.id`, `.name`, etc. continue to work unchanged.

## Consequences

- Backend: 4 SQL changes (Sets / Collections × SQLite / Postgres) plus model field addition.
- iris-client: model field addition.
- MCP: zero code change (passthrough).
- Frontend: zero impact (the web UI doesn't render `mcp_system_context` in search-results UI).
- Search results are slightly larger when scope hits are present, by the size of the populated `mcp_system_context` (typically a few hundred bytes to ~1 KB per hit). Negligible.
- 4 new backend tests + 4 new iris-client tests.
- Doc trim: canonical content for the Outcomes Theory Set's `mcp_system_context` field cut from ~140 lines to ~50 lines, since the verbose flow descriptions can live in the response_format prompt body (where they belong) once an admin amends that row via `/admin/settings/ai`.

## Out of scope (deferred)

- Surfacing `mcp_system_context` on `list_packages` or `list_diagrams` results (these are sub-scope; the field is per-scope-root).
- Scope context in MCP `prompts` channel responses (that channel has its own protocol and isn't a discovery surface for sets).
- A dedicated `iris_get_scope_context(set_id)` MCP tool (would have the same trigger-reliability problem this ADR is fixing).

## See also

- [ADR-125](ADR-125-Search-Across-Sets-Collections.md) — the search endpoint this ADR extends.
- [ADR-150](ADR-150-Scope-Level-System-Prompts.md) — `system_prompt` (Iris-AI auto-apply; not affected here).
- [ADR-151](ADR-151-MCP-Boundary-Strips-Scope-System-Prompts.md) — strip rule (still in force for `system_prompt`; `mcp_system_context` is not stripped).
- [ADR-156](ADR-156-MCP-System-Context-Data-Passthrough.md) — the field this ADR makes more discoverable.
- [SPEC-159-A](specs/SPEC-159-A-Scope-Context-In-Search-Results.md) — schema and test plan.
- `docs/prompts/doview-book-mcp-system-context.md` — the canonical content this surfaces.
