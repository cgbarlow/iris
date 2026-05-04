# iris-client

Async Python client for the Iris HTTP API.

Implements the decisions in
[ADR-132](../docs/adrs/ADR-132-Shared-Python-Client-Library.md) and the
spec in [SPEC-132-A](../docs/adrs/specs/SPEC-132-A-Shared-Client.md).

Used by:
- [`iris-cli`](../cli/) — the human-facing command-line tool.
- [`iris-mcp`](../mcp/) — the stdio MCP server for AI agents.
- Downstream Python integrations.

## Install (from a repo checkout)

```sh
uv sync                      # from repo root, installs the workspace
```

## Usage

```python
from iris_client import IrisClient

async with IrisClient(url="http://localhost:8000", token="iris_pat_...") as c:
    hits = await c.search(q="payment")
    diagram = await c.get_diagram("diagram-id")
```

If `token` is omitted (or `None`), the client runs anonymous — the
backend applies the anonymous rate-limit bucket and ADR-123 read-only
bypass.

## Configuration

| Source | Default |
|---|---|
| `IrisClient(url=...)` arg | first |
| `IRIS_URL` env | fallback |
| — | `http://localhost:8000` |

Same order for `token` / `IRIS_TOKEN`.

## Schema regeneration

```sh
IRIS_URL=http://localhost:8000 uv run iris-client-regen
```

Regenerates `src/iris_client/models/generated.py` from the running
backend's `/api/openapi.json`. The generated file is committed to the
repo; CI fails if it drifts from the live schema.
