# ADR-168: Remove the `ask` tool from the MCP surface

Status: Accepted (2026-05-13)
Supersedes: parts of [ADR-156](ADR-156-MCP-System-Context-Data-Passthrough.md)
Extends: [ADR-167](ADR-167-Orient-Directive-In-Tool-Response.md)

## Context

The `ask` MCP tool routes a question through Iris' server-side AI (`/api/ai/ask`). It was added when the canonical assumption was that MCP clients didn't necessarily have their own LLM — a CLI script could call `ask` and let Iris do the reasoning.

That assumption no longer holds for the dominant consumer pattern. claude.ai, Claude Desktop, Claude Code, and Cursor all have a capable LLM as the *primary* runtime; the MCP server is a *data adapter*. Routing the model's question to Iris' server-side AI is:

- **Redundant**: the client's own model is already a top-tier LLM. Funnelling through a second AI adds latency without adding capability.
- **Confusing**: the user picks a menu option in claude.ai expecting the local model to do the work; instead claude.ai calls `ask`, which spawns a *different* conversation on the Iris backend with its own context, and surfaces a synthesised answer that doesn't match claude.ai's tone or follow-through.
- **Wrong for analyses**: issue #119 v6.0.7 testing surfaced a concrete failure — the user selected "Generate a new DoView outcomes-theory analysis", and the model called `ask` to do it. The analysis came back from Iris' AI in a different voice, with no path for the user to follow up via the local AI's normal capabilities. The user-intent was clearly "the AI I'm chatting with should do this", not "delegate to a different AI."

Cross-scope question-answering — the original use case for `ask` — is fulfilled equally well by the local model reading the data directly through the read-only MCP tools (`search`, `get_diagram`, `get_element`, `get_package`, `get_set`, `get_collection`, `list_*`, `package_hierarchy`). The local model can walk the data, synthesise, and answer in its own voice.

## Decision

Remove the `ask` tool from iris-mcp's tool surface:

- Drop the `Tool(name="ask", ...)` entry from `tool_definitions()`.
- Drop the `_ask` dispatch handler.
- Drop the v5.x `TestAsk` test class. Pin the removal with two regression assertions: `ask` is not in `tool_definitions()`; dispatching to `"ask"` returns the standard unknown-tool error.

Update the orient wrapper in `links.py` to explicitly steer the model:

- Cross-package / cross-set / cross-collection questions: "answered by YOUR reasoning over data you read via the read-only MCP tools. There is no 'ask Iris AI' tool — it has been removed."
- DoView analyses + visual outcomes maps: "drafted by YOU using your own reasoning, following the creation cascade from `get_response_prompt(purpose='creation_format', ...)`. Persist via `create_diagram` (single) or `apply_diagram_creation` (batch). Do NOT look for a separate AI-analysis tool — none exists."

Update the canonical Outcomes Theory Book `mcp_system_context` paste-doc to match — option 2 broadens from "cross-package via Iris AI" to "cross-package, cross-set, or cross-collection" and drops the `mcp__iris__ask` reference; option 3 drops the `→ call create_diagram` implementation tag. The admin pastes the new content into `/admin/settings/ai`.

## What about iris-client?

`iris-client.IrisClient.ask(...)` stays. iris-client is a Python SDK that's used outside the MCP context too — by the iris-mcp `ask` handler we're removing, but also potentially by scripts, jobs, the iris-cli, and any future non-MCP consumer. Removing the SDK method would be a breaking change unrelated to the MCP surface concern.

The MCP boundary is the right place to draw the line: clients that have their own LLM use the SDK's read-only methods through MCP; clients that need Iris AI inference can use the SDK directly outside MCP. v6.0.8 enforces that boundary.

## What about `apply_diagram_creation`?

Kept. The `apply_diagram_creation` MCP tool persists a *locally-drafted* diagram bundle — it's the persistence step after the local AI runs the creation cascade. No server-side AI involved.

Its description previously read "Use after calling `ask` with mode='creation' and receiving a diagrams JSON string." — that referenced the removed `ask` path. The v6.0.8 description rewrites it: "The client drafts the diagrams JSON (one entry per diagram, matching the creation_format cascade...) and posts it here for persistence. Prefer `create_diagram` for single-diagram creation; this tool is for batch saves."

## Why not feature-gate `ask` (e.g. expose only when an env var is set)?

- The wrong-routing failure mode is severe enough that defaulting to "exposed" is wrong for the dominant consumer pattern (capable-LLM clients).
- Any consumer that genuinely needs Iris AI inference can call `iris-client` directly. No need to feature-gate the MCP tool.
- Less code is better than gated code.

## Consequences

- Six lines fewer in `tool_definitions()`; ten lines fewer in dispatch handlers; one fewer registered tool in the iris-mcp surface.
- claude.ai (and any other capable-LLM MCP client) no longer has the option to delegate analysis to Iris' AI. The local model does the work directly. Tone and follow-through stay consistent through the conversation.
- The orient wrapper picks up two new short paragraphs explicitly steering the model on how to fulfil cross-scope questions and analysis menu options.
- Existing live `mcp_system_context` bodies that reference `mcp__iris__ask` should be re-pasted from `docs/prompts/doview-book-mcp-system-context.md` to drop the obsolete tool reference and the `→ call create_diagram` implementation tag.
- Two existing tests (the v5.x `TestAsk` class and one wrapper assertion mentioning `mcp__iris__ask`) updated. One new test class (`TestAskRemoved`) and one new wrapper assertion (`TestWrapperStepersAnalysisToLocalAI`) pin the removal.
- Version bump v6.0.7 → v6.0.8. Patch-level (tool removal does change the MCP surface, but the orient wrapper transitions the affordance smoothly — no caller of `ask` is left without a path).

## See also

- [ADR-167](ADR-167-Orient-Directive-In-Tool-Response.md) — the orient wrapper this ADR strengthens.
- [`docs/prompts/doview-book-mcp-system-context.md`](../prompts/doview-book-mcp-system-context.md) — the canonical paste-ready menu (updated to v6.0.8 wording).
- Issue [#119](https://github.com/cgbarlow/iris/issues/119) — six-revision fix history culminating in this menu-and-tool cleanup.
