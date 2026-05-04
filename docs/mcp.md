# Iris MCP Server — `iris-mcp`

Iris exposes a Model Context Protocol server so AI agents (Claude
Desktop, Claude Code, Cursor, custom clients) can use Iris as a
knowledge and modelling resource. Two install paths — pick the one
that suits the client.

## Recommended: remote install (URL only)

This is the easiest path for end users. **No Python, no uv, no git, no
local install.**

iris-mcp runs as its own Render web service (ADR-134) — a
Streamable-HTTP MCP server that proxies the iris backend. To add it
to Claude Desktop:

1. Open Claude Desktop → **Settings → Connectors → Add custom connector**.
2. Name: `iris`.
3. Remote MCP server URL: `https://iris-mcp-gtb3.onrender.com`
   (or your iris-mcp deployment's bare hostname — the standalone
   service is MCP-only, so the protocol lives at `/`, not `/mcp`).
4. Optional: paste a PAT (`iris_pat_…`) for authenticated access.
   Without it, you get the same anonymous read-only + AI scope as the
   web frontend.
5. Save. The 19 iris tools appear in the next chat's tool picker.

Same idea for Cursor's *Add Custom MCP Server* and any other client
that accepts a remote MCP URL.

### Mint a PAT (optional)

```sh
curl -X POST https://iris-uat.chrisbarlow.nz/api/users/me/tokens \
  -H "Authorization: Bearer <browser JWT>" \
  -H "Content-Type: application/json" \
  -d '{"name": "claude-desktop"}'
# → returns { token: "iris_pat_…" } once. Copy it; it isn't shown again.
```

Or use `iris login` from `iris-cli` (mints + saves a PAT in one step).

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

Each tool ships with an LLM-facing description with "when to use"
guidance so an agent picks the right tool without manual prompting.

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
| 401 / 403 | `ERROR: Unauthenticated (…). Check your PAT.` |
| 429 | `ERROR: Rate-limited (…). Try again shortly.` |
| 4xx / 5xx | `ERROR: HTTP <code>: <detail>` |

## Example agent prompt

> Using the iris MCP, search for any element named "Payments", fetch
> its relationships, and export the owning set as Markdown so I can
> commit it to our wiki.

The agent will call `search`, `get_element`, `export_set`, and return
the Markdown body.

---

## Local install (advanced)

For offline use, sandboxed environments, or anyone who'd rather have
the MCP server in their own process. Requires Python ≥ 3.12 and a
launcher (`uvx`, `pipx`, or `pip`).

### With uv

```sh
# From a repo checkout:
uv tool install --from ./mcp iris-mcp

# Or directly from GitHub:
uv tool install "git+https://github.com/cgbarlow/iris.git#subdirectory=mcp"
```

Claude Desktop config (`%APPDATA%\Claude\claude_desktop_config.json` on
Windows, `~/Library/Application Support/Claude/claude_desktop_config.json`
on macOS):

```json
{
  "mcpServers": {
    "iris": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/cgbarlow/iris.git#subdirectory=mcp",
        "iris-mcp"
      ],
      "env": {
        "IRIS_URL": "https://iris.example.com",
        "IRIS_TOKEN": "iris_pat_..."
      }
    }
  }
}
```

### With pipx (no uv required)

```sh
pipx install "git+https://github.com/cgbarlow/iris.git#subdirectory=mcp"
```

Then `"command": "iris-mcp"` (no `args`) in the config.

After editing the config file, **fully quit Claude Desktop** (system-
tray Quit, not close-window) and reopen.

---

See [ADR-131](adrs/ADR-131-MCP-Server-Architecture.md) (stdio
architecture), [ADR-133](adrs/ADR-133-MCP-Remote-Transport.md) (HTTP
remote transport), and SPEC-131-A / SPEC-133-A for the full design.
