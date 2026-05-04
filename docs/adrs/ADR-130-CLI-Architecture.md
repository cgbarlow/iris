# ADR-130: CLI Architecture (`iris-cli`)

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-130 |
| **Initiative** | Agentic-AI-friendly API (Issue #21) |
| **Proposed By** | Engineering |
| **Date** | 2026-04-22 |
| **Status** | Proposed |

---

## ADR (WH(Y) Statement format)

**In the context of** Iris being usable today only through the
SvelteKit frontend in a browser — architects cannot query the
repository from a terminal, a shell pipeline, or a CI job; the
headless HTTP surface (ADR-129) and server-side export (ADR-128)
unlock this possibility but still require a human to wrangle curl +
JSON + authentication on the command line,

**facing** the requirement from Issue #21 that Iris be usable as an
**AI-friendly resource** — which includes not just MCP (ADR-131) but a
first-class CLI that a developer, architect, or CI job can invoke to
run a search, fetch a diagram, ask the AI a question, or export a set
as Markdown; and facing the DRY constraint that the CLI and the MCP
server must not independently re-implement the HTTP surface
(duplication would break parity the moment a router changes),

**we decided for** a **Python 3.12 + uv + Typer** CLI living at
`/cli/` in the repo root, published as the installable package
`iris-cli` (entry point: `iris`):
(a) **dependency stack:** `typer` (command tree + auto-help), `httpx`
(HTTP + SSE streaming), `rich` (tables + progress), `pydantic`
(response validation), all pinned to current stable releases at
install time per protocol 11;
(b) **config resolution order:** CLI flag → env (`IRIS_URL`,
`IRIS_TOKEN`) → `~/.config/iris/config.toml` → anonymous defaults
(`http://localhost:8000`, no token) — so `iris search foo` works on a
local dev box with zero setup, env vars take over in CI, and an
explicit `--url` / `--token` wins when both are set;
(c) **`iris login`** interactively prompts for username + password,
POSTs `/api/auth/login`, uses the returned JWT to create a PAT via
`POST /api/users/me/tokens` (name defaults to `iris-cli@<hostname>`),
stores `{url, token}` in the config file — the JWT is never persisted,
only the long-lived PAT; the secret is never printed on-screen;
(d) **command surface matches the v1 scope** (read-only + AI per the
approved plan): `search`, `diagrams|elements|packages|sets|collections`
`list|get|versions|thumbnail`, `export`, `ask` (with `--stream` default
on, `--file` uploads via `/api/ai/files/extract`, `--context` hydrates
local packs), `ask apply <path.json>` (wraps create-diagram/apply),
`conversations list`, `context pack create|list|show|delete`, `whoami`,
`login` — no mutation endpoints for entities (no create/update/delete,
no imports, no tags) to stay inside the scoping decision;
(e) **"add to context" is a local CLI concept, not a server-side
one** — because the backend assembles context per-request from
`set_ids`, `collection_id`, `docref_doc_ids`, and inline
`file_contexts`, there is no server state to "add to"; the CLI
therefore stores named bundles under
`~/.config/iris/contexts/<NAME>.json` (containing set IDs + extracted
file contents) and `iris ask --context NAME` hydrates the bundle into
the next ask request; this keeps the CLI stateless against the backend
and parity with MCP, which does the same thing in memory per session;
(f) **output format**: default `rich` tables for human use; `--json`
flag on every command for machine-parsable output (agents invoking the
CLI via `subprocess`); HTTP errors map to non-zero exit codes with a
friendly one-line message; SSE streaming for `iris ask` prints tokens
to stdout as they arrive;
(g) **shared HTTP client**: the CLI **does not** implement HTTP
itself; it depends on the `iris-client` library (ADR-132), keeping a
single source of truth for endpoint paths, schemas, and the
`iris_pat_` / JWT header handling;
(h) **packaging for v1**: installable via
`uv tool install git+https://github.com/cgbarlow/iris#subdirectory=cli`
or `pip install -e cli/` from a repo clone; PyPI publish is deferred
to a subsequent release once the surface has stabilised in real use,

**and neglected** (a) **Node / TypeScript** — would match the
frontend's stack but (i) requires regenerating OpenAPI types instead of
sharing Pydantic models with the backend, (ii) forces us to pick a
Node CLI framework (commander, oclif, yargs) without a clear winner,
(iii) costs a second toolchain (`node` + `npm`) on every install;
Python matches the backend, reuses the Pydantic models through
`iris-client`, and the MCP SDK we need (ADR-131) is a Python package
anyway; (b) **Go / Rust single-binary** — self-contained install is
attractive but doubles the implementation (every schema must be
hand-mapped) and the benefit is small while `uvx iris-cli` is
one-shot install for a Python-toolchain'd machine; (c) **wrapping the
existing OpenAPI as an auto-generated CLI (via e.g. `openapi-cli` or
`typer-openapi`)** — auto-generated CLIs are generic and poor UX; a
hand-written command tree lets us tune defaults (`--stream` on for
`ask`, sensible aliases, rich output) and is the right investment;
(d) **publishing to PyPI on day one** — premature; the package name,
command surface, and config format will shift in the first few weeks
of real use, and PyPI promises stability we don't want to make yet;
(e) **exposing write endpoints (element/diagram CRUD) behind a
`--yes`/force flag** — the user explicitly scoped v1 to read-only +
AI; writes can be added in a later ADR without breaking existing
commands,

**to achieve** a CLI that a human can pick up in 30 seconds
(`iris login`, `iris search foo`), that a CI job can script reliably
(env vars + `--json`), that an agent can invoke via `subprocess` and
parse the output of, and that stays in lockstep with the backend via
the shared `iris-client` library,

**accepting that** a Python tool requires Python 3.12 on the user's
machine (mitigated by `uv tool install`, which manages its own
interpreter); accepting that `~/.config/iris/config.toml` stores a
PAT in plaintext on disk (same risk model as `~/.ssh/id_rsa` — file
perms 0600, documented in SPEC-130-A); accepting that
`iris ask --stream` leaves interpretation of partial tokens to
whatever consumes stdout — fine for humans, agents use `--no-stream`
for atomic responses.

---

## Summary

| Capability | Description | Specification |
|------------|-------------|---------------|
| Package layout | `/cli/` at repo root. `pyproject.toml` with `[project.scripts] iris = "iris_cli:main"`. Depends on `iris-client`. | [SPEC-130-A](./specs/SPEC-130-A-CLI.md) |
| Command surface | `login`, `whoami`, `search`, `diagrams|elements|packages|sets|collections list\|get\|…`, `export`, `ask`, `ask apply`, `conversations`, `context pack …`. | SPEC-130-A |
| Config resolution | Flag → env → `~/.config/iris/config.toml` → anon defaults. Token stored as PAT (never JWT). | SPEC-130-A |
| Context packs | Local-only named bundles under `~/.config/iris/contexts/<NAME>.json`. Hydrated into ask requests via `--context NAME`. | SPEC-130-A |
| Output | `rich` tables by default; `--json` for machine output; non-zero exit on HTTP errors; SSE streaming for `ask`. | SPEC-130-A |
| Packaging v1 | `uv tool install` from the repo; PyPI deferred. | SPEC-130-A |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Depends On | ADR-127 | Personal Access Tokens | `iris login` creates and stores a PAT. |
| Depends On | ADR-128 | Server-Side Export | `iris export` wraps `/api/export/*`. |
| Depends On | ADR-129 | Public HTTP API Stabilisation | CLI reads the public API; docs live at `/api/docs`. |
| Depends On | ADR-132 | Shared Python Client Library | CLI imports `iris_client.IrisClient` — no duplicate HTTP code. |
| Coordinates | ADR-131 | MCP Server Architecture | CLI and MCP share `iris-client`; command names and tool names align where they overlap. |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-130-A | CLI Implementation | Technical Specification | [specs/SPEC-130-A-CLI.md](./specs/SPEC-130-A-CLI.md) |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Engineering | 2026-04-22 |
