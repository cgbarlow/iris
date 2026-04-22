# SPEC-132-A: Shared Python Client Library (`iris-client`)

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-132-A |
| **ADR** | [ADR-132](../ADR-132-Shared-Python-Client-Library.md) |
| **Status** | Proposed |
| **Date** | 2026-04-22 |

## Overview

Shared async HTTP client imported by both `iris-cli` and `iris-mcp`.
Pydantic models generated from the backend's `/api/openapi.json`.
Workspace-managed via uv.

## Repo-level workspace

New root `pyproject.toml` at repo root (this feature branch):

```toml
[project]
name = "iris-workspace"
version = "0.0.0"
requires-python = ">=3.12"

[tool.uv.workspace]
members = ["backend", "iris-client", "cli", "mcp"]
```

Each member package carries its own `pyproject.toml` with
`[tool.uv.sources]` workspace references as needed.

## Package layout

```
iris-client/
  pyproject.toml
  README.md
  src/iris_client/
    __init__.py               # exports IrisClient, common models
    client.py                 # IrisClient class
    auth.py                   # token header helper
    streaming.py              # SSE parser + ask_stream()
    exceptions.py
    models/
      __init__.py
      generated.py            # produced by datamodel-code-generator
      exports.py              # hand-written bundle schemas (mirror backend SPEC-128-A)
  scripts/
    regen_schemas.py          # calls datamodel-code-generator
  tests/
    conftest.py               # respx fixtures
    test_client_*.py
```

`pyproject.toml`:

```toml
[project]
name = "iris-client"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "httpx>=0.27",
  "pydantic>=2.8",
]

[project.optional-dependencies]
dev = [
  "datamodel-code-generator>=0.26",
  "pytest>=8",
  "respx>=0.22",
]

[project.scripts]
iris-client-regen = "iris_client.scripts.regen:main"
```

## Client surface

```python
from iris_client import IrisClient

async with IrisClient(url="http://localhost:8000", token="iris_pat_...") as c:
    hits = await c.search(q="payment", limit=20)
    diagram = await c.get_diagram("diagram-id")
    async for event in c.ask_stream(question="...", set_ids=["default"]):
        print(event.chunk, end="")
```

Constructor:

```python
class IrisClient:
    def __init__(
        self,
        url: str | None = None,
        token: str | None = None,
        *,
        timeout: float = 30.0,
        user_agent: str = "iris-client/0.1",
    ) -> None:
        self.url = url or os.environ.get("IRIS_URL", "http://localhost:8000")
        self.token = token if token is not None else os.environ.get("IRIS_TOKEN")
        self._client = httpx.AsyncClient(
            base_url=self.url,
            headers=self._auth_headers(),
            timeout=timeout,
        )

    def _auth_headers(self) -> dict[str, str]:
        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
```

Methods (v1 — read-only + AI):

```python
# Auth
async def login(self, username: str, password: str) -> LoginResponse
async def whoami(self) -> UserResponse
async def create_token(self, name: str, expires_at: datetime | None = None) -> TokenCreateResponse
async def list_tokens(self) -> list[TokenResponse]
async def revoke_token(self, token_id: str) -> None

# Search
async def search(self, q: str, *, set_id: str | None = None,
                 collection_id: str | None = None,
                 limit: int = 50) -> SearchResponse

# Diagrams / Elements / Packages / Sets / Collections — list / get / versions
async def list_diagrams(self, ...) -> DiagramListResponse
async def get_diagram(self, id: str) -> DiagramResponse
async def get_diagram_versions(self, id: str) -> list[DiagramVersion]
async def get_diagram_thumbnail(self, id: str, theme: str = "light") -> bytes

async def list_elements(self, ...) -> ElementListResponse
async def get_element(self, id: str) -> ElementResponse
async def get_element_versions(self, id: str) -> list[ElementVersion]

async def list_packages(self, ...) -> PackageListResponse
async def get_package(self, id: str) -> PackageResponse
async def package_hierarchy(self, ...) -> PackageHierarchy

async def list_sets(self, collection_id: str | None = None) -> list[SetResponse]
async def get_set(self, id: str) -> SetResponse

async def list_collections(self) -> list[CollectionResponse]
async def get_collection(self, id: str) -> CollectionResponse

# Export
async def export_diagram(self, id: str, format: Literal["json","markdown"]) -> bytes
async def export_element(self, id: str, format: ...) -> bytes
async def export_package(self, id: str, format: ...) -> bytes
async def export_set(self, id: str, format: ...) -> bytes
async def export_collection(self, id: str, format: ...) -> bytes

# AI
async def ask(self, question: str, *, set_ids: list[str] | None = None,
              collection_id: str | None = None,
              mode: str = "discuss",
              notation: str | None = None,
              thread_id: str | None = None,
              file_contexts: list[FileContext] | None = None,
              provider_id: str | None = None) -> QAResponse

async def ask_stream(self, ...) -> AsyncIterator[AskStreamEvent]
async def extract_file_text(self, filename: str, content: bytes) -> FileExtractResponse
async def apply_diagram_creation(self, set_id: str, diagrams_json: str,
                                 package_id: str | None = None) -> ApplyCreationResponse
async def list_conversations(self, set_id: str, limit: int = 50,
                             offset: int = 0) -> list[ConversationResponse]
```

## Schema generation

`scripts/regen_schemas.py`:

```python
import subprocess

def main() -> None:
    subprocess.run([
        "datamodel-codegen",
        "--url", os.environ.get("IRIS_URL", "http://localhost:8000") + "/api/openapi.json",
        "--output", "src/iris_client/models/generated.py",
        "--output-model-type", "pydantic_v2.BaseModel",
        "--target-python-version", "3.12",
        "--use-standard-collections",
        "--use-union-operator",
        "--disable-timestamp",
    ], check=True)
```

Usage:

```
# From a running backend
uv run iris-client-regen
```

CI:

- A job runs `uv run iris-client-regen` against a test-backend
  fixture and diffs the result against the committed file. Any
  change → CI fails, forcing the PR to include the regenerated
  `generated.py`. Prevents silent schema drift.

Generated file has a header comment:

```python
# GENERATED FILE — do not edit by hand.
# Regenerate with: uv run iris-client-regen
```

## SSE streaming

`src/iris_client/streaming.py`:

```python
class AskStreamEvent(BaseModel):
    kind: Literal["chunk", "done", "error"]
    chunk: str | None = None
    conversation_id: str | None = None
    model_used: str | None = None
    error: str | None = None

async def ask_stream(self, ...) -> AsyncIterator[AskStreamEvent]:
    async with self._client.stream(
        "POST", "/api/ai/ask?stream=true", json={...}
    ) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            if not line.startswith("data: "):
                continue
            payload = json.loads(line[len("data: "):])
            yield AskStreamEvent(**payload)
```

## Error handling

- `httpx.HTTPStatusError` is raised by `response.raise_for_status()`
  and allowed to bubble up. Callers (CLI, MCP) map it.
- Connection errors become `httpx.ConnectError` — similarly bubble.
- No retries beyond httpx's default transport; if we need retries
  later, we add them as an opt-in argument.

## Testing (TDD)

`iris-client/tests/test_client_search.py` and siblings:

- Use `respx` to mock the backend.
- Verify request URL, headers (`Authorization: Bearer ...`), body.
- Verify response parses into the expected Pydantic model.
- Verify anonymous mode sends no `Authorization` header.

`iris-client/tests/test_streaming.py`:

- Fake SSE response via `respx`; iterate `ask_stream`; assert the
  sequence of `AskStreamEvent` objects.

`iris-client/tests/test_generated_models.py`:

- Import and instantiate a sample of generated models to ensure
  the file is syntactically valid.

## Acceptance criteria

1. `uv sync` at repo root installs the workspace; `iris-client`,
   `iris-cli`, `iris-mcp` all resolvable.
2. `IrisClient(token="iris_pat_...")` sends the Bearer header;
   `IrisClient()` (no token) sends none.
3. `client.search("q")` parses into a `SearchResponse` model.
4. `client.ask_stream(...)` yields typed events ending in
   `kind="done"`.
5. `client.export_diagram(id, "markdown")` returns bytes matching
   the backend's `text/markdown` response.
6. `uv run iris-client-regen` against a running backend produces
   `generated.py` byte-identical to the committed file.
