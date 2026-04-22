# SPEC-131-A: MCP Server (`iris-mcp`)

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-131-A |
| **ADR** | [ADR-131](../ADR-131-MCP-Server-Architecture.md) |
| **Status** | Proposed |
| **Date** | 2026-04-22 |

## Overview

Python 3.12 stdio MCP server built on the official `mcp` Python SDK.
Wraps `iris-client`. Exposes ~24 tools + resource URIs for entities.

## Package layout

```
mcp/
  pyproject.toml
  README.md
  src/iris_mcp/
    __init__.py
    __main__.py             # python -m iris_mcp → run()
    server.py               # MCP Server wiring + stdio transport
    config.py               # IRIS_URL, IRIS_TOKEN env → IrisClient
    errors.py               # HTTP → MCP error mapper
    tools/
      __init__.py
      search.py
      diagrams.py
      elements.py
      packages.py
      sets.py
      collections.py
      export.py
      ai.py                 # ask, extract_file_text, apply_diagram_creation, list_conversations
    resources.py            # iris:// URI handlers
  tests/
    conftest.py
    test_tools_*.py
    test_resources.py
```

`pyproject.toml`:

```toml
[project]
name = "iris-mcp"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "iris-client",
  "mcp>=1.2",              # official Python SDK; verify latest stable
  "httpx>=0.27",
  "pydantic>=2.8",
]

[project.scripts]
iris-mcp = "iris_mcp.__main__:run"

[tool.uv.sources]
iris-client = { workspace = true }
```

## Server wiring

`src/iris_mcp/server.py`:

```python
from mcp.server import Server
from mcp.server.stdio import stdio_server

from iris_client import IrisClient

def build_server(client: IrisClient) -> Server:
    server = Server("iris-mcp")
    register_tools(server, client)
    register_resources(server, client)
    return server

async def run() -> None:
    config = load_config()
    async with IrisClient(url=config.url, token=config.token) as client:
        server = build_server(client)
        async with stdio_server() as (read, write):
            await server.run(read, write, InitializationOptions(...))
```

## Tool inventory

Each tool has:

1. A machine name (snake_case).
2. A description that is **LLM-facing** — purpose + when-to-use +
   one-line example input.
3. A JSON Schema for inputs derived from `iris-client` Pydantic
   request models.
4. An implementation that calls one `IrisClient` method.

| Tool | Wraps | Notes |
|---|---|---|
| `search` | `client.search(q, set_id, collection_id, limit)` | Returns flat list of mixed entity types with `deep_link`. |
| `list_diagrams` | `client.list_diagrams(...)` | Paginated. |
| `get_diagram` | `client.get_diagram(id)` | |
| `get_diagram_versions` | `client.get_diagram_versions(id)` | |
| `get_diagram_thumbnail` | `client.get_diagram_thumbnail(id, theme)` | Returns MCP `ImageContent` (PNG bytes). |
| `list_elements` | `client.list_elements(...)` | |
| `get_element` | `client.get_element(id)` | |
| `get_element_versions` | `client.get_element_versions(id)` | |
| `list_packages` | `client.list_packages(...)` | |
| `get_package` | `client.get_package(id)` | |
| `package_hierarchy` | `client.package_hierarchy(set_id, root_id)` | |
| `list_sets` | `client.list_sets(collection_id)` | |
| `get_set` | `client.get_set(id)` | |
| `list_collections` | `client.list_collections()` | |
| `get_collection` | `client.get_collection(id)` | |
| `export_diagram` | `client.export_diagram(id, format)` | format ∈ json/markdown. |
| `export_element` | `client.export_element(id, format)` | |
| `export_package` | `client.export_package(id, format)` | |
| `export_set` | `client.export_set(id, format)` | |
| `export_collection` | `client.export_collection(id, format)` | |
| `ask` | `client.ask(question, set_ids, collection_id, mode, notation, thread_id, file_contexts, provider_id)` | Non-streaming; returns full `QAResponse`. |
| `extract_file_text` | `client.extract_file_text(filename, bytes)` | For feeding back into `ask`. |
| `apply_diagram_creation` | `client.apply_diagram_creation(set_id, diagrams_json, package_id)` | AI-generated diagram ingest. |
| `list_conversations` | `client.list_conversations(set_id, limit, offset)` | |

### Tool description style

Example for `ask`:

```
Ask the Iris AI a question about one or more modelled sets. Use when
the user wants a synthesised answer across packages, diagrams, and
elements — e.g. "what services depend on the Payments component?" or
"summarise the onboarding flow". Pair with `search` if you need to
locate an entity first, or with `extract_file_text` to add external
document context.

Example:
  {
    "question": "Which components own customer PII?",
    "set_ids": ["default"],
    "mode": "discuss"
  }
```

## Resources

MCP resources at `iris://` URIs, registered via the SDK's
`list_resources` / `read_resource` handlers:

| URI | Returns |
|---|---|
| `iris://diagrams/{id}` | JSON export bundle (text/json resource). |
| `iris://elements/{id}` | JSON export bundle. |
| `iris://packages/{id}` | JSON export bundle. |
| `iris://sets/{id}` | JSON export bundle. |
| `iris://collections/{id}` | JSON export bundle. |
| `iris://diagrams/{id}/thumbnail` | Image resource (PNG). |

Resource discovery: `list_resources` returns top-level sets +
collections by default (not every entity — avoids a massive list).
The agent is expected to `search` or `list_*` first, then read the
specific resource.

## Error mapping

`src/iris_mcp/errors.py`:

```python
def map_http_error(exc: httpx.HTTPStatusError) -> McpError:
    status = exc.response.status_code
    detail = exc.response.json().get("detail", str(exc))
    return McpError(
        code={
            401: "UNAUTHENTICATED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            413: "TOO_LARGE",
            429: "RATE_LIMITED",
        }.get(status, "HTTP_ERROR"),
        message=f"{status}: {detail}",
        data={"http_status": status},
    )
```

Every tool wraps its `iris-client` call in `try/except
httpx.HTTPStatusError` and re-raises as the mapped `McpError`. The
MCP SDK surfaces this to the client as a structured tool error.

## Configuration

Env vars (loaded in `config.py`):

- `IRIS_URL` — base URL. Default `http://localhost:8000`.
- `IRIS_TOKEN` — PAT or JWT. Absent → anonymous.
- `IRIS_MCP_LOG_LEVEL` — default `INFO`.

Client install snippet (docs):

```json
{
  "mcpServers": {
    "iris": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/cgbarlow/iris#subdirectory=mcp", "iris-mcp"],
      "env": {
        "IRIS_URL": "https://iris.example.com",
        "IRIS_TOKEN": "iris_pat_..."
      }
    }
  }
}
```

## Testing (TDD)

`mcp/tests/test_tools_*.py`:

- For each tool module, mock `iris-client` methods and assert:
  - Tool schema matches the client's signature.
  - Happy path returns expected payload shape.
  - HTTP error → mapped `McpError`.
- Tool descriptions are non-empty and end with an example block
  (meta-test on the registry).

`mcp/tests/test_resources.py`:

- `iris://diagrams/{id}` reads via `client.export_diagram(id, "json")`
  and returns a text resource.
- `iris://diagrams/{id}/thumbnail` returns an image resource with
  `mime_type="image/png"`.
- Unknown URI → 404-equivalent error.

## Acceptance criteria

1. `uvx iris-mcp` boots, handshakes over stdio, and lists ~24 tools
   + ~6 resource URI templates.
2. In Claude Desktop with the snippet above, an agent can
   successfully call `search`, `get_diagram`, `ask`, and
   `apply_diagram_creation` against a running backend.
3. 401 from backend → `UNAUTHENTICATED` MCP error; agent surfaces a
   recoverable message.
4. `get_diagram_thumbnail` returns an image resource the vision
   model can read.
5. All tests pass (`uv run pytest mcp/`).
