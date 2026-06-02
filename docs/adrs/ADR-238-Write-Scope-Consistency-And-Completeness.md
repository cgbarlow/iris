# ADR-238: Make collection write-scope consistent and comprehensive

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-238 |
| **Initiative** | Fix the two defects found in live testing of ADR-237 write-scope: a create that passes but whose save 403s, and write affordances still shown in out-of-scope collections |
| **Proposed By** | Engineering |
| **Date** | 2026-06-02 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** the per-user collection write-scope shipped in ADR-237
(v6.45.0), where a scoped `architect` should be able to fully edit inside their
collections and have no write access elsewhere,

**facing** two defects found in live testing: (1) a scoped user could *create* a
view but got `403 "Outside your collection write-scope"` when adding an element /
saving — because the create-gate, the persisted row, and the update-gate each
resolved "the collection" differently (request payload vs the service's
`DEFAULT_SET_ID` fallback vs the persisted `set_id`), and the canvas's
add-element call sent neither `set_id` nor `package_id`; and (2) write
affordances (canvas **Edit**, global **New** buttons, package controls) still
appeared in out-of-scope collections, partly because `write_scope` didn't
reliably reach the client and partly because several surfaces (the canvas
editor, global creates, and the **relationships** / **package-relationships**
endpoints — ungated entirely) were never covered,

**we decided to** (a) introduce a single shared resolver
`resolve_effective_set(db, set_id, parent_package_id)` used by **both** the
create-gate and the `create_diagram`/`create_element`/`create_package` services,
so the create check, the persisted row, and the later update/delete check all
resolve the **same** collection (an entity created under a package now lands in
that package's set, not the un-grouped Default); (b) **gate every remaining
write surface** — element-relationships and package-relationships create/edit/
delete (via the source element/package's collection); (c) surface `collection_id`
on **package** reads (it was missing) so the client can gate package screens;
(d) make the frontend reliably load `write_scope` (refresh `/api/auth/me` on app
load) and have the canvas/hierarchy creates send `set_id`; and (e) gate the
remaining UI: force browse mode on out-of-scope views (hide the canvas Edit
button + guard the edit-mode entry centrally), and hide the global New buttons +
package edit controls when out of scope.

**because** the root cause was *inconsistent collection resolution across
operations* plus *incomplete coverage* — a single shared resolver removes the
class of create/update divergence, and gating the last endpoints + threading
collection context into the canvas closes the holes without changing the
read model (reads remain open, unchanged from ADR-237).

## Consequences
- A scoped user can create AND edit content inside their collections; the
  "created but can't save" failure is gone (regression-guarded in
  `tests/test_authz/test_collection_scope.py::TestScopeConsistencyADR238`).
- Canvas-created elements/diagrams land in their real set/collection instead of
  silently orphaning into the Default set (this also fixed a latent bug that
  affected *unscoped* users).
- All write endpoints are now scope-gated (relationships and
  package-relationships included). Reads are unaffected.
- The web UI hides edit/create affordances in collections the user can't write
  to, and reliably reflects scope after login and reload.

## Alternatives considered
- **Resolve the collection only at the gate (leave the service's Default
  fallback)**: rejected — that's exactly the divergence that caused the bug; the
  gate and the persisted row must agree.
- **Deny-by-default in the frontend `canWrite` when `write_scope` is absent**:
  rejected — would break unscoped/anonymous users; instead we ensure
  `write_scope` is reliably loaded (refresh on app start).
- **Restrict reads too**: out of scope (unchanged from ADR-237) — the ask is to
  confine edits, not hide content.

## Surface parity (§14) / §15
No new endpoints, MCP tools, or CLI commands — only enforcement added to existing
ones; `check_surface_parity` stays green. No schema change (package
`collection_id` is a SELECT join, not a column) → no migration.

## Dependencies
Extends [ADR-237](ADR-237-Per-User-Collection-Write-Scope.md). Spec:
`docs/adrs/specs/SPEC-237-A-Per-User-Collection-Write-Scope.md` (updated).
Operator runbook: `docs/collection-write-scope.md`.
