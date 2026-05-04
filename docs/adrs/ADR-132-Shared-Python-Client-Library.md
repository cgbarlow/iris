# ADR-132: Shared Python Client Library (`iris-client`)

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-132 |
| **Initiative** | Agentic-AI-friendly API (Issue #21) |
| **Proposed By** | Engineering |
| **Date** | 2026-04-22 |
| **Status** | Proposed |

---

## ADR (WH(Y) Statement format)

**In the context of** Issue #21 shipping three surfaces that all call
the same HTTP API — the CLI (ADR-130), the MCP server (ADR-131), and
future service-to-service integrations — each of which needs to
(i) construct the correct URL with `/api/` prefixes, (ii) attach the
correct `Authorization: Bearer ...` header for either a JWT or a PAT
(ADR-127), (iii) parse JSON responses into typed models matching the
backend's Pydantic schemas, (iv) handle SSE streaming for `POST
/api/ai/ask`, and (v) degrade gracefully to anonymous mode when no
token is present,

**facing** the DRY protocol (`docs/protocols.md` § 13) which forbids
CLI and MCP from independently re-implementing HTTP plumbing — a
real risk because the two surfaces are in separate packages, owned
by separate command trees, and tested with separate fixtures; and
facing the parity requirement — whatever the CLI can do, the MCP
must do identically, or agents and humans will see different results
for the same underlying capability,

**we decided for** a dedicated `iris-client` Python package at
`/iris-client/` in the repo, depended on by both `cli/` and `mcp/`
(and available for downstream Python users), which encapsulates:
(a) **an `IrisClient` class** built on `httpx.AsyncClient`, with
typed methods for every in-scope endpoint — `search()`, `get_diagram()`,
`list_elements()`, `export_diagram()`, `ask()`, `apply_diagram_creation()`,
etc. — returning Pydantic models;
(b) **auto-generated Pydantic models** produced by
`datamodel-code-generator` from the backend's live `/api/openapi.json`
(available always-on per ADR-129), committed to the repo as generated
artefacts under `iris-client/src/iris_client/models/generated.py` so
schema drift is visible in PR diffs — the generator is invoked via
`uv run iris-client-regen` (or `make schemas`) against a running
backend, and a CI job fails if the committed file doesn't match what
the generator produces from the backend's current OpenAPI;
(c) **auth as a single concern** — `IrisClient(token=...)` handles
both JWT and PAT (they are both Bearer tokens; the client doesn't
need to care which) and a `None` token yields anonymous mode; the
token prefix is preserved as-is in the header;
(d) **SSE streaming helper** — `async for event in client.ask_stream(...)`
yields typed `AskStreamEvent` dicts, hiding the raw SSE frame format
from both CLI and MCP;
(e) **workspace packaging** — the repo gains a root `pyproject.toml`
declaring a **uv workspace** with members `backend/`, `cli/`, `mcp/`,
`iris-client/`, so one `uv sync` at the root installs the whole
monorepo and each package can depend on siblings via workspace
references (`iris-client = { workspace = true }`);
(f) **version pinning** — the three client-facing packages
(`iris-client`, `iris-cli`, `iris-mcp`) share a major version with
the backend, meaning `iris-client==4.3.*` is the guaranteed client
for `backend 4.3.*`; breaking backend changes bump the major
everywhere;
(g) **zero business logic** — `iris-client` is a transport + schema
layer only; no caching, no request-coalescing, no retries beyond
httpx's built-ins — a thin client that is easy to reason about and
equally easy to replace if someone wants a different stack,

**and neglected** (a) **OpenAPI client generators (`openapi-python-client`,
`openapi-generator`)** — valid alternatives that produce a full
client from the OpenAPI document; rejected because (i) their
generated code is verbose, opinionated, and hard to customise
(e.g. our SSE helper wouldn't fit their templates), (ii) their
Pydantic output lags the v2 features we want, (iii) we'd still need
a hand-written wrapper for ergonomics, so we'd end up with two layers
instead of one; `datamodel-code-generator` just for the model layer +
hand-written client methods is the sweet spot; (b) **importing the
backend's Pydantic models directly from `backend/app/`** — would be
perfect parity but makes `iris-client` depend on every backend
dependency (SQLAlchemy, aiosqlite, asyncpg, etc.), which is absurd
for a client; generation from OpenAPI decouples cleanly; (c) **a
per-language fleet of clients (Python, TypeScript, Go)** — out of
scope for v1; Python is all we need for the CLI + MCP + most agents;
future ADRs can add a TypeScript client for the frontend when it
stops relying on `fetch` directly; (d) **`sync` + `async` variants
of every method** — doubles the surface; keep the client async-only
and let callers use `asyncio.run()` or `anyio` if they need sync; the
CLI wraps async methods in a single `asyncio.run()` per command, MCP
is async natively; (e) **schema generation at client-runtime from a
live backend** — too fragile; committed artefacts are more
debuggable,

**to achieve** a single place where an HTTP call or a schema change
is made (one import in cli and mcp), guaranteed parity across the
three surfaces, a package downstream Python users can `pip install`
to talk to Iris without reinventing the wheel, and schema drift that
shows up loudly in PR review rather than silently at runtime,

**accepting that** schema regeneration is a manual step (invoke
`uv run iris-client-regen` against a running backend) — fine because
schema changes are expected to accompany backend PRs, and CI enforces
that the committed file matches the backend's OpenAPI; accepting
that async-only means sync Python callers must use `asyncio.run()` —
standard cost for modern Python HTTP libraries; accepting that
`iris-client` and the backend are versioned in lockstep — simpler
than independent versioning and matches how the repo is already
released as a single unit.

---

## Summary

| Capability | Description | Specification |
|------------|-------------|---------------|
| `iris-client` package | `/iris-client/` — `httpx`-based async client, typed methods for every v1-scope endpoint, SSE streaming helper. | [SPEC-132-A](./specs/SPEC-132-A-Shared-Client.md) |
| Generated models | `datamodel-code-generator` from `/api/openapi.json` → `iris_client/models/generated.py`. Committed; CI verifies. | SPEC-132-A |
| Auth | `IrisClient(token=...)` handles both JWT + PAT (Bearer) + anonymous (`token=None`). | SPEC-132-A |
| Workspace | Root `pyproject.toml` declares uv workspace with members `backend/`, `cli/`, `mcp/`, `iris-client/`. | SPEC-132-A |
| Version pinning | Shared major version with backend. `iris-cli` and `iris-mcp` depend on `iris-client` via workspace reference. | SPEC-132-A |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Depends On | ADR-127 | Personal Access Tokens | Client accepts PATs as Bearer tokens. |
| Depends On | ADR-129 | Public HTTP API Stabilisation | Schema generation pulls from `/api/openapi.json`. |
| Enables | ADR-130 | CLI Architecture | CLI imports `iris_client.IrisClient`. |
| Enables | ADR-131 | MCP Server Architecture | MCP imports `iris_client.IrisClient`. |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-132-A | Shared Client Library Implementation | Technical Specification | [specs/SPEC-132-A-Shared-Client.md](./specs/SPEC-132-A-Shared-Client.md) |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Engineering | 2026-04-22 |
