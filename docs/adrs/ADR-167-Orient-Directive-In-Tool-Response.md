# ADR-167: Embed the orient directive in MCP tool responses

Status: Accepted (2026-05-13)
Extends: [ADR-156](ADR-156-MCP-System-Context-Data-Passthrough.md), [ADR-163](ADR-163-Centralised-MCP-Server-Instructions.md), [ADR-165](ADR-165-MCP-Server-Instructions-Over-HTTP-Transport.md), [ADR-166](ADR-166-MCP-Server-Instructions-TTL-Refresh.md)

## Context

ADR-163 (v5.18.0) lifted the universal ORIENT-FIRST protocol into the MCP `Server(instructions=...)` channel. The intent was DRY: one server-wide body, surfaced via `InitializeResult.instructions`, instead of repeating the protocol in every authored scope's `mcp_system_context`.

ADR-165 (v6.0.4) wired the channel through the HTTP transport so claude.ai actually received the body. ADR-166 (v6.0.5) added a TTL refresh so admin edits propagated without a redeploy. Both verified-working on the wire:

```bash
$ curl iris-mcp.onrender.com/info
{"version":"6.0.5", ...}

$ curl -X POST iris-mcp.onrender.com/ -d '{"method":"initialize",...}'
{"result":{"instructions":"... INVOKE the structural-overview call ... TOC is mandatory, not optional ...", ...}}
```

But claude.ai's hosted MCP integration **still does not invoke `package_hierarchy` and still paraphrases the menu**, even with the strong canonical body served. Verified across three diagnostic sessions in issue #119 testing.

The conclusion: **claude.ai does not reliably surface `InitializeResult.instructions` to the model's context.** Whatever its hosted-connector implementation does with the field, the model's behaviour in tool-response handling does not change as the field changes. The whole ADR-163 architecture is broken for claude.ai specifically.

What the model **does** consistently read:

1. **Tool descriptions** — every tool's description text is sent to the model. Verified by the v6.0.3 tool-name regression class (`iris_package_hierarchy` typo broke tool resolution because the model used the wrong name from the description).
2. **Tool response bodies** — every JSON field returned by a tool is read. Verified by every working flow in v5.x and the partial mcp_system_context reading in v6.x (the model paraphrased the menu, demonstrating it read that field).

The fix has to put the orient directive somewhere claude.ai *definitely* gives the model. Tool response bodies are the only reliable channel.

## Decision

**Embed the orient directive directly into `mcp_system_context` at the MCP transport boundary**, prepended to whatever admin-authored content the field carries. The directive is hardcoded in `iris-mcp` source (`links.py`) — it doesn't need admin editing because it's the universal protocol, not scope-specific content.

Concretely, when `iris-mcp` returns a search / list / get response that contains a set or collection with non-empty `mcp_system_context`, the field gets wrapped:

```text
[ORIENT — DO THESE STEPS BEFORE RESPONDING TO THE USER]
This scope is a set (set_id="33032180-d77a-4ce4-88cf-b49cd643e093"). The
orient sheet below names a structural-overview call AND a numbered menu.
Before responding to the user, you MUST, in order:
  1. Briefly describe the scope (one sentence based on its name and
     description).
  2. INVOKE the structural-overview call named below, passing this
     scope's set_id="33032180-d77a-4ce4-88cf-b49cd643e093". The TOC is
     mandatory, not optional. If the named tool is not currently in
     your toolset, request a tool-load first — do NOT skip this step.
  3. Offer the menu options below via AskUserQuestion (if your client
     supports it) or a numbered list, IN ORDER, VERBATIM. Do not
     paraphrase, do not silently drop options.

Do NOT ask "want me to load the table of contents?" — load it yourself.
Do NOT respond with just the menu and skip the TOC.

---

<original admin-authored mcp_system_context content>
```

Key design choices:

- **Pre-fill the scope's id** in the tool-call signature (`set_id="33032180-..."`) so the model has the exact call ready. No inference needed; the model just executes.
- **Negate the failure modes explicitly** ("DO NOT ask 'want me to load it?'", "DO NOT paraphrase"). Mirrors how v5.x content worked in practice.
- **Apply at the iris-mcp transport boundary** (`links.py`), not at the backend search-service layer. Keeps the architectural separation: backend is data, iris-mcp is presentation. Future MCP-transport changes (e.g. a non-HTTP variant) inherit the wrapper for free because it lives at the shared serialisation point.
- **Idempotent**. The wrapper checks for its own marker prefix; reprocessing the same payload doesn't double-wrap. Safe under any in-place mutation order.
- **Always-on, regardless of `IRIS_WEB_URL`**. The web-URL decoration is gated on the env var; the orient wrapper is universal — local dev needs it as much as production.
- **Only sets and collections**. Other entity kinds don't carry scope-orient semantics. Even if a rogue server populated the column on a diagram, the wrapper is a no-op there.

## Why not back-port orient into per-scope `mcp_system_context`

- That regresses ADR-163's DRY win — every authored scope (Outcomes Theory Book, future Set/Collection contributions) would carry the same boilerplate.
- Code-level wrapping centralises the orient text in one place (`links.py`), edits propagate to all scopes on the next iris-mcp deploy.
- Admin edits to `mcp_system_context` stay focused on the scope-specific menu, which is where admin expertise actually matters.

## Why not inject the orient into the search tool's *description*

- Considered. claude.ai definitely reads tool descriptions. But tool descriptions are static code constants registered at server-construction; admin edits to the orient body wouldn't propagate without an iris-mcp redeploy (re-introducing the problem ADR-166 just solved).
- The current orient body is delivered via the v6.0.5 TTL refresh, so the wrapper text — pre-filled with the scope id at response time — captures admin intent indirectly through the menu it wraps.

## Why keep `Server.instructions` wired at all

- Other MCP clients (Claude Desktop, Claude Code, Cursor, future hosted-MCP clients) **do** appear to surface `InitializeResult.instructions` reliably. The ADR-163/165/166 channel works for them. Removing it would regress those.
- The tool-response wrapper is **belt-and-suspenders**: claude.ai gets the orient via the wrapper; other clients get it via both (the wrapper is just additional reinforcement).
- If a future claude.ai update starts honouring `InitializeResult.instructions` properly, the wrapper is still correct — the model just sees the directive twice, which is fine.

## Consequences

- One new function `wrap_orient(item, kind)` in `mcp/src/iris_mcp/links.py` (~50 LOC).
- `with_web_url`, `with_web_urls_list`, `with_web_urls_search` each call `wrap_orient` for every set/collection in their payload. Unconditional on `IRIS_WEB_URL` (the wrapper is independent of web-URL decoration).
- ~600 chars added to each set/collection result's `mcp_system_context`. Search returning 10 sets adds ~6 KB. Negligible relative to total response size.
- One existing test class (`test_links_passes_mcp_system_context.py::TestMcpSystemContextPassesThrough`) updated from "equal to original" to "starts with marker AND ends with original". Behaviour intent is preserved; assertion shape changes.
- One new test file `test_links_orient_wrapper.py` with 18 cases covering the wrapper's primitives, search/list/single-entity surfaces, idempotency, and IRIS_WEB_URL independence.
- Version bump v6.0.5 → v6.0.6. Patch-level (operator-experience fix for claude.ai compatibility, no API surface change).

## Verification

- Local: `pytest mcp/tests/` green — 154/154.
- Post-deploy: claude.ai opens the Outcomes Theory Book → TOC auto-loads, four-option `AskUserQuestion` widget. Matches the 5.x.previous flow from issue #119.

## See also

- [ADR-163](ADR-163-Centralised-MCP-Server-Instructions.md) — original "centralise orient in Server.instructions" decision.
- [ADR-165](ADR-165-MCP-Server-Instructions-Over-HTTP-Transport.md) — wired Server.instructions through HTTP.
- [ADR-166](ADR-166-MCP-Server-Instructions-TTL-Refresh.md) — kept Server.instructions fresh.
- [SPEC-167-A](specs/SPEC-167-A-Orient-Directive-In-Tool-Response.md) — wrapper format, injection points, test plan.
- Issue [#119](https://github.com/cgbarlow/cgbarlow/iris/issues/119) — original regression report and four-revision fix history (v6.0.4 → v6.0.6).
