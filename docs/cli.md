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

The URL must be the **iris-api backend service** — the host that
serves `/api/*`. **Not** the SvelteKit frontend (which serves the SPA
shell at every path) and **not** the iris-mcp service (which speaks
MCP, not REST). For the UAT deployment this is
`https://iris-api-gtb3.onrender.com`; self-hosted, it's whatever host
your `iris-api` Render/Docker/uvicorn service is on.

### SQLite-mode backend (local dev, single-tenant self-host)

```sh
iris login --url https://iris-api.example.com
# Prompts for username + password, creates a PAT, saves
# { url, token } to ~/.config/iris/config.toml (mode 0600).
```

### Supabase-mode backend (UAT, multi-tenant prod)

In Supabase deployment mode the backend's `/api/auth/login` is
disabled — auth is handled by Supabase Auth. Mint a PAT externally
and pass it to the CLI with `--token`:

```sh
# 1) Sign in via the frontend (https://iris-uat.chrisbarlow.nz)
#    and copy the Supabase JWT from your browser's local storage.
# 2) Mint a PAT with that JWT:
curl -X POST https://iris-api-gtb3.onrender.com/api/users/me/tokens \
  -H "Authorization: Bearer <supabase-jwt>" \
  -H "Content-Type: application/json" \
  -d '{"name":"iris-cli"}'
# -> { "token": "iris_pat_...", ... }   # shown ONCE
#
# 3) Hand the PAT to the CLI — no API call, just persists config:
iris login --url https://iris-api-gtb3.onrender.com --token iris_pat_...
```

(A frontend Settings → API Tokens page that mints PATs without the
curl detour is on the roadmap.)

### Env vars

Same rule — backend host:

```sh
export IRIS_URL=https://iris-api-gtb3.onrender.com
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
