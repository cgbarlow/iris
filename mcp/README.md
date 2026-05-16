# iris-mcp

Stdio MCP server for Iris. Wraps the HTTP API via
[`iris-client`](../iris-client/README.md) so AI agents (Claude Desktop,
Claude Code, Cursor, custom agents) can use Iris as a knowledge and
modelling resource.

See [ADR-131](../docs/adrs/ADR-131-MCP-Server-Architecture.md) and
[SPEC-131-A](../docs/adrs/specs/SPEC-131-A-MCP-Server.md).

## Install

```sh
uv tool install --from . iris-mcp
```

Or from a repo URL:

```sh
uv tool install "git+https://github.com/cgbarlow/iris#subdirectory=mcp"
```

## Configure an MCP client

iris-mcp can run in three shapes depending on what your MCP client
supports. Pick **one** of the following blocks and paste it into your
client's MCP config file
(`claude_desktop_config.json` / `~/.claude/mcp.json` /
`.cursor/mcp.json`). All three reach the same `iris-mcp` server and
expose the same tools / resources / prompts; they differ only in
transport.

### Option A — stdio over `mcp-remote` (currently recommended for Claude Desktop)

```json
{
  "mcpServers": {
    "iris": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://iris-mcp.onrender.com"]
    }
  }
}
```

Bridges the remote Streamable HTTP server to a local stdio process via
the [`mcp-remote`](https://www.npmjs.com/package/mcp-remote) npm
package. Works in **every** MCP client that supports stdio MCP —
including Claude Desktop builds that haven't yet exposed prompts UI
for direct-HTTP MCP servers. Requires Node available on `PATH` for
the `npx` invocation.

For authenticated calls, add an `Authorization` header:

```json
{
  "mcpServers": {
    "iris": {
      "command": "npx",
      "args": [
        "-y", "mcp-remote", "https://iris-mcp.onrender.com",
        "--header", "Authorization: Bearer iris_pat_..."
      ]
    }
  }
}
```

The scope-prompt index is anonymous-readable, so prompts work without
a token; tools like `search` or `ask` require auth.

### Option B — direct HTTP (Claude Code / Claude.ai web / recent Claude Desktop)

```sh
claude mcp add --transport http iris https://iris-mcp.onrender.com
```

Or for Claude.ai web: Settings → Connectors → Add Custom Connector →
URL `https://iris-mcp.onrender.com`. Both clients fully support the
HTTP transport including tools, resources, and prompts.

For Claude Desktop, the direct-HTTP path works for tools today but
prompts UI for HTTP MCP servers is still rolling out (build 1.6608.2
shows tools but no prompts row in Settings). Use Option A on Claude
Desktop until the build you're on lights up the prompts picker for
HTTP MCP.

### Option C — stdio with a locally installed `iris-mcp` binary

```json
{
  "mcpServers": {
    "iris": {
      "command": "uvx",
      "args": ["iris-mcp"],
      "env": {
        "IRIS_URL": "https://iris.example.com",
        "IRIS_TOKEN": "iris_pat_..."
      }
    }
  }
}
```

Runs `iris-mcp` locally from the package installed via `uv tool install`.
Useful for development against a local backend, or for self-hosted
deployments where you don't want to round-trip through the hosted MCP
service. Requires `uv` available on `PATH`. Omit `IRIS_TOKEN` to run
anonymous (subject to the `anon`/`anon_ai` rate-limit buckets per
ADR-123/129).

## Capabilities

- **Tools** for search, list/get/versions on diagrams + elements +
  packages + sets + collections, export (JSON + Markdown), ask-AI
  (single and multi-set), file extraction, applying AI-generated
  diagrams, and conversation history.
- **Resources** at `iris://diagrams|elements|packages|sets|collections/{id}`
  returning JSON export bundles.
- **Prompts** (v5.8.3, ADR-152; v5.8.5 naming refresh per ADR-153) —
  every Collection / Set with an attached `system_prompt` appears as
  `set:<uuid>` or `collection:<uuid>` (MCP clients namespace these
  under the server name automatically — e.g. Claude Code shows them
  as `/iris:set:<uuid>`). Invoking a prompt loads the body into the
  conversation as a user-authored directive.

## Conversation conventions

The MCP server `instructions` body (surfaced to every client via
`InitializeResult.instructions` per ADR-163 / v5.18.0) carries two
top-level conversation rules that every connected client / model
inherits:

- **ORIENT-FIRST PROTOCOL** — on the first turn after a scope's
  `mcp_system_context` is fetched, briefly describe the scope, invoke
  the named structural-overview call (typically `package_hierarchy`),
  then offer the scope's menu options via the client's user-question
  tool. The orient is mandatory, not optional (ADR-167).
- **ASKING QUESTIONS** (v6.1.0, ADR-177) — every time the model needs
  the user to pick from a finite set of options (orient menu, every
  Stage-0 setup question in a creation cascade, the save-destination
  chooser, anything else), use the client's structured user-question
  tool (`AskUserQuestion` in Claude Code / Claude Desktop / Cursor).
  Do not embed multi-option questions in prose; one question per
  turn; fall back to a numbered list with options IN ORDER, VERBATIM
  only if the client doesn't expose a question tool.

## Creation cascades

When the model fetches `get_response_prompt(notation=..., diagram_type=...,
purpose='creation_format')` to drive a guided diagram creation flow,
the returned body composes three shared base-layer prompts (v6.1.0,
ADR-176) common to every notation:

1. **`creation-cascade-shared-v1`** — Stage-0 questions (subject,
   info source with paste/upload affordance, default name suggestion)
   and the Stage 1 → Stage 2 transition question (skip detail / review
   detail / refine structure).
2. **`creation-cascade-citations-v1`** — citation discipline: every
   source-reference element uses raw URLs and the
   `Author/Org · Title · YYYY · https://url` label format.
3. **`creation-cascade-destination-v1`** — save-destination chooser
   (Iris / downloadable artefacts / both; new set under parent
   collection by default; markdown / docx / pdf format selection).

The notation-specific prompt (e.g. `creation-doview-notation-v1`)
adds methodology and any notation-specific Stage-0 questions. The
diagram-type prompt (e.g. `creation-outcomes-map-v1`) adds layout
rules. The shared layer applies to every notation — DoView, BPMN,
UML, ArchiMate, C4, Simple — so any cascade enjoys the same
conversational conventions without per-notation duplication.

Phase 1 of issue #133 (v6.1.0) ships the **prompts** for the
destination chooser; the actual md/docx/pdf renderer ships in v6.2.0
and the `move_*` recovery tools ship in v6.3.0. The Phase-1 cascade
explains the gap and offers fallbacks when the user picks formats or
destinations that the renderer/move tools don't yet support.
