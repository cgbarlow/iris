# Iris MCP Server — `iris-mcp`

Stdio Model Context Protocol server for AI agents (ADR-131 / SPEC-131-A).
Wraps the Iris HTTP API through the shared
[`iris-client`](../iris-client/README.md) so parity with the CLI and
the web frontend is guaranteed.

## Install

```sh
# From a repo checkout:
uv tool install --from ./mcp iris-mcp

# Or from GitHub:
uv tool install "git+https://github.com/cgbarlow/iris#subdirectory=mcp"
```

## Configure your MCP client

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

Mint the PAT via `iris login` or the frontend's Settings → API Tokens.
Omit `IRIS_TOKEN` to run anonymous — subject to the `anon`/`anon_ai`
rate-limit buckets per ADR-123/129.

## Tools

| Tool | What it does |
|---|---|
| `search` | Full-text search across entities |
| `list_diagrams` / `get_diagram` | Browse diagrams |
| `list_elements` / `get_element` | Browse elements |
| `list_packages` / `get_package` | Browse packages |
| `list_sets` / `get_set` | Browse sets |
| `list_collections` / `get_collection` | Browse collections |
| `export_diagram` / `..._element` / `..._package` / `..._set` / `..._collection` | Export as JSON or Markdown (ADR-128) |
| `ask` | Multi-set AI question with optional file contexts |
| `apply_diagram_creation` | Apply an AI-generated diagram bundle (`mode="creation"` output of `ask`) |
| `list_conversations` | AI conversation history for a set |

Each tool carries an LLM-facing description with "when to use"
guidance so an agent can pick the right tool without manual prompting.

## Resources

`iris://{diagrams|elements|packages|sets|collections}/{id}` resolves
to the JSON export bundle for that entity. Agents that prefer the
standard "read resource" flow can use:

```
Please summarise iris://sets/default
```

## Error mapping

| HTTP | MCP tool result |
|---|---|
| 401 / 403 | `ERROR: Unauthenticated (…). Check IRIS_TOKEN.` |
| 429 | `ERROR: Rate-limited (…). Try again shortly.` |
| 4xx / 5xx | `ERROR: HTTP <code>: <detail>` |

## Example agent prompt

> Using the iris MCP, search for any element named "Payments", fetch
> its relationships, and export the owning set as Markdown so I can
> commit it to our wiki.

Under the hood the agent will call `search`, `get_element`,
`export_set`, and return the Markdown body.

See [ADR-131](adrs/ADR-131-MCP-Server-Architecture.md) and
[SPEC-131-A](adrs/specs/SPEC-131-A-MCP-Server.md) for the full design.
