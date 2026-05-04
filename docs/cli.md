# Iris CLI — `iris`

Python command-line interface over the Iris HTTP API. Read-only + AI
scope (ADR-130 / SPEC-130-A).

## Install

```sh
# From a repo checkout:
uv tool install --from ./cli iris-cli

# Or from GitHub:
uv tool install "git+https://github.com/cgbarlow/iris#subdirectory=cli"
```

If this is your first `uv tool install` on this machine, uv will warn
that `~/.local/bin` isn't on `PATH`. One-time fix that future-proofs
every tool you install via uv:

```sh
uv tool update-shell
exec $SHELL -l   # reload shell so the new PATH takes effect
```

## First login

```sh
iris login --url https://iris.example.com
# Prompts for username + password, creates a PAT, saves
# { url, token } to ~/.config/iris/config.toml (mode 0600).
```

Alternatively, export env vars:

```sh
export IRIS_URL=https://iris.example.com
export IRIS_TOKEN=iris_pat_...
```

Config resolution order (first match wins):
1. `--url` / `--token` flags
2. `IRIS_URL` / `IRIS_TOKEN` env
3. `$XDG_CONFIG_HOME/iris/config.toml` (defaults to `~/.config/...`)
4. Anonymous defaults (`http://localhost:8000`, no token)

## Commands

| Command | Purpose |
|---|---|
| `iris login` | Interactive — mints a PAT and saves it |
| `iris whoami` | Show the authenticated user |
| `iris search <query>` | Full-text search (`--set`, `--collection`, `--limit`) |
| `iris diagrams list` / `get <id>` / `versions <id>` | Diagrams |
| `iris elements list` / `get <id>` | Elements |
| `iris packages list` / `get <id>` | Packages |
| `iris sets list` / `get <id>` | Sets |
| `iris collections list` / `get <id>` | Collections |
| `iris export diagram\|element\|package\|set\|collection <id> --format json\|markdown [-o PATH]` | Headless export |
| `iris ask "<question>"` | AI question (`--set S` repeatable, `--mode discuss\|creation`, `--stream/--no-stream`) |
| `iris conversations list --set <id>` | History |

Add `--json` to any command for machine-parsable output. `-o -` on
`iris export` writes to stdout.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | success |
| `1` | HTTP 4xx/5xx from the backend (not auth/network) |
| `2` | Network / connection error |
| `3` | 401 / 403 — hints `iris login` |

## Example recipes

```sh
# Pipe search hits into jq:
iris search payment --json | jq '.results[].name'

# Export an entire set as Markdown and commit it:
iris export set <id> --format markdown -o docs/platform.md
git add docs/platform.md && git commit -m "Sync platform docs from Iris"

# Streaming ask:
iris ask "Which services own PII?" --set default --stream

# Non-streaming ask with JSON for scripting:
iris ask "Count of Architect-owned diagrams" --set default --json \
  | jq '.answer'
```

See [ADR-130](adrs/ADR-130-CLI-Architecture.md) and
[SPEC-130-A](adrs/specs/SPEC-130-A-CLI.md) for the full design.
