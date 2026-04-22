# SPEC-130-A: CLI (`iris-cli`)

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-130-A |
| **ADR** | [ADR-130](../ADR-130-CLI-Architecture.md) |
| **Status** | Proposed |
| **Date** | 2026-04-22 |

## Overview

Python 3.12 + Typer CLI wrapping the HTTP API via `iris-client`.
Read-only + AI scope. Entry point `iris`.

## Package layout

```
cli/
  pyproject.toml
  README.md
  src/iris_cli/
    __init__.py
    __main__.py                # python -m iris_cli → main()
    main.py                    # Typer app assembly + entry point
    config.py                  # config.toml + env loader
    output.py                  # rich tables, json formatter
    context.py                 # local context-pack mgmt
    commands/
      __init__.py
      auth.py                  # login, whoami
      search.py
      diagrams.py
      elements.py
      packages.py
      sets.py
      collections.py
      export.py
      ask.py                   # ask, ask apply
      conversations.py
      context.py               # context pack CRUD
  tests/
    conftest.py                # httpx respx fixture
    test_login.py
    test_search.py
    ...
    snapshots/                 # golden-file outputs
```

`pyproject.toml`:

```toml
[project]
name = "iris-cli"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "iris-client",
  "typer>=0.12",
  "httpx>=0.27",
  "rich>=13",
  "pydantic>=2.8",
]

[project.scripts]
iris = "iris_cli.main:app"

[tool.uv.sources]
iris-client = { workspace = true }
```

## Configuration

Loader in `iris_cli/config.py`:

```python
@dataclass
class CliConfig:
    url: str
    token: str | None
    config_path: Path

def load_config(
    url_flag: str | None,
    token_flag: str | None,
) -> CliConfig:
    # Order: flag → env → ~/.config/iris/config.toml → anon defaults
    ...
```

**File location:** `${XDG_CONFIG_HOME:-~/.config}/iris/config.toml`.

**File format:**

```toml
[default]
url = "https://iris.example.com"
token = "iris_pat_abc12345_..."
```

File perms on create: `0600`.

Env overrides: `IRIS_URL`, `IRIS_TOKEN`.

Anonymous defaults: `url = "http://localhost:8000"`, `token = None`.

## Command reference

All commands accept `--url URL`, `--token TOKEN` global flags (Typer
`typer.Option(..., envvar="IRIS_URL")`).

### Auth

```
iris login [--url URL]
  # Interactive prompt: username, password.
  # Calls /api/auth/login → receives JWT.
  # Calls POST /api/users/me/tokens with name=f"iris-cli@{hostname}".
  # Writes {url, token} to ~/.config/iris/config.toml (0600).
  # Never prints the token.
  # Non-interactive form (CI): IRIS_USERNAME + IRIS_PASSWORD env + --non-interactive.

iris whoami
  # GET /api/auth/me → prints {username, role, token_prefix}.

iris logout
  # Revokes the stored PAT (DELETE /api/users/me/tokens/{id})
  # and clears config.
```

### Read commands

```
iris search "<query>" [--set ID] [--collection ID] [--limit 50] [--json]

iris diagrams list [--set ID] [--type TYPE] [--page N] [--page-size N] [--json]
iris diagrams get <id> [--json]
iris diagrams versions <id> [--json]
iris diagrams thumbnail <id> [--theme dark|light|high-contrast] [-o PATH]

iris elements list [--set ID] [--type TYPE] [--search TEXT] [--page N] [--json]
iris elements get <id> [--json]
iris elements versions <id> [--json]

iris packages list [--set ID] [--json]
iris packages get <id> [--json]
iris packages hierarchy [--set ID] [--root-id ID] [--json]

iris sets list [--collection ID] [--json]
iris sets get <id> [--json]

iris collections list [--json]
iris collections get <id> [--json]

iris conversations list --set ID [--limit 50] [--json]
```

### Export

```
iris export diagram <id>    --format json|markdown [-o PATH]
iris export element <id>    --format json|markdown [-o PATH]
iris export package <id>    --format json|markdown [-o PATH]
iris export set <id>        --format json|markdown [-o PATH]
iris export collection <id> --format json|markdown [-o PATH]
```

If `-o` omitted: writes to the filename suggested by the server's
`Content-Disposition` header in the current directory. If `-o -`:
stream to stdout.

### AI

```
iris ask "question"
  [--set S1 --set S2]                # repeatable
  [--collection C]
  [--mode discuss|creation]
  [--notation uml|archimate|simple|sequence|c4|doview]
  [--thread THREAD_ID]
  [--file PATH]                      # repeatable; extracted via /api/ai/files/extract
  [--context NAME]                   # hydrates ~/.config/iris/contexts/NAME.json
  [--stream/--no-stream]             # default: --stream
  [--provider PROVIDER_ID]
  [--json]                           # implies --no-stream

iris ask apply <diagrams.json> --set ID [--package ID]
  # Wraps POST /api/ai/sets/{id}/create-diagram/apply.
  # Prints resulting diagram_ids.
```

### Context packs (local-only)

```
iris context pack create NAME
  [--set S1 --set S2]                # set IDs to replay
  [--file PATH]                      # extracted once, stored inline
  [--description TEXT]

iris context pack list [--json]
iris context pack show NAME [--json]
iris context pack delete NAME [--yes]
```

Storage: `~/.config/iris/contexts/<NAME>.json`:

```json
{
  "name": "platform-rfcs",
  "description": "...",
  "created_at": "2026-04-22T10:00:00Z",
  "set_ids": ["set-uuid-1", "set-uuid-2"],
  "file_contexts": [
    {"filename": "rfc-42.md", "text": "# RFC-42\n...", "extracted_at": "..."}
  ]
}
```

On `iris ask --context NAME`, the CLI loads the file, merges its
`set_ids` with any `--set` flags, and passes `file_contexts` into
`POST /api/ai/ask`.

## Output

Two modes on every command that returns data:

- **Default:** `rich.table.Table` — columns chosen per command; wraps
  to terminal width; colours via existing `rich` themes.
- **`--json`:** `json.dumps(..., indent=2, default=str)` to stdout.
  No ANSI codes. Suitable for piping.

Errors:

- 4xx/5xx from `iris-client`: exit code `1`, one-line message on
  stderr (`Error: 404 Diagram not found`). `--json` mode prints a
  JSON error object (`{"error": "...", "status": 404}`).
- Network errors: exit code `2`.
- Auth errors (401/403): exit code `3`, suggest `iris login`.

Streaming (`iris ask --stream`):

- Tokens print to stdout as they arrive.
- Final line: `---` separator + `Conversation: <id>` on stderr.
- With `--json`: `--stream` is downgraded to `--no-stream` with a
  warning.

## Testing (TDD)

### Unit tests

`cli/tests/test_config.py`:

- Flag beats env beats file beats default.
- File created with `0600`.

`cli/tests/test_commands_*.py` — one per command module:

- Use `typer.testing.CliRunner` + `respx` mocking `iris-client`'s
  httpx calls.
- Golden-file output assertions under `cli/tests/snapshots/`.

`cli/tests/test_context.py`:

- Pack create reads files, extracts via mocked `/api/ai/files/extract`,
  writes to the expected path.
- `ask --context NAME` merges set IDs and file contexts into the
  request body.

### Integration tests

`cli/tests/integration/test_smoke.py` (marked `@pytest.mark.integration`,
skipped in unit runs):

- Boot a real backend fixture (uses `backend/tests/conftest.py`
  `TestClient` or a subprocess).
- `iris search "*"`, `iris diagrams list`, `iris export diagram <id>
  --format markdown` — verify real end-to-end behaviour.

## Acceptance criteria

1. `iris login` on a fresh machine creates a PAT, stores it 0600,
   and subsequent commands succeed without further prompting.
2. `iris search foo` returns a table; `iris search foo --json`
   returns parsable JSON.
3. `iris export set <id> --format markdown -o set.md` writes a file
   whose bytes exactly match the backend's `/api/export/sets/<id>?format=markdown`
   body.
4. `iris ask "…" --stream` prints tokens live.
5. `iris context pack create NAME --file doc.md` extracts the file
   and `iris ask --context NAME "…"` includes it in the request.
6. Unknown subcommand or bad flag → exit 2 with Typer's usage line.
7. Unit tests pass (`uv run pytest cli/`); integration smoke passes
   against a live backend.
