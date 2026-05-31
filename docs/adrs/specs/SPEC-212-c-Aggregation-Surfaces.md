# SPEC-212-c: Aggregation REST / MCP / CLI surfaces

Implements: [ADR-212](../ADR-212-Aggregation-Profiles-And-Engine.md)

## 1. REST endpoints

### Profile CRUD (writes — need ADR-182 parity)

| Method + Path | Purpose | Auth |
|---|---|---|
| `POST /api/aggregation/profiles` | Create | Authenticated |
| `GET /api/aggregation/profiles` | List with scope filter | Authenticated read (optional in v1.1) |
| `GET /api/aggregation/profiles/{id}` | Fetch one | Authenticated read |
| `PUT /api/aggregation/profiles/{id}` | Update | Authenticated |
| `DELETE /api/aggregation/profiles/{id}` | Soft-delete | Authenticated |

### Run (read-shaped despite POST)

| Method + Path | Purpose |
|---|---|
| `POST /api/aggregation/run` body `{profile_id, source_diagram_id}` | Compute aggregation, return markdown |

POST because the body carries the profile and source ids. Idempotent (no persistence side-effects). Auth: same as profile read.

Response shape (matches `AggregationResult` from SPEC-212-b §2):

```json
{
  "markdown": "## Meat & Poultry\n- ...\n",
  "computed_at": "2026-05-22T11:00:00+00:00",
  "source_versions": {"<source-diag-id>": 7, "<inner-diag-id>": 3},
  "row_count": 12,
  "warnings": []
}
```

## 2. MCP tools

| Tool | Purpose |
|---|---|
| `create_aggregation_profile` | Write — needs surface parity. |
| `list_aggregation_profiles` | Read. |
| `get_aggregation_profile` | Read. |
| `update_aggregation_profile` | Write. |
| `delete_aggregation_profile` | Write. |
| `aggregate` | Run a profile against a source. **The linchpin tool.** Agent description emphasises shopping-list / rollup use case. |

`aggregate` tool description:

> "Run a named aggregation profile against a source smart_markdown diagram. Returns aggregated markdown — deduplicated, summed roll-up of entity values referenced across the source (and, if the profile uses a two-level traversal, the diagrams the source references). Use this when you need a shopping list from a meal plan, a points rollup from a sprint backlog, hours by client from a time log, an expense report from receipts, or any pattern that aggregates structured per-use values across a set of smart-markdown documents."

## 3. CLI subcommands

```
iris aggregation-profile create   --name <s> --profile-data-file <path> [--set <id>] [--global] [--description <s>]
iris aggregation-profile update   --id <id> [--name <s>] [--profile-data-file <path>] [--description <s>] [--set <id-or-null>] [--global/--no-global]
iris aggregation-profile list     [--set <id>] [--global]
iris aggregation-profile get      --id <id>
iris aggregation-profile delete   --id <id>

iris aggregate                    --profile <id-or-name> --source <diagram-id>
```

`--profile <id-or-name>`: accepts either a UUID or a `name` (the CLI resolves to id via `list` + filter; for ambiguous matches errors with a list of candidates).

## 4. Parity check

`scripts/check_surface_parity.py` already enforces write-parity. New writes (`POST/PUT/DELETE /api/aggregation/profiles`) get matching MCP tools and CLI subcommands listed above. No exceptions needed.

## 5. Tests

`backend/tests/test_aggregation/test_routes.py` — every endpoint, every status code.

`mcp/tests/test_aggregation.py` — every MCP tool name resolves and forwards correctly.

`cli/tests/test_aggregation.py` — every CLI subcommand round-trips against a fixture API.

## 6. Inline `profile_data` on `/run` (SPEC-212-f)

`POST /api/aggregation/run` accepts an optional `profile_data: ProfileData` in the request body for the form-editor's live-preview pane:

```json
{
  "profile_data": {"traversal": {...}, "output": {...}},
  "source_diagram_id": "<uuid>"
}
```

Exactly one of `profile_id` or `profile_data` must be supplied — providing both is `400`, providing neither is `400`. Malformed inline `profile_data` is `422` (Pydantic). The inline path bypasses the ADR-227 cache.

Mirrored on the parity surfaces:

- **MCP** `aggregate` tool: `profile_id` is now optional, new optional `profile_data: object` arg with the same exactly-one-of semantics.
- **CLI** `iris aggregate`: `--profile-data <path|->` flag accepts a JSON file path or `-` for stdin. Mutually exclusive with `--profile`.

`scripts/check_surface_parity.py` is unaffected — only the write set is checked, and `aggregate` was already a read-shaped POST on the existing exception list.
