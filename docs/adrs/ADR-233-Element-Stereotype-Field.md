# ADR-233: Stereotype as a read-through element field

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-233 |
| **Initiative** | Surface the EA stereotype (e.g. ArchiMate_Capability) carried by imported elements |
| **Proposed By** | Engineering |
| **Date** | 2026-06-01 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** Sparx EA imports, where every element carries a
`stereotype` (e.g. `ArchiMate_Capability`) stored in
`element_versions.metadata.stereotype` (and on the canvas node's
`data.stereotype` for theming),

**facing** that this is not surfaced as a first-class element attribute —
`ElementResponse` exposes only the opaque `metadata` blob, so API/MCP/CLI
consumers and the element page can't reliably read "what kind of thing is
this",

**we decided to** expose `stereotype` as a **read-through derived field** on
`ElementResponse` (`stereotype = metadata.get("stereotype")`), typed on the
frontend `Element`, and shown as a chip on the element header (the element
page already renders a Stereotype detail-row). No new column, no migration,
no writer plumbing — `stereotype` already round-trips through the existing
`metadata` create/update path.

**because** the value already exists in metadata; promoting it to a named
read field gives a clean, typed surface for display now (and a hook for
future filter/group/theme-by-stereotype) at near-zero cost and risk, whereas
a first-class column would force a paired SQLite+Supabase migration, a
back-fill and writer changes for no v1 gain.

## Consequences
- `GET /api/elements/{id}` and the list endpoint return `stereotype`;
  the element page shows it as a chip.
- Deeper use (filtering/grouping/theming by stereotype) is explicitly future.

## Alternatives considered
- First-class `elements.stereotype` column — rejected for v1 (migration +
  back-fill + writer plumbing, no display benefit).
- Leave it in `metadata` only — rejected (not discoverable/typed).

## Surface parity (§14) / §15
Read-only derived field on GET responses — out of §14 scope (reads aren't
parity-checked); writes already exist via `metadata`. No schema change, no
migration.

Spec: `docs/adrs/specs/SPEC-233-A-Element-Stereotype-Field.md`.
