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
- **Prompts** (v5.8.3, ADR-152) — every Collection / Set with an
  attached `system_prompt` appears as `iris:set:<uuid>` or
  `iris:collection:<uuid>`. Invoking a prompt loads the body into the
  conversation as a user-authored directive.
