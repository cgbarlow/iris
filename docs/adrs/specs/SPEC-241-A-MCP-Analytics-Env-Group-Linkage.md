# SPEC-241-A: iris-mcp GA4 tracking via the shared env group

Implements **[ADR-241](../ADR-241-MCP-Analytics-Env-Group-Linkage.md)**.

## 1. The enablement contract (unchanged code, `mcp/src/iris_mcp/analytics.py`)

`mcp_tool_call` events fire only when **both** resolve to a truthy value:

| Function | Reads | Notes |
|----------|-------|-------|
| `_measurement_id()` | `GA_MEASUREMENT_ID` → else `PUBLIC_GA_MEASUREMENT_ID` | fallback to the frontend's var |
| `_api_secret()` | `GA_API_SECRET` | Measurement Protocol secret |

`is_enabled()` is `bool(measurement_id and api_secret)`. When false, `track_tool_call`
returns before any POST — **no log, no error, no event**. This spec supplies the
missing measurement ID to `iris-mcp` so the AND is satisfied; no code changes.

## 2. Env group membership (`iris shared environment vars`)

The group is authoritative for both GA vars. Both `sync: false` (values live in
the Render dashboard, never committed):

| Key | Consumed by | Purpose |
|-----|-------------|---------|
| `PUBLIC_GA_MEASUREMENT_ID` | iris-frontend (build-time `gtag.js`), iris-mcp (MP fallback ID) | GA4 measurement ID, e.g. `G-5B0T5HKVQ9` |
| `GA_API_SECRET` | iris-mcp | GA4 Measurement Protocol API secret |

## 3. Blueprint changes (`render.yaml`)

| Location | Before | After |
|----------|--------|-------|
| top level | *(no `envVarGroups`)* | `envVarGroups:` declaring `iris shared environment vars` with both keys (`sync: false`) |
| `iris-frontend` `envVars` | `- key: PUBLIC_GA_MEASUREMENT_ID` (`sync: false`) | `- fromGroup: iris shared environment vars` |
| `iris-mcp` `envVars` | `- key: GA_API_SECRET` (`sync: false`), no ID | `- fromGroup: iris shared environment vars` (provides both; per-service `GA_API_SECRET` removed) |

`iris-api` is **not** linked — it renders no browser pages and has no Measurement
Protocol code (verified: the only "analytics" references in `backend/` are demo
seed content in `scenia_seed.py`).

## 4. Blueprint-sync invariant (prune hazard)

A `render blueprint sync` reconciles a group's membership to exactly what the
`envVarGroups` block lists. Therefore the block **must enumerate every member** of
`iris shared environment vars`; any dashboard var omitted here is pruned on sync.
Currently the group holds exactly the two GA vars above. `render.yaml` carries a
`⚠️` comment stating this constraint.

## 5. Verification

1. Link the group to `iris-mcp` in the dashboard and redeploy (done manually
   2026-07-07, deploy `dep-d96oak3tqb8s73eb879g`, status `live`).
2. Invoke any MCP tool against the deployed server.
3. GA4 Realtime → filter `eventName` contains `mcp` → expect `mcp_tool_call ≥ 1`.
   **Observed:** one `list_collections` dispatch produced exactly one
   `mcp_tool_call` event in property `chrisbarlow.nz` (`532831327`).

Failed dispatches still emit an event with `success=false` (by design), so a 401
from an expired backend token during the check still validates the path.

## 6. Out of scope / follow-ups

- **Loud enablement warning.** `analytics.py` could log once when exactly one of
  the two GA vars is set (silent-no-op → visible signal). Deferred (ADR-241
  **and neglected** #3).
- **Custom dimensions.** Register `tool` (and optionally `success`, `duration_ms`)
  as GA4 event-scoped custom definitions to slice `mcp_tool_call` by tool name.
  Dashboard action, no code/Blueprint change; does not backfill.
