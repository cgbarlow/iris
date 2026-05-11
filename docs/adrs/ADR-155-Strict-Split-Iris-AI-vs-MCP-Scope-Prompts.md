# ADR-155: Strict split between Iris-AI and MCP scope prompts

Status: Accepted (2026-05-11)
Amends: [ADR-150](ADR-150-Scope-Level-System-Prompts.md), [ADR-152](ADR-152-MCP-Prompts-Capability-for-Scope-System-Prompts.md), [ADR-153](ADR-153-Drop-Redundant-iris-Prefix-From-MCP-Prompt-Names.md)
Extends: [ADR-154](ADR-154-Multiple-Named-Prompts-per-Scope.md)

## Context

ADR-150 added a single `system_prompt` per scope that auto-applies to every Ask Iris call. ADR-152 surfaced that same `system_prompt` as the scope's MCP `prompts` entry (`set:<uuid>` / `collection:<uuid>`). So a single column was doing two jobs at once: server-side auto-apply in Iris's internal AI flows AND user-pickable directive in the MCP prompt picker.

This is a problem when those two audiences want different content. Examples:

- An Iris author wants "always cite the control number" to apply to every Iris discussion / creation flow on a scope (good `system_prompt` content), but the same author wants the MCP picker entry for that scope to be a richer external-facing directive — e.g. "summarise + cite + retrieve diagrams via mcp__iris__get_diagram" — which would be wrong to inject into every internal Iris AI call.
- Conversely, a directive that's useful inside Iris's UI ("draft formal language for the user's report") is irrelevant or counterproductive when invoked from Claude Code where the model is talking to the user directly.

ADR-154 added per-scope named prompts that are picker-only. But those are picker-only by being many; the *primary* per-scope prompt was still tied to the auto-apply behaviour, conflating the two roles.

## Decision

**Split the single per-scope `system_prompt` column into two orthogonal columns.** Both nullable text.

- `system_prompt` (existing, unchanged behaviour for Iris AI) — auto-applies in Iris's Ask Iris pipeline (web GUI + MCP `ask` tool, both via `app/ai/scope_prompts.py`). **No longer** surfaced in the MCP `prompts` channel.
- `mcp_prompt` (new) — surfaced in the MCP `prompts` channel as the scope's MCP picker entry (`set:<uuid>` / `collection:<uuid>`). **Never** auto-applies in Iris AI.

Both apply at both scope levels (Collection + Set). Inheritance for `system_prompt` continues to follow ADR-150 (Set sees its own + parent Collection's, concatenated). Inheritance for `mcp_prompt` does not need to be considered — the MCP picker shows distinct entries per scope and the user picks one.

Both columns participate in ADR-151's MCP-boundary strip (neither leaks via the `get_set` / `get_collection` MCP tool responses) — same anti-injection posture for both.

## Why split rather than reuse `system_prompt` for both

- **Two roles, two audiences, two contents.** The Iris-AI audience is the model running inside Iris's discussion / creation flows; the MCP audience is the model on the user's client (Claude Code, Claude Desktop). They legitimately need different directives. Squeezing both into one column forces compromise content that's wrong for at least one audience.
- **No silent behaviour change for Iris AI.** Authors who never go near the MCP picker keep getting exactly the v5.8.x behaviour for their `system_prompt`. The new `mcp_prompt` column is purely opt-in.
- **Symmetric with named prompts.** ADR-154 named prompts already separate "picker-only" content from auto-apply. This ADR finishes the job for the scope's single primary slot.

## Why this is a breaking change for the MCP picker

Pre-v5.10.0 scopes with a populated `system_prompt` were surfaced in the MCP picker as `set:<uuid>` / `collection:<uuid>` with `system_prompt` as the body. Post-v5.10.0, the MCP picker source switches to `mcp_prompt`. Existing scopes have `mcp_prompt = NULL`, so their MCP picker entries **disappear** until an author populates the new column.

This is intentional — chose for clarity over preservation per the design question raised during build. Authors who want the v5.8.x behaviour (same content in both roles) simply copy the body from `system_prompt` into `mcp_prompt`. Authors who want distinct content populate them independently. Authors who only want Iris-AI behaviour need do nothing.

Communicated via CHANGELOG `[5.10.0]` under "Changed (breaking)" with migration guidance.

## Why no auto-migration of `system_prompt` content into `mcp_prompt`

- **Quiet content drift.** Auto-copying would put content into the MCP picker that the author never deliberately put there. Some `system_prompt` content is Iris-internal in spirit ("use Iris's terminology for elements") and would be wrong for the external audience.
- **The migration is one PUT per scope.** Authors can do it manually if they want; or leave the MCP picker empty for that scope.
- **The first deploy is the right moment.** The author edits the scope, sees the new field, fills it in deliberately.

## Why one column, not promoting one named prompt to "primary MCP"

- **The scope MCP picker entry's name is stable** (`set:<uuid>`). Promoting a named prompt would require a per-scope "primary" pointer that any rename / delete invalidates.
- **The picker UX is cleanest** with one well-known per-scope entry plus many named entries.
- **Less moving parts.** A second nullable column on existing tables vs. a new association.

## Consequences

- One new SQLite migration `m049_mcp_prompt_column.py` (additive ALTERs, idempotent).
- One new Supabase migration `m053_mcp_prompt_and_prompts_timestamps.sql`:
  1. `ALTER TABLE collections / sets ADD COLUMN IF NOT EXISTS mcp_prompt TEXT`
  2. Fix v5.9.0's `prompts.created_at` / `prompts.updated_at` from `text` to `timestamptz`. The Supabase adapter (`backend/app/db/adapter.py:_convert_params`) auto-converts ISO datetime strings to native datetime before asyncpg, and asyncpg rejected `datetime` against `text`. Every other Iris table uses `timestamptz`. This was the cause of the user-visible `DataError: invalid input for query argument $7: datetime.datetime(...)` when creating named prompts on the v5.9.0 UAT deploy.
- Pydantic `CollectionUpdate` / `CollectionResponse` / `SetUpdate` / `SetResponse` gain a `mcp_prompt: str | None` field.
- `update_collection` and `update_set` accept `mcp_prompt` and persist it.
- `app/prompts/service.py:list_scope_prompts` now reads from `mcp_prompt` for the scope's MCP picker entries. The `entry_kind` literal stays `"system_prompt"` for backwards-compat with iris-client / MCP code that discriminates on it (rename would be a breaking change to every consumer; the literal is now slightly misnamed but the behaviour is correct).
- `app/ai/scope_prompts.py` and `app/ai/service.py` continue to read from `system_prompt` only — Iris AI composition unchanged.
- iris-client `IrisSet` and `Collection` models gain `system_prompt` and `mcp_prompt` fields (the existing `_Permissive` base accepted them implicitly; making them explicit is for type-checked client code).
- Frontend `/sets/[id]` and `/collections/[id]` edit pages get a second textarea ("MCP prompt") below the existing "System prompt".
- ADR-151's strip rule extends conceptually to `mcp_prompt` too — but in practice no MCP tool response currently exposes the `mcp_prompt` column (`get_set` / `list_sets` tool responses already pass through model serialisation that omits nulls; adding the column there would be explicit opt-in elsewhere). The MCP boundary doesn't need a code change — the column is only intended to flow through the `prompts` channel.

## Out of scope (deferred)

- **Inheritance for `mcp_prompt`.** Unlike `system_prompt` (which composes Collection + Set per ADR-150), `mcp_prompt` is one-per-scope-shown-in-picker. Authors who want a Collection-wide MCP prompt populate the collection's `mcp_prompt`. Sets in that Collection each have their own. No composition — the picker is the disambiguation layer.
- **Per-mode prompts.** A future "discuss-mode only" / "creation-mode only" split of `system_prompt` is still possible (see ADR-150 out-of-scope) and orthogonal to this ADR.
- **One-time content migration tooling.** No CLI or batch endpoint to copy `system_prompt` → `mcp_prompt`. Authors edit the scope and paste if they want both populated.

## See also

- [ADR-150](ADR-150-Scope-Level-System-Prompts.md) — original scope-prompt foundation; the column this ADR splits.
- [ADR-151](ADR-151-MCP-Boundary-Strips-Scope-System-Prompts.md) — anti-injection strip; applies symmetrically to `mcp_prompt`.
- [ADR-152](ADR-152-MCP-Prompts-Capability-for-Scope-System-Prompts.md) — the MCP `prompts` channel; this ADR redirects its body source.
- [ADR-153](ADR-153-Drop-Redundant-iris-Prefix-From-MCP-Prompt-Names.md) — current naming convention.
- [ADR-154](ADR-154-Multiple-Named-Prompts-per-Scope.md) — per-scope named prompts; same picker-only ethos, many per scope.
- [SPEC-155-A](specs/SPEC-155-A-MCP-Prompt-Column.md) — schema, endpoint shapes, MCP wiring, edit-page wiring, test plan.
