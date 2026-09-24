# Iris HTTP API

The Iris HTTP API is the same surface the SvelteKit frontend uses. It
is documented live at **`/api/docs`** (Swagger UI) and **`/api/redoc`**
(ReDoc) in every environment, with the raw schema at
**`/api/openapi.json`** (ADR-129).

## Base URL

| Environment | URL |
|---|---|
| Local dev | `http://localhost:8000` |
| UAT | `https://iris-uat.chrisbarlow.nz` |

## Authentication

| Credential | Issuer | Lifetime | Use |
|---|---|---|---|
| **JWT** | `/api/auth/login` (SQLite) or Supabase Auth (Supabase mode) | 15 min access, 7-day refresh | Browser sessions |
| **PAT** | `/api/users/me/tokens` (ADR-127) | Long-lived, revocable | CLI, MCP, CI, agents |

Both travel as `Authorization: Bearer <token>`. The backend
discriminates by the `iris_pat_` prefix and resolves both to the same
user dict. PATs inherit the creating user's role (Admin / Architect /
Reviewer / Viewer).

Many read endpoints accept anonymous callers (no `Authorization`
header) per [ADR-123](adrs/ADR-123-Anonymous-Read-Only-Bypass.md). The
anonymous rate-limit bucket is tighter than the authenticated ones.

## Managing Personal Access Tokens

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/users/me/tokens` | List your PATs (prefix + metadata, never the secret). |
| `POST` | `/api/users/me/tokens` | Create a PAT. The secret is returned **exactly once** in the `token` field. |
| `DELETE` | `/api/users/me/tokens/{id}` | Revoke. Idempotent. |

Example:

```sh
curl -X POST https://iris.example.com/api/users/me/tokens \
  -H "Authorization: Bearer <JWT>" \
  -H "Content-Type: application/json" \
  -d '{"name": "my laptop"}'
# → {"id": "...", "name": "my laptop", "prefix": "abc12345",
#    "token": "iris_pat_abc12345_...", "created_at": "..."}
```

Copy the `token` value — it will never be shown again. Then:

```sh
curl https://iris.example.com/api/search?q=payment \
  -H "Authorization: Bearer iris_pat_abc12345_..."
```

## Rate limits (ADR-129)

Six buckets, each with an independent sliding window. Exceeding one
bucket never blocks requests in another:

| Bucket | Who | Default | Window | Env override |
|---|---|---|---|---|
| `login` | `POST /api/auth/login` | 10 | 60 s | `IRIS_RATE_LIMIT_LOGIN` |
| `refresh` | `POST /api/auth/refresh` | 30 | 60 s | `IRIS_RATE_LIMIT_REFRESH` |
| `anon_ai` | Anonymous on `/api/ai/*` | 10 | 3600 s | `IRIS_RATE_LIMIT_ANON_AI` |
| `anon` | Other anonymous | 30 | 60 s | `IRIS_RATE_LIMIT_ANON` |
| `pat` | PAT (`Bearer iris_pat_…`) | 60 | 60 s | `IRIS_RATE_LIMIT_PAT` |
| `general` | JWT (any other Bearer) | 1000 | 60 s | `IRIS_RATE_LIMIT_GENERAL` |

A `429 Too Many Requests` response includes `Retry-After` in seconds.

## Versioning + deprecation policy

Paths are **unversioned** (`/api/...`), because version-on-every-path
forces a v1→v2 migration on every existing client the day you decide a
versioning scheme is "correct." Instead:

- **Additive changes** (new endpoint, new optional request field, new
  response field) are made freely and do not bump anything.
- **Breaking changes** ship as a `-v2` suffix on the affected path
  (e.g. `/api/diagrams/{id}-v2`). The original path continues to serve
  the old contract for **at least one minor release**, carrying these
  response headers:
  - `Deprecation: <RFC-1123 date>` — the date the path became deprecated.
  - `Sunset: <RFC-1123 date>` — the earliest date the path may be removed.
- Old paths are removed only after a subsequent minor release with the
  sunset date in the past.

Consumers (iris-cli, iris-mcp, third-party scripts) can detect the
headers and upgrade proactively.

## Feature highlights for agents

- **`GET /api/search`** — full-text search across elements, diagrams,
  packages, sets, collections. Anonymous-friendly.
- **`POST /api/ai/ask`** — multi-set Q&A with optional file contexts.
  Supports SSE streaming via `?stream=true`.
- **`POST /api/ai/sets/{id}/create-diagram/apply`** — ingest AI-
  generated diagram JSON (ADR-093/094).
- **`GET /api/export/{diagrams|elements|packages|sets|collections}/{id}?format=json|markdown`**
  — headless export bundles (ADR-128).
- **Relationships (ADR-249, v6.50.0)** — connect existing elements:
  - `POST /api/batch/relationships/create` — body
    `{"relationships": [{source_element_id, target_element_id,
    relationship_type, source_role?, target_role?, label?, description?,
    data?}, ...]}` (1–100 items). Each item succeeds or fails on its own;
    the response is `{succeeded, failed, errors[], ids[]}` and each error
    names the item's index. Items are rejected when source and target are
    the same element, when they are in different sets, or when either
    element doesn't exist. `source_role` / `target_role` are stored as
    `data.sourceRole` / `data.targetRole`.
  - `GET /api/relationships?element_id=&set_id=&relationship_type=&page=&page_size=`
    — `element_id` matches either end; `set_id` matches when either end is
    in the set. Every item includes `source_role`, `target_role` and `data`.
    Anonymous-friendly, as is `GET /api/relationships/{id}` (ADR-251).
  - `PUT /api/relationships/{id}` (`If-Match: <current_version>`) — full
    replace of `label` / `description` / `data`; optional
    `relationship_type` (omit to keep), `source_role` / `target_role`
    (merged into `data`; `""` clears).
  - `DELETE /api/relationships/{id}` (`If-Match`) — soft delete.
  - A returned id can be set as a diagram edge's `data.relationshipId` in
    `PUT /api/diagrams/{id}`; saving the diagram does not create a second
    relationship for that source/target pair.
- **`PATCH /api/diagrams/{id}`** — incremental canvas edits (ADR-252,
  v6.51.0). Body `{"operations": [...], "change_summary"?}` with 1–200
  operations, each an object with an `op`:
  `add_node {node}`, `update_node {id, position?, width?, height?, type?,
  data?}`, `remove_node {id, cascade_edges?=true}`, `add_edge {edge}`,
  `update_edge {id, data?, sourceHandle?, targetHandle?, type?}`,
  `remove_edge {id}`, `sync_labels {node_ids?}`. `data` in the update ops
  is shallow-merged (`null` deletes a key). Operations apply in order and
  atomically: the response `{id, current_version, updated_at, applied,
  results[]}` describes one new version (each result has the op's `index`,
  `op` and affected `id`; `remove_node` adds `removed_edges`, `sync_labels`
  returns `ids` changed and `skipped` nodes whose element is gone). A
  failing operation → `422` with `detail: {error: "operation_failed",
  op_index, op, message}` and nothing written. `If-Match: <version>` is
  optional; on a mismatch → `409` with `detail: {error:
  "version_conflict", current_version, expected_version, message}`.
  Validation: `add_node`'s `data.entityId` must be a live element in the
  diagram's set; node and edge ids must be new; edges must join existing
  nodes and a `data.relationshipId` must link the two nodes' elements
  (either direction). Only `{nodes, edges}` canvases can be patched. The
  new canvas is saved through the same path as `PUT`, so the stored data
  and side effects (relationship auto-create, search, thumbnails) match a
  full update. Same write-scope rules as `PUT`.
- **`GET /api/diagrams/{id}/elements`** — every element drawn on the
  diagram's current canvas, in one call (ADR-248). Each item is identical
  to `GET /api/elements/{id}` (tags, relationship and diagram-usage counts
  included); canvas order, duplicates and deleted elements removed; `404`
  if the diagram is missing or deleted. Anonymous-friendly — use it instead
  of one element request per node, which quickly exhausts the `anon`
  bucket above.

## Client libraries

- Python: [`iris-client`](../iris-client/README.md) — shared async
  `httpx` client used by both the CLI and the MCP server.
- CLI: [`iris-cli`](../cli/README.md) (once shipped).
- MCP: [`iris-mcp`](../mcp/README.md) (once shipped).

---

For deeper design rationale see
[ADR-127](adrs/ADR-127-Personal-Access-Tokens.md),
[ADR-128](adrs/ADR-128-Server-Side-Export.md), and
[ADR-129](adrs/ADR-129-Public-HTTP-API-Stabilisation.md).
