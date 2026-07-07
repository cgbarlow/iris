# ADR-241: iris-mcp GA4 tracking needs the shared env group linked in the Blueprint

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-241 |
| **Initiative** | Make the `mcp_tool_call` Measurement Protocol tracking (from the GA4-for-UAT work, PR #288) actually fire in production, and capture the env-group linkage in `render.yaml` so it can't silently regress |
| **Proposed By** | Engineering |
| **Date** | 2026-07-07 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** the Google-Analytics-for-UAT work (PR #288: frontend
`gtag.js` page views + `mcp/src/iris_mcp/analytics.py` server-side
`mcp_tool_call` events via the Measurement Protocol), the MCP-side tracking was a
**strict no-op in production despite the deploy being live and serving tool
traffic**. `analytics.py:is_enabled()` requires **both** a measurement ID and an
API secret; the ID is resolved as `GA_MEASUREMENT_ID` or, as a fallback,
`PUBLIC_GA_MEASUREMENT_ID`. The `iris-mcp` service was given `GA_API_SECRET`
(declared `sync: false`) but **was never supplied a measurement ID** —
`PUBLIC_GA_MEASUREMENT_ID` was declared only on the `iris-frontend` service, and
`render.yaml` contained **no env-group linkage** despite a code comment claiming
the ID "is inherited from the shared env group". Diagnosis confirmed this: GA
reported zero `mcp_tool_call` events over 365 days while Render request logs
showed active `POST /` MCP traffic to the deployed service,

**facing** the fact that GA env vars (`sync: false`) are entered in the Render
dashboard and are trivially, silently divergent from the committed Blueprint —
`is_enabled()` fails closed and swallows all send errors by design, so a missing
ID produces **no log, no error, no event**, only absent data,

**we decided to** (a) put **both** GA vars — `PUBLIC_GA_MEASUREMENT_ID` and
`GA_API_SECRET` — into the existing **`iris shared environment vars`** Render env
group, and (b) declare that group at the Blueprint top level (`envVarGroups`) and
reference it from **both** `iris-frontend` and `iris-mcp` via `fromGroup`, so the
MCP's measurement-ID fallback is actually satisfied and the linkage lives in
code, not just the dashboard; the redundant per-service `GA_API_SECRET` key on
`iris-mcp` is removed since the group now provides it,

**and neglected** (1) hard-coding a second per-service `GA_MEASUREMENT_ID` on
`iris-mcp` — rejected because it duplicates the frontend's value and re-creates
the same dashboard-vs-code drift this ADR exists to kill; (2) keeping
`GA_API_SECRET` per-service on `iris-mcp` only (strict least-privilege, so the
frontend build never sees the secret) — considered and **not** taken because the
static frontend bakes in only `PUBLIC_`-prefixed vars referenced in `app.html`,
so a non-`PUBLIC_` secret present in its build env is never emitted to the client;
the simpler single-group model was preferred, and this trade-off is recorded here
so it can be revisited; (3) making `analytics.py` fail *loud* (log a warning when
only one of the two vars is set) — deferred as a follow-up, out of scope for the
config fix,

**to achieve** a live `mcp_tool_call` event stream in the same GA4 property as
the frontend page-view stream (verified: one `list_collections` dispatch produced
exactly one `mcp_tool_call` event in GA Realtime immediately after the group was
linked and redeployed), captured durably in the Blueprint,

**accepting that** a `render blueprint sync` reconciles a group's membership to
what the `envVarGroups` block lists — so the block must enumerate **every** member
of `iris shared environment vars`, or a sync will prune the omitted ones; this ADR
lists the two GA vars known to be in the group and flags the constraint inline in
`render.yaml`. Values remain `sync: false` (dashboard-only, never committed).

---

## Consequences

- **No schema, endpoint, MCP tool, or CLI change.** Deploy configuration only.
  Surface parity (§14) and SQLite↔Supabase parity (§15) are N/A — no write
  surface is added or altered.
- **No `{@html}` change (§7).** No HTML rendering.
- **DRY (§13).** The GA measurement ID now has a single source of truth (the env
  group) instead of being declared per-service; the duplicated per-service
  `GA_API_SECRET` on `iris-mcp` is removed.
- **Prune hazard documented.** Because Blueprint sync is authoritative over group
  membership, `render.yaml` now carries a `⚠️` note that every group member must
  be listed before a sync. If the group later gains shared vars, they must be
  added to the `envVarGroups` block.
- **Least-privilege note.** `iris-frontend` now also receives `GA_API_SECRET` via
  the shared group. It is not exposed to browsers (static build emits only
  referenced `PUBLIC_` vars), but the blast radius is slightly wider; revisiting
  is captured in the **and neglected** clause.
- **Follow-up flagged.** `analytics.py` could log a one-time warning when exactly
  one of the two GA vars is set, converting this class of silent-no-op back into a
  visible signal. Tracked as a follow-up, not done here.

## Alternatives considered

See the **and neglected** clause: per-service `GA_MEASUREMENT_ID`, keeping the
secret per-service for least-privilege, and making `analytics.py` fail loud — each
rejected or deferred with rationale.

## Dependencies

- PR #288 (feat: Google Analytics for Iris UAT — frontend page views + MCP tool
  calls; commits `3959afb`, `c0e585c`) — introduced `analytics.py` and the
  `GA_API_SECRET` / `PUBLIC_GA_MEASUREMENT_ID` env contract this ADR wires up.

## References

- Implementation spec: [SPEC-241-A](./specs/SPEC-241-A-MCP-Analytics-Env-Group-Linkage.md)
- `mcp/src/iris_mcp/analytics.py` — `is_enabled()`, `_measurement_id()` fallback.
- `render.yaml` — `envVarGroups: iris shared environment vars` + `fromGroup` refs.
