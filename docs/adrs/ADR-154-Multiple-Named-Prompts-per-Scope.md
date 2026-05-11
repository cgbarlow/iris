# ADR-154: Multiple named prompts per scope (Collection and Set)

Status: Proposed (2026-05-11)
Extends: [ADR-150](ADR-150-Scope-Level-System-Prompts.md), [ADR-152](ADR-152-MCP-Prompts-Capability-for-Scope-System-Prompts.md), [ADR-153](ADR-153-Drop-Redundant-iris-Prefix-From-MCP-Prompt-Names.md)

## Context

ADR-150 added a single `system_prompt` per Collection and per Set. It
auto-applies via the Ask Iris composition pipeline and is also
surfaced via the MCP `prompts` capability (ADR-152, ADR-153) so Claude
clients can see it explicitly. That single slot is exactly right for
"house rules" content that should always travel with the scope.

What's missing is the ability to author **multiple named directives**
on the same scope. A real example: the DoView Book Set already has a
working `system_prompt`, and the user also wants to host two distinct
authored directives on the same Set — one for outcomes-theory text
responses and one for diagram retrieval. Each is an entire prompt of
its own (~250 lines), each is invoked on its own turn, and each must
appear in the Claude prompt picker as a discrete entry. Squeezing both
into a single `system_prompt` would force the model to pick which mode
applies per turn, which is exactly the kind of in-prompt branching
that user-pickable named prompts exist to avoid.

This ADR also has a non-goal worth naming up front: it is **not** the
"Skills" feature originally sketched in issue #88. The name "skill"
in Anthropic's vocabulary now means a model-side auto-trigger
mechanism backed by local files. The MCP `prompts` capability is
spec-mandated **user-controlled**, so a server-side directive
delivered over MCP is a *prompt*, not a skill, no matter what we call
it. Calling these "skills" would only confuse users who have
expectations from Claude Code's local skill system.

## Decision

**Add a new `prompts` table holding zero-or-more named prompts per
scope.** The table is purely additive — the existing
`collections.system_prompt` and `sets.system_prompt` columns and
their auto-apply behaviour are unchanged.

```sql
CREATE TABLE prompts (
  id           TEXT PRIMARY KEY,
  scope_type   TEXT NOT NULL CHECK (scope_type IN ('collection','set')),
  scope_id     TEXT NOT NULL,
  name         TEXT NOT NULL,        -- ^[a-z][a-z0-9-]{0,63}$
  description  TEXT NOT NULL,        -- 1..1024 chars (shown in picker)
  body         TEXT NOT NULL,        -- 1..256000 chars
  created_at   TEXT NOT NULL,
  updated_at   TEXT NOT NULL,
  created_by   TEXT,
  UNIQUE (scope_type, scope_id, name)
);
```

Named prompts are surfaced via the **same MCP `prompts` channel** that
ADR-152 / ADR-153 established for scope `system_prompt`. The
`/api/prompts/scope-index` endpoint and `mcp/src/iris_mcp/prompts.py`
both grow to include named-prompt entries alongside the existing
system_prompt entries. Naming convention (post-v5.8.5, no `iris:`
prefix per ADR-153):

| Kind | MCP prompt name |
|---|---|
| Scope `system_prompt` (existing) | `set:<uuid>` / `collection:<uuid>` |
| Named prompt (new) | `set:<uuid>:<name>` / `collection:<uuid>:<name>` |

Claude Code clients prepend the server name, so users see them in the
picker as `/iris:set:<uuid>` and `/iris:set:<uuid>:<name>`.

**Inheritance is additive, mirroring ADR-150.** A Set sees its own
named prompts plus its parent Collection's named prompts. Same name
on Set and Collection: the Set entry shadows the Collection entry
(scoped uniqueness is per `(scope_type, scope_id, name)`, so this
only matters at MCP-listing time).

**No auto-apply.** Named prompts never participate in the Ask Iris
server-side composition pipeline. Only `system_prompt` does. This
preserves the existing Iris discussion / create flow behaviour
exactly. Auto-apply for one slot per scope is the right ceiling —
users authoring multiple directives explicitly want the picker, not
silent prepending.

**Endpoints** (all under `/api/named-prompts`, parallel to
`/api/prompts` rather than nested):

- `GET    /api/named-prompts?scope_type=&scope_id=` — list scoped
- `GET    /api/named-prompts/by-scope?collection_id=&set_id=` — effective list (own + inherited)
- `POST   /api/named-prompts` — create
- `GET    /api/named-prompts/{id}` — detail
- `PUT    /api/named-prompts/{id}` — update description and/or body; scope and name immutable
- `DELETE /api/named-prompts/{id}`

Validation on create / update: `name` must match
`^[a-z][a-z0-9-]{0,63}$`; `description` 1..1024 chars; `body`
1..256_000 chars. The 256k body cap is generous — covers the longest
realistic prompt by a wide margin.

**Anonymous read posture** matches ADR-150: the list endpoint and the
extended `/api/prompts/scope-index` are anonymous-readable (the prompt
content is metadata the asker can already see in the scope's edit
screen). Writes require authentication.

## Why a separate table, not a JSON array on the scope row

- **Real multiplicity now.** Unlike `system_prompt` (always at most
  one per scope, justifying the column-on-existing-table choice in
  ADR-150), named prompts have unbounded cardinality. A side table is
  the right shape.
- **Per-row CRUD without read-modify-write contention.** The web GUI
  edits one prompt at a time. A JSON array would force re-serialising
  the whole array on every edit, racing concurrent edits.
- **Foreign-key-style scoping with a cheap index.** `(scope_type,
  scope_id)` is the natural index; uniqueness on `(scope_type,
  scope_id, name)` enforces the picker's "no duplicate names per
  scope" requirement at the database layer.
- **Symmetry with how Skills would have been stored** under issue 88.
  This is the same shape; only the framing changes.

## Why retain `system_prompt` unchanged

- **The user explicitly asked.** It still applies for Iris's internal
  AI discussion / create flows, where one always-on directive is
  exactly the right primitive.
- **Migration safety.** Existing scopes with non-empty `system_prompt`
  keep working unchanged. No data move, no behaviour delta for
  current users.
- **Different slot, different purpose.** Auto-apply (`system_prompt`)
  and user-pick (named prompts) are not interchangeable. Conflating
  them would require a per-prompt `auto_apply` flag, deferred below.

## Why no auto-apply for named prompts

- **Picker-invocation is the whole point.** If the user wanted the
  prompt to apply silently they'd put the content in `system_prompt`
  instead.
- **Context-budget hygiene.** Auto-applying multiple unrelated
  directives every turn would balloon `system_content` quickly.
  ADR-150's 16k soft warning would fire constantly.
- **Avoids prompt-mode-switching.** Two unrelated directives
  auto-applied together force the model to figure out which one is
  relevant per turn — exactly the problem named prompts exist to
  avoid.

A future `auto_apply` boolean is left as a deferred extension below
if a real use case shows up.

## Why surface via the same MCP `prompts` channel, not a new capability

- **Spec compliance + zero new client work.** Named prompts are
  user-controlled directives — the exact intent of the MCP `prompts`
  capability. No new MCP capability is needed.
- **Consistent UX.** Users see all scope-attached directives —
  system_prompt and named prompts alike — in the same prompt picker,
  alongside each other.
- **No prompt-injection risk above what ADR-152 already analysed.**
  Same channel, same trust model, same provenance preamble.

## Why no prefix in the name

ADR-153 dropped the `iris:` prefix because clients double-prefix.
Named prompts inherit the same naming hygiene: no `iris:`, just
`set:<uuid>:<name>` / `collection:<uuid>:<name>`. The colon between
UUID and name is the natural separator since UUIDs don't contain
colons; the regex is unambiguous.

## Consequences

- One new SQLite migration `m048_named_prompts.py` and one Supabase
  mirror `m052_named_prompts.sql`. Both idempotent (`CREATE TABLE IF
  NOT EXISTS`, guard the index too).
- New backend module `app/named_prompts/{models,service,router}.py`.
  Module is parallel to the existing `app/prompts/` module (which
  owns the scope-index endpoint), keeping the latter focused.
- `app/prompts/router.py:list_scope_prompts_endpoint` extends to
  include named-prompt entries; the response model gains an
  `entry_kind: Literal["system_prompt", "named_prompt"]` discriminator
  and a nullable `prompt_name` field on each entry.
- `mcp/src/iris_mcp/prompts.py:_NAME_RE` extends from
  `^(set|collection):([0-9a-f-]{36})$` to also match
  `^(set|collection):([0-9a-f-]{36}):([a-z][a-z0-9-]{0,63})$`.
  `list_prompts` and `get_prompt` learn to dispatch on whether a
  third capture group is present. `_preamble` extends to include the
  prompt name when one is present (`Loaded from Iris {Label}
  "{scope_name}" — prompt "{prompt_name}" ({url}):\n\n{body}`).
- `iris-client` gains a `list_named_prompts()` method (or extends the
  existing `list_scope_prompts()` to return both kinds — TBD in
  SPEC-154-A).
- Web GUI: `/sets/[id]` and `/collections/[id]` edit pages each gain
  a "Prompts" section below the existing "System prompt" textarea,
  offering per-row CRUD on named prompts.
- **No changes** to `app/ai/scope_prompts.py` or `app/ai/service.py`.
  Named prompts are deliberately outside the auto-apply pipeline.
- **No changes** to the existing `system_prompt` columns, MCP names
  for scope `system_prompt`, or any other v5.8.x behaviour.

## Out of scope (deferred)

- **Per-prompt `auto_apply` flag.** Tempting unification with
  `system_prompt` (just promote a named prompt to auto-apply), but
  introduces composition-order, dedup, and budget questions that
  aren't worth solving until a real use case appears. The current
  one-auto-apply-slot-per-scope ceiling is sufficient.
- **Argument templating** (`{{set.name}}` etc.). A picker prompt that
  takes named arguments would be useful for parametric workflows.
  Not needed for the DoView Book use case; can be added without
  schema change later.
- **Per-user named prompts.** Personal prompts attached to a user
  rather than a scope. Different privacy model; revisit on demand.
- **Skill bundles / multi-file resources.** Issue 88 Phase 3
  envisaged file attachments to skills. This ADR addresses single-
  body prompts only.
- **Local-file delivery** (writing prompts down to `.claude/skills/`
  or similar). Out of architectural scope for this ADR — would
  require a CLI / sync mechanism not present today and would
  conflate server-controlled and client-controlled lifecycles.

## See also

- [ADR-150](ADR-150-Scope-Level-System-Prompts.md) — scope
  `system_prompt` foundation; the table, composition pipeline, and
  inheritance pattern this ADR extends.
- [ADR-151](ADR-151-MCP-Boundary-Strips-Scope-System-Prompts.md) —
  prompt-injection defence at the MCP boundary; same trust model
  applies to named prompts.
- [ADR-152](ADR-152-MCP-Prompts-Capability-for-Scope-System-Prompts.md)
  — the MCP `prompts` channel itself; this ADR rides on the same
  capability.
- [ADR-153](ADR-153-Drop-Redundant-iris-Prefix-From-MCP-Prompt-Names.md)
  — current naming convention with no `iris:` prefix.
- [Issue #88](https://github.com/cgbarlow/iris/issues/88) — original
  "Skills" roadmap; this ADR fulfils the practical authoring need
  (multiple named directives per scope) while explicitly rejecting
  the "Skills" framing for the reasons in Context.
- [SPEC-154-A](specs/SPEC-154-A-Named-Prompts.md) — schema, endpoint
  shapes, MCP wiring, edit-page wiring, test plan.
