# ADR-156: Scope `mcp_system_context` is data passthrough, not a slash-command

Status: Accepted (2026-05-11)
Supersedes: [ADR-155](ADR-155-Strict-Split-Iris-AI-vs-MCP-Scope-Prompts.md) (in part)
Amends: [ADR-151](ADR-151-MCP-Boundary-Strips-Scope-System-Prompts.md), [ADR-152](ADR-152-MCP-Prompts-Capability-for-Scope-System-Prompts.md)

## Context

ADR-155 (v5.10.0) split the scope's MCP-facing content out of `system_prompt` into a new column `mcp_prompt`, and surfaced it through the MCP `prompts` channel as a slash-command (`/iris:set:<uuid>` / `/iris:collection:<uuid>`). Released to UAT immediately.

In use, the slash-command exposure turned out wrong for the intended job. The content the user wants attached to a scope is **initial context for an MCP client browsing the scope** — not a directive the user picks. It should accompany `get_set` / `get_collection` MCP tool responses as scope-level data the model can read while exploring, not appear as a separate command the user has to invoke.

We had this flow pre-v5.8.2. In v5.8.0 (ADR-150) `system_prompt` was simply a field on Collections and Sets, and MCP `get_set` returned the full record including it as data. ADR-151 then redacted the field at the MCP boundary because `system_prompt` had become an Iris-AI-only directive whose contents were never intended for the external model and posed a prompt-injection vector when surfaced as untrusted tool data.

ADR-156 reintroduces the data-passthrough mechanism but on a column **explicitly authored for that purpose**, so the security analysis of ADR-151 doesn't apply: the content is not internal Iris-AI behaviour leaking out, it's deliberate scope context the author intends external models to see.

## Decision

Three changes, all in v5.11.0.

### 1. Rename the column

Rename `mcp_prompt` (introduced v5.10.0, ADR-155) → `mcp_system_context`. The new name reflects its purpose: scope context for MCP clients, not a pickable prompt. SQLite m050 and Supabase m054 perform the rename idempotently.

### 2. Remove scope-level entries from the MCP `prompts` channel

`backend/app/prompts/service.py:list_scope_prompts` no longer emits `set:<uuid>` / `collection:<uuid>` entries. The endpoint now returns **named prompts only** (ADR-154 entries, names of the form `set:<uuid>:<name>` / `collection:<uuid>:<name>`). This is a partial revert of ADR-152's scope-system-prompt exposure: scope `system_prompt` is no longer in MCP (ADR-151 strip still applies), and scope `mcp_system_context` was never wired in (ADR-155's wiring is undone before any prod use).

ADR-152's MCP `prompts` capability stays. ADR-154 named prompts still flow through it. Only the per-scope single entry goes away.

### 3. Let `mcp_system_context` flow through MCP tool responses

`mcp_system_context` is **not** in `iris_mcp/links.py:_STRIPPED_KEYS`, so the field passes through `get_set`, `list_sets`, `get_collection`, `list_collections`, and the search endpoint untouched. An MCP client browsing the scope sees the column as part of the entity payload — exactly the pre-ADR-151 flow but on a column built for the role.

`system_prompt` continues to be stripped (ADR-151 unchanged) because it remains a server-side-only directive for Iris's internal AI flows.

## Why undo ADR-155's slash-command exposure rather than keep both

- **One concept, one mechanism.** Keeping the same column as both a tool-data passthrough AND a slash-command entry doubles the consumer's mental model with no benefit. Authors picking which behaviour they want when they only want one is friction.
- **The slash-command path duplicates named prompts** (ADR-154). If an author wants a discrete pickable directive, that's already what named prompts are for — and they support many per scope. The scope-level single slash command was a redundant slot.
- **The passthrough path is genuinely new** and is the actual unmet need.

Removing the slash-command exposure now is cheap because v5.10.0 was released minutes before this ADR — no authored content depends on it yet on the UAT instance.

## Why not strip `mcp_system_context` symmetrically with `system_prompt`

- **ADR-151's strip targets server-side-only directive content.** That category fits `system_prompt` (Iris-AI internal). It does not fit `mcp_system_context`, which exists *because* the author wants the external model to see it.
- **Prompt-injection posture.** Tool data is still tool data — the client model treats it as data, not as a directive. The author authors this column knowing it will land as data on browse. Adversarial scope content is fundamentally an "edit-permission" problem (same scope where any field could carry adversarial text). No new attack surface vs. `description` or `name`.

## Why rename rather than re-use `mcp_prompt`

- **`mcp_prompt` implied "a prompt for MCP"**, fitting the v5.10.0 slash-command framing. With the slash-command path removed, the name misleads. `mcp_system_context` says what the field is: scope-level system-style context for MCP-side consumption.
- **One-time cost.** v5.10.0 was released minutes ago; renaming now incurs one extra migration and a small code sweep. The alternative — living with the misnomer — multiplies the cost over every future code reader.

## Why no auto-migration of v5.10.0 `mcp_prompt` content (the column is renamed, content preserved)

The column rename preserves data. Any author who populated `mcp_prompt` on UAT during v5.10.0's brief window will find their content under `mcp_system_context` after deploy. They may want to revisit it now that the behaviour is "context passthrough" rather than "picker entry" — different content suits the different role — but the data isn't lost.

## Consequences

- One new SQLite migration `m050_rename_mcp_prompt_to_mcp_system_context.py` (idempotent column rename).
- One new Supabase migration `m054_rename_mcp_prompt_to_mcp_system_context.sql` (idempotent column rename via `information_schema` guard).
- Pydantic `CollectionUpdate` / `CollectionResponse` / `SetUpdate` / `SetResponse` field renamed `mcp_prompt` → `mcp_system_context`.
- `update_collection` and `update_set` keyword arg renamed correspondingly.
- `app/prompts/service.py:list_scope_prompts` stripped of scope-level SELECTs; emits named-prompt entries only. Docstring and code length significantly reduced.
- `iris-client` `IrisSet` and `Collection` models field renamed.
- Frontend state variable + textarea + label + helper text renamed and reworded. The textarea now says "MCP system context" with a placeholder explaining "Passed through as data on MCP get_set responses".
- `mcp/src/iris_mcp/links.py:_STRIPPED_KEYS` unchanged — still just `("system_prompt",)`. New test `mcp/tests/test_links_passes_mcp_system_context.py` pins the contract that `mcp_system_context` passes through.
- Existing `mcp/tests/test_links_strip_system_prompt.py` unchanged — ADR-151 still in force.
- 5 new tests; existing scope-index tests rewritten to assert the new contract (picker = named prompts only; scope content is data-passthrough). 233 tests pass; only the pre-existing `test_no_extra_rls_tables` failure (issue 88 Phase 4 TODO).

## Out of scope (deferred)

- Inheritance for `mcp_system_context`. Set-scope content does not currently merge with parent-Collection content on the tool response. If authors find they want both layered, revisit then. Today: whichever scope is being browsed contributes its own column.
- A second strip table for scope columns that authors might want stripped. Not asked for; deferred.
- Migration tooling to copy v5.10.0 `mcp_prompt` body to `system_prompt` or named prompts. Authors handle by hand if they want different content distribution post-rename.

## See also

- [ADR-150](ADR-150-Scope-Level-System-Prompts.md) — original `system_prompt` foundation; Iris-AI auto-apply behaviour preserved unchanged.
- [ADR-151](ADR-151-MCP-Boundary-Strips-Scope-System-Prompts.md) — `system_prompt` strip at MCP boundary; still in force, complemented now by ADR-156's explicit passthrough exception for `mcp_system_context`.
- [ADR-152](ADR-152-MCP-Prompts-Capability-for-Scope-System-Prompts.md) — MCP `prompts` channel; this ADR removes the scope-level entry but keeps the channel for ADR-154 named prompts.
- [ADR-153](ADR-153-Drop-Redundant-iris-Prefix-From-MCP-Prompt-Names.md) — naming convention unchanged.
- [ADR-154](ADR-154-Multiple-Named-Prompts-per-Scope.md) — picker entries; now the *only* contents of the picker.
- [ADR-155](ADR-155-Strict-Split-Iris-AI-vs-MCP-Scope-Prompts.md) — superseded in part. The split column survives (renamed); the slash-command exposure does not.
- [SPEC-156-A](specs/SPEC-156-A-MCP-System-Context-Data-Passthrough.md) — schema, code-rename map, MCP boundary contract, test plan.
