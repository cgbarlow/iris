# ADR-152: MCP `prompts` capability for scope system prompts

Status: Accepted (2026-05-11)

## Context

v5.8.0 (ADR-150) added a free-text `system_prompt` field on Collections
and Sets. The web GUI applies it server-side at ask time; the MCP `ask`
tool inherits the same composition. v5.8.2 (ADR-151) closed the leak
where the field travelled as MCP tool data and triggered Claude
Desktop's prompt-injection defense.

That fix removes a UX paper-cut but leaves a real capability gap:
**there is no way for a Claude Desktop user (chatting with the Claude
Desktop model directly, with the Iris MCP server connected) to invoke
a scope-attached system prompt as authoritative context for the
conversation.** The original Phase 2 plan assumed MCP tool data could
carry skill/prompt content that Claude would follow silently. ADR-151
formalised why that won't work — by design.

What does work, and is spec-defined, is the **MCP `prompts` capability**:
`prompts/list` enumerates server-curated prompts; `prompts/get` returns
a sequence of messages the client renders into the conversation. The
key behavioural difference from `tools`: a prompt loaded via this
capability arrives as a message attributed to the user. The model
treats it as a user-authored directive, not as untrusted tool output.
No prompt-injection flagging; full authority over the rest of the
conversation.

## Decision

**Surface every Iris Collection / Set that has a non-empty
`system_prompt` as an MCP prompt named `iris:<scope_type>:<uuid>`.**
Backend exposes a thin scope-prompt index endpoint
(`GET /api/prompts/scope-index`). iris-client provides
`list_scope_prompts()`. The MCP server registers `@server.list_prompts()`
and `@server.get_prompt()` decorators backed by a new
`iris_mcp/prompts.py` module.

Specifics:

1. **Name format**: `iris:set:<uuid>` and `iris:collection:<uuid>`.
   UUIDs are stable across renames, exports, and re-imports. The
   human-friendly scope name lives in the prompt's `description`
   field (which is what Claude Desktop's picker actually displays).
2. **Body shape**: one `role: user` `PromptMessage` per prompt. Content
   is the scope's `system_prompt` body verbatim, preceded by a
   provenance preamble: `Loaded from Iris {Set|Collection} "<name>"
   (<web_url>):\n\n` (URL only when `IRIS_WEB_URL` is configured).
3. **Single round-trip**: the iris-client `list_scope_prompts()`
   response carries the body inline. `prompts/get` resolves from the
   already-fetched index rather than making a second backend call.
   At Iris's scope cardinality (tens to hundreds, not millions) this
   is the simpler design and avoids a second network hop in the hot
   path.
4. **Arguments**: empty in v1. Variable substitution (templating) is
   a future enhancement that would not change the URI shape.
5. **Auth posture**: the scope-index endpoint is anonymous-readable,
   matching `list_collections` and `list_sets`. Authoring still
   requires auth.

## Why MCP `prompts`, not MCP `tools`

The MCP spec explicitly distinguishes the two:

- **Tools** are model-invoked; their output is data. Claude correctly
  treats tool data as untrusted (ADR-151).
- **Prompts** are user-invoked (or template-invoked) and arrive in the
  conversation as messages that came from outside the tool boundary.
  Claude treats them as user-authored framing.

Scope-attached system prompts are conceptually "the author of this
scope wants the assistant to behave this way" — exactly the framing
prompts capture. Tools are the wrong channel for this content.

## Why a dedicated endpoint vs reusing `list_sets` + `list_collections`

The MCP server could iterate the existing list endpoints and filter
client-side. Rejected because:

- Pagination, thumbnails, counts — all the noise of the full
  list-endpoints — would have to be downloaded per `prompts/list`
  call, which Claude Desktop hits eagerly.
- The leak fix in ADR-151 strips `system_prompt` from those endpoints
  when called via MCP — making them useless for this purpose anyway.
- A dedicated endpoint can return exactly the shape the MCP server
  needs (name, scope_type, scope_id, scope_name, description, body)
  with no transformation step.

## Why one user message vs splitting into system / user

The MCP SDK's `PromptMessage` supports `role: "user"` and
`role: "assistant"` but not `role: "system"`. Loaded prompts function
as if the user typed them at session start. The provenance preamble
makes the source explicit so the model treats the directive as
authoritative without confusing it for end-user input.

## Consequences

- Two layers of new code: backend module + iris-client method + MCP
  module. All small and isolated. Net ~250 lines including tests.
- No frontend changes — authoring already works via the v5.8.0 edit
  screens.
- The MCP `ask` tool is unaffected; it still composes prompts
  server-side. Users have two valid paths for using a scope's prompt
  via MCP:
  - **Server-side AI**: call `ask` — Iris's configured provider does
    the reasoning with the prompt applied.
  - **Client-side AI** (this ADR): invoke the prompt explicitly in
    Claude Desktop; Claude does the reasoning with the prompt as
    user-authored framing.
- Scope deletion (or clearing the system_prompt) removes the prompt
  from the index automatically — the picker self-cleans on next
  `prompts/list`. No GC pass needed.
- The Phase 2 / Phase 3 plan around DB-resident skills can reuse this
  same channel: each skill becomes an additional prompt entry. No
  new MCP capability needed for skills.

## Out of scope (deferred)

- **Argument templating** — letting prompts accept user input
  (e.g., a query string). Trivial to add later; not blocking the
  scope-prompt use case.
- **Multiple system_prompts per scope** — still 1:1 with the
  underlying field. Skills are the right channel for "many directives
  per scope".
- **Filtering by user / scope visibility** — Iris's authentication
  model already treats Collections and Sets as authoring-public.
  When that changes, the scope-prompt index inherits the access
  policy from the underlying scope.
- **Prompt search / fuzzy match** — Claude Desktop's picker provides
  its own filtering UX. No need for server-side search.

## See also

- [ADR-150](ADR-150-Scope-Level-System-Prompts.md) — the feature that
  introduced `system_prompt` on Collections and Sets.
- [ADR-151](ADR-151-MCP-Boundary-Strips-Scope-System-Prompts.md) — why
  the field cannot travel as MCP tool data.
- [SPEC-152-A](specs/SPEC-152-A-MCP-Prompts-Capability.md) — endpoint
  shape, MCP wiring, error semantics, test plan.
