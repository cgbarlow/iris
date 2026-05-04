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

Add to `claude_desktop_config.json` / `~/.claude/mcp.json` /
`.cursor/mcp.json`:

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

Omit `IRIS_TOKEN` to run anonymous (subject to the `anon`/`anon_ai`
rate-limit buckets per ADR-123/129).

## Capabilities

- **Tools** for search, list/get/versions on diagrams + elements +
  packages + sets + collections, export (JSON + Markdown), ask-AI
  (single and multi-set), file extraction, applying AI-generated
  diagrams, and conversation history.
- **Resources** at `iris://diagrams|elements|packages|sets|collections/{id}`
  returning JSON export bundles.
