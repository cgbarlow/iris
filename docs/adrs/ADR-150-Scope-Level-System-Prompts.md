# ADR-150: Scope-level system prompts (Collection and Set)

Status: Accepted (2026-05-11)

## Context

Iris's AI features (Ask Iris in discuss and creation modes; the Iris
MCP `ask` tool consumed by Claude Desktop / web) compose a system
prompt from one place only: the active provider's `system_prompt` row
plus retrieved Set context. There is no way for the owner of a
Collection or Set to attach domain-specific instructions that travel
with the scope.

A user editing a Collection or Set wants to be able to say things
like "this collection is about NZISM controls — always cite the
control number" or "this set is the Auckland Transport reference
model — preserve element naming conventions in any creation output".
Today that intent has to be repeated in every prompt by every user.

This ADR also sets up the surface that ADR-151 plugs into for Skills.

## Decision

**Add a nullable `system_prompt TEXT` column to both the `collections`
and `sets` tables.** When an AI request is dispatched for a scope
(set, multi-set, or set within a collection), compose system content
in this order:

1. **Scope prepend** — collection prompt(s) first, then set prompt(s),
   each separated by a blank line.
2. **Provider system prompt** (existing, unchanged).
3. **Creation prompt** (if creation mode; ADR-132 layered prompts).
4. **Retrieved context** (existing, unchanged).

The scope prepend is additive — a set inherits its parent collection's
prompt, never overrides it. This matches the way the user picked it
during planning and mirrors how nested settings compose elsewhere in
the stack (e.g., Claude Code's project-then-user settings cascade).

**Multi-set requests** that span multiple collections concatenate each
distinct collection prompt once, in `set_ids` order, then each set
prompt in `set_ids` order. Duplicate collection prompts are
deduplicated by collection id.

**Anonymous AI asks** (ADR-123) get scope prompts applied the same way
as signed-in asks. The scope prompt is metadata the asker can already
see (it appears in the edit screen of any collection/set they can
view); no new privilege boundary.

**Soft warning at 16 000 chars**: when the composed `system_content`
exceeds 16 000 characters, log a warning under the `[AI_DEBUG]`
channel. No hard truncation in v1 — model context windows are
generally large enough that the warning is an authoring signal, not
a correctness boundary.

## Why a column on the existing tables, not a separate `scope_prompts` table

- **No multiplicity to model.** A collection has at most one prompt;
  same for a set. A side table would force an extra LEFT JOIN on
  every list/read for no expressive gain.
- **Matches the `ai_providers.system_prompt` precedent.** That column
  is also free-text on the parent row, and the symmetry keeps the
  Pydantic models, the migration shape, and the test patterns
  uniform.
- **Migration is two ALTER TABLE statements.** Smallest possible
  schema delta; idempotent without joining any new tables into the
  existing soft-delete / search-indexing flows.

## Why additive inheritance, not override

- **Composability.** Authors can put "house rules" on the collection
  ("we use a hexagonal architecture lens") and reserve the set
  prompt for narrower context ("this set is the SREv2 platform").
  Override semantics would push authors to copy the collection
  prompt into every set.
- **Discoverability.** A reader of a set's prompt doesn't have to
  guess whether the parent collection's prompt is also in effect —
  it always is.
- **Aligns with how skills will compose** (ADR-151). Skills are
  additive across the hierarchy. Keeping prompts the same avoids two
  different mental models for the two adjacent features.

## Why dedup collection prompts in multi-set asks

A user asking about three sets in the same collection should not
have the collection prompt prepended three times. Dedup is by
collection id; the prompt itself is included once even if two
collections happen to have the same text.

## Consequences

- One new migration (`m047_scope_system_prompts.py`) and its Supabase
  mirror (`m051_scope_system_prompts.sql`).
- Pydantic `CollectionUpdate` / `CollectionResponse` and `SetUpdate` /
  `SetResponse` gain a `system_prompt: str | None` field.
- `update_collection` and `update_set` service functions accept
  `system_prompt` and persist it. Existing callers continue to work
  (parameter is keyword-only with a default).
- A new small module `app/ai/scope_prompts.py` exposes
  `build_scope_prompts(db, set_ids, collection_id)` returning the
  composed prepend text. Returns `""` when no scope has a prompt.
- Composition wiring lands in four places that all read the same
  helper: `router._ask_streaming`, `router._ask_multi_set_streaming`,
  `service.ask_question`, `service.ask_multi_set_question`.
- The MCP `ask` tool benefits automatically — it already forwards
  `collection_id` and `set_ids` to `/api/ai/ask`.
- New ADR-150-related fields surface in the Collection and Set edit
  pages as a textarea below the description field.
- Token-budget warning is observability only; no behaviour change
  beyond the log line in v1.

## Out of scope (deferred)

- **Per-user overrides.** Could be useful ("never use markdown
  tables") but introduces a fourth composition layer and a privacy
  question. Revisit when there's a concrete request.
- **Per-conversation overrides.** A user might want to temporarily
  suppress the scope prompt for a single thread. Solvable with a
  `?ignore_scope_prompt=true` query param later; not needed v1.
- **Prompt templating / variables.** Plain text only for v1. Variable
  substitution (`{{collection.name}}`) is a power-user feature that
  can be added without a schema change.
- **Per-mode prompts.** A future "creation-only" or "discuss-only"
  field could let authors split intent. For v1 the same prompt
  applies in both modes; the model can be told which mode it's in
  via the prompt text.

## See also

- [ADR-093](ADR-093-AI-Q-And-A.md) — original Ask Iris architecture.
- [ADR-102](ADR-102-Collections.md) — collections data model.
- [ADR-123](ADR-123-Anonymous-AI-Asks.md) — anonymous asker rules.
- [ADR-132](ADR-132-Layered-Creation-Prompts.md) — the prompt-layering
  precedent we extend with scope prepend.
- [ADR-151](ADR-151-DB-Resident-Skills-Progressive-Disclosure.md) —
  Skills, the companion feature that uses the same scope hierarchy.
- [SPEC-150-A](specs/SPEC-150-A-Scope-System-Prompts.md) — schema,
  composition rules, endpoint diffs, edit-page wiring, test plan.
