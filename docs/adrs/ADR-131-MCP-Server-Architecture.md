# ADR-131: MCP Server Architecture (`iris-mcp`)

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-131 |
| **Initiative** | Agentic-AI-friendly API (Issue #21) |
| **Proposed By** | Engineering |
| **Date** | 2026-04-22 |
| **Status** | Proposed |

---

## ADR (WH(Y) Statement format)

**In the context of** the Model Context Protocol (MCP) being the
de-facto way autonomous AI agents (Claude Code, Claude Desktop,
Cursor, Windsurf, custom agents built on the Claude/OpenAI/Gemini
SDKs) discover and invoke tools, fetch resources, and read prompts —
Iris ships the HTTP API (ADR-129), PATs (ADR-127), and server-side
export (ADR-128), but no MCP surface, which means an agent today
needs a hand-written wrapper for each deployment,

**facing** the Issue #21 requirement that Iris be usable as an AI
resource — specifically to expose search, browse, ask-AI, diagram
creation, and export to agents with the MCP client conventions they
already support; and facing the DRY constraint that the MCP server
must not re-implement the HTTP API (duplication would break parity
with the CLI and the web frontend),

**we decided for** a **Python 3.12 + official `mcp` SDK** server at
`/mcp/` in the repo, published as `iris-mcp` (entry point:
`iris-mcp`), shipping as a **stdio MCP server**:
(a) **stdio transport only** for v1 — the universal transport for
MCP clients: users add an entry to `claude_desktop_config.json`,
`~/.claude/mcp.json`, `.cursor/mcp.json`, etc., of the form
`{"command": "uvx", "args": ["iris-mcp"], "env": {"IRIS_URL": "…",
"IRIS_TOKEN": "iris_pat_…"}}`; no server infrastructure, no SSE/HTTP
transport plumbing — just a subprocess the client manages;
(b) **auth** via the same `IRIS_URL` + `IRIS_TOKEN` env vars the CLI
uses; token is a PAT (ADR-127); anonymous (no token) works for every
endpoint that ADR-123 already allows anonymously, subject to the
`anon_ai` / `anon` rate-limit buckets (ADR-129);
(c) **shared HTTP client** — the MCP server imports `iris-client`
(ADR-132) and does **zero** raw HTTP calls; every tool is a thin
wrapper around an `iris_client.IrisClient` method, guaranteeing
parity with the CLI and the live schema;
(d) **tool inventory (v1)** — `search`, `list_diagrams`, `get_diagram`,
`get_diagram_versions`, `get_diagram_thumbnail`, `list_elements`,
`get_element`, `get_element_versions`, `list_packages`, `get_package`,
`package_hierarchy`, `list_sets`, `get_set`, `list_collections`,
`get_collection`, `export_diagram`, `export_element`, `export_package`,
`export_set`, `export_collection`, `ask`, `extract_file_text`,
`apply_diagram_creation`, `list_conversations` — each with a
LLM-friendly description (purpose + when-to-use + example input) and
JSON Schema derived from the shared Pydantic models;
(e) **resources** — entities are also exposed as MCP **resources** so
agents can use the generic "read resource" flow (e.g. when a user says
"summarise `iris://sets/default`"): URIs `iris://diagrams/{id}`,
`iris://elements/{id}`, `iris://packages/{id}`, `iris://sets/{id}`,
`iris://collections/{id}` resolve to the JSON export bundle; thumbnails
are exposed as **image resources** at `iris://diagrams/{id}/thumbnail`
rather than inlined in tool outputs, because MCP image resources are
the idiomatic way to pass images to a vision-capable model;
(f) **error mapping**: HTTP 4xx/5xx from `iris-client` become MCP tool
errors with a one-line human message and the status code in the
structured error payload — agents can distinguish 401 (bad token) from
404 (entity missing) from 429 (rate-limited) and retry or re-auth
appropriately;
(g) **no write tools outside AI creation** — `apply_diagram_creation`
is the only mutating tool in v1 per the approved scoping; element /
diagram / package / set / collection CRUD is not exposed; this is the
safest default for an agent with a user's PAT,

**and neglected** (a) **HTTP/SSE MCP transport** — valid and standards-
compliant, and the only way to share one MCP server across many
clients without each client spawning its own subprocess, but requires a
new server mount inside FastAPI (or a dedicated MCP web server), auth
plumbing (session tokens vs headers), and CORS / origin policy; stdio
covers every current Claude/Cursor install and can be extended later
via a second transport without breaking v1 clients; (b) **WebSocket
transport** — not in the MCP spec's current set of blessed transports;
moot; (c) **auto-generating the MCP tool list from OpenAPI** — the
tool descriptions and when-to-use guidance are the single biggest
influence on whether an LLM picks the right tool; hand-written
descriptions are more valuable than a larger auto-generated set;
(d) **running the MCP server inside the backend process** (as an
in-process server sharing the DB pool) — would bypass the HTTP API
entirely and break the "parity via `iris-client`" rule; explicitly
rejected; (e) **exposing audit log / admin endpoints** — out of scope
v1; agents should not be manipulating the audit log; (f) **MCP prompts
(templated prompts for the client to offer the user)** — a nice-to-
have that can be added once real prompt templates emerge from MCP
usage in the wild,

**to achieve** an MCP surface that drops into any modern agent's
config block with three lines of JSON, gives the agent a complete
read + ask-AI + apply-diagram capability set, stays in lockstep with
the HTTP API through the shared client, and distinguishes tools (the
agent performs an action) from resources (the agent reads an entity)
idiomatically,

**accepting that** stdio-only means every client must `uvx iris-mcp`
on its own machine (fine for Claude Desktop / Code / Cursor use;
HTTP transport can be added later for shared-server scenarios);
accepting that the image resource for thumbnails triggers an extra
HTTP round-trip per read (acceptable — thumbnails are small and
cached by the backend for 300s); accepting that the tool descriptions
need curation and occasional revision as LLM tool-picking behaviour
evolves — mitigated by the descriptions living next to the tool
schemas and being covered by LLM-eval tests once we have them.

---

## Summary

| Capability | Description | Specification |
|------------|-------------|---------------|
| Package | `/mcp/` — `iris-mcp` Python package, stdio transport, official `mcp` SDK, entry point `iris-mcp`. | [SPEC-131-A](./specs/SPEC-131-A-MCP-Server.md) |
| Auth | `IRIS_URL` + `IRIS_TOKEN` env. Anonymous if token absent. | SPEC-131-A |
| Tools | ~24 tools covering search, list/get, export, ask-AI, file extract, diagram creation, conversations. | SPEC-131-A |
| Resources | `iris://diagrams|elements|packages|sets|collections/{id}` → JSON bundle. `iris://diagrams/{id}/thumbnail` → image resource. | SPEC-131-A |
| Client | Imports `iris-client`; no raw HTTP in MCP code. | SPEC-131-A |
| Error mapping | HTTP 4xx/5xx → structured MCP tool error with status + message. | SPEC-131-A |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Depends On | ADR-127 | Personal Access Tokens | `IRIS_TOKEN` is a PAT. |
| Depends On | ADR-128 | Server-Side Export | `export_*` tools + `iris://` resources resolve to `/api/export/*`. |
| Depends On | ADR-129 | Public HTTP API Stabilisation | Tool schemas derived from `/api/openapi.json`. |
| Depends On | ADR-132 | Shared Python Client Library | MCP imports `iris_client.IrisClient`. |
| Coordinates | ADR-130 | CLI Architecture | MCP and CLI share `iris-client`; overlapping capabilities (search, ask, export) use the same underlying call. |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-131-A | MCP Server Implementation | Technical Specification | [specs/SPEC-131-A-MCP-Server.md](./specs/SPEC-131-A-MCP-Server.md) |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Engineering | 2026-04-22 |
