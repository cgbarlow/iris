# ADR-151: MCP boundary strips scope `system_prompt`

Status: Accepted (2026-05-11)

## Context

v5.8.0 (ADR-150) added a free-text `system_prompt` field to Collections
and Sets. The field is consumed correctly in three places:

- **Web GUI** edit screens (`/collections/[id]`, `/sets/[id]`) — authors
  read and write it via the existing REST endpoints.
- **Iris backend ask path** (`/api/ai/ask`) — the field is composed
  into the LLM's system message in `build_scope_prompts`. The model
  sees it as part of its own system context, not as tool data.
- **Iris MCP `ask` tool** — same backend code path, same result.

What broke: the *four other* MCP tools that return Set or Collection
data — `list_sets`, `get_set`, `list_collections`, `get_collection` —
serialise the full response model and pass `system_prompt` straight
through to the MCP client as a JSON field. UAT testing surfaced this
within hours: Claude Desktop, presented with a `system_prompt` field
inside a tool's JSON response, correctly treats it as untrusted data
and announces "this set has a system prompt attached … I'm flagging
it rather than silently obeying."

This is **Claude's prompt-injection defense working as designed.**
Tool outputs are data, not instructions. If a malicious actor attached
a `system_prompt` to a resource, the model must not silently obey it.
The defense applies even when the author is legitimate (Iris has no
way to convey "this came from a trusted scope owner" through the
tool-response channel; any such marker would itself be untrusted data).

## Decision

**The Iris MCP server must redact `system_prompt` from every tool
response that crosses the MCP boundary.** Authoring still flows
through the REST endpoints unchanged. Scope prompts continue to apply
silently via the `ask` MCP tool (the backend injects them
server-side). The spec-compliant channel for delivering scope-attached
directives to a Claude Desktop conversation is the MCP `prompts`
capability, which ADR-152 introduces.

Implementation: the strip lives in the three serialisation helpers in
`mcp/src/iris_mcp/links.py` — `with_web_url`, `with_web_urls_list`,
`with_web_urls_search`. Every Set- or Collection-returning tool
already routes through these helpers for web-URL decoration; the
strip is added inside the existing JSON parse/serialise round-trip,
adding one `dict.pop("system_prompt", None)` call per item. The
strip runs *unconditionally* — independent of whether `IRIS_WEB_URL`
is configured.

The list of stripped keys lives in a module-level constant
`_STRIPPED_KEYS = ("system_prompt",)`. Future redactions (e.g.,
forthcoming MCP-sensitive fields on other entities) extend the tuple
rather than copy-pasting strip logic into every handler.

## Why strip at the helper layer

Three options were considered:

1. **Backend response models exclude `system_prompt`.** Rejected — the
   web GUI authoring flow needs the field on the same endpoints.
2. **iris-client filters the field.** Rejected — iris-client is a
   shared library used by surfaces that legitimately need the field
   (e.g., a hypothetical Python admin CLI).
3. **MCP server strips at the egress boundary.** Accepted — the only
   layer where "MCP" is the meaningful constraint and where the rest
   of the system stays untouched. Single edit, durable across future
   handlers that follow the same pattern.

Within option 3, the strip could live in each MCP handler (`_list_sets`,
`_get_set`, etc.) or in the shared `with_web_url*` helpers. The
helpers were chosen for durability: every Set- or Collection-returning
tool today already calls them, and any new tool following the same
pattern will inherit the strip automatically. Catches future leaks
without future code review having to flag them.

## Consequences

- Single small diff in `mcp/src/iris_mcp/links.py` (adds one private
  helper, three calls).
- No changes to handlers, iris-client, or the backend.
- Future tools returning Set or Collection data inherit the strip for
  free as long as they route through `with_web_url*`. A handler that
  bypasses the helpers would re-introduce the leak; the pattern is
  consistent enough that the chance is low, but worth flagging in code
  review.
- The MCP `ask` tool continues to apply prompts server-side
  (unchanged) — it doesn't return Set/Collection JSON; it returns a
  text answer.
- "Silent automatic application of scope prompts inside a Claude
  Desktop conversation outside of `ask`" is explicitly **not** achievable
  through this fix. ADR-152 introduces the MCP `prompts` channel for
  that use case.

## See also

- [ADR-095](ADR-095-RLS-Posture.md) — analogous "defence-at-the-boundary"
  principle for Supabase RLS.
- [ADR-150](ADR-150-Scope-Level-System-Prompts.md) — original feature
  that introduced the leaking field.
- ADR-152 — the spec-compliant alternative channel for delivering
  scope prompts to MCP clients.
- [SPEC-151-A](specs/SPEC-151-A-MCP-System-Prompt-Strip.md) — the
  helpers, the test plan, and the future-redaction extension point.
