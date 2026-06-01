# ADR-237: Restrict a user's write permissions to a whitelist of collections

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-237 |
| **Initiative** | Let an admin keep a user's global role (e.g. `architect`) but confine that role's WRITE powers to a specified list of collections; read-only everywhere else |
| **Proposed By** | Engineering |
| **Date** | 2026-06-01 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** wanting to hand someone an editing role but confine their
edits to a subset of collections (e.g. give an external contributor `architect`
on two collections only), where roles in Iris are global and there is no
per-collection access control,

**facing** that the only knobs today are the four global roles (admin /
architect / reviewer / viewer) — a write-capable role can edit *every*
collection — and that reads are already anonymous (ADR-123), so the meaningful
lever is *write* authorization, not read,

**we decided to** add a per-user **collection write-scope**: a junction table
`user_collection_scope(user_id, collection_id)`. A user with rows may WRITE only
inside those collections; a user with **no rows is unscoped** (writes everywhere
— the prior behaviour); **admins always bypass**. Enforcement is a thin
app-layer guard (`backend/app/authz/`): `assert_write_allowed(db, user,
collection_id)` on every write endpoint (resolving the target entity's owning
collection via `collection_of_set/package/diagram/element/template`), and
`assert_unscoped_or_admin(db, user)` on the operations a scoped user may never
perform — **creating or deleting a collection, and mutating a global element
template**. Reads are untouched. Assignment is managed **directly in Supabase**
(the admin inserts rows in the dashboard) — Iris only reads + enforces — so **no
new write endpoint, MCP tool, or CLI command** is added. `/api/auth/me` returns
`write_scope` and element/diagram reads now carry `collection_id` so the
frontend can hide edit/comment affordances the user can't use.

**because** scope is fundamentally a *write*-authorization concern: gating
writes (a few dozen endpoints, all already authenticated) is tractable and
leaves the anonymous-read model intact, whereas filtering reads would mean
flipping the whole deployment to auth-required and touching ~10 read modules for
no security gain. Keeping assignment in Supabase matches how users + roles are
already administered and keeps the surface-parity contract untouched.

## Consequences
- A scoped user edits content (sets, packages, diagrams, elements, comments,
  tags, images) only inside their assigned collections; elsewhere the API
  returns `403` and the UI hides the affordances + the comments panel.
- Scoped users cannot create or delete collections, nor write global templates,
  even inside their scope — they work *within* assigned collections, not on the
  containers.
- PAT and OAuth callers are gated automatically (they resolve through the same
  `get_current_user`).
- No schema-dependent read path changes; existing deployments behave exactly as
  before until scope rows are added for a user.

## Alternatives considered
- **Postgres Row-Level Security**: rejected — the backend connects via a
  trusted service/direct connection that bypasses RLS, and RLS has no SQLite
  analogue, so it wouldn't enforce through the app's data path.
- **A new "access" role**: rejected — scope is orthogonal to the role; bolting it
  onto a role would duplicate the permission matrix and still need the junction.
- **Filtering reads too (auth-required deployment)**: rejected for now — large
  blast radius (~10 read modules + closing anonymous browsing) for no benefit,
  since the ask is to confine *edits*. Revisit if private read scoping is needed.
- **A FastAPI dependency factory** instead of in-route helper calls: rejected —
  the target collection is only known inside each route (resolved from a body
  field or path id), so a factory would need the same async resolution plus more
  glue.

## Surface parity (§14) / §15
No write endpoints, MCP tools, or CLI commands are added — `check_surface_parity`
stays green (verified). The migration ships as a SQLite/Supabase pair
(`m082_user_collection_scope.py` / `m088_user_collection_scope.sql`) with a
schema-mirror test; `user_id` references `users(id)` on SQLite and `profiles(id)`
on Supabase. Service/authz code uses positional row access.

## Dependencies
Builds on ADR-123 (anonymous reads), ADR-005 (RBAC roles), ADR-158
(set→collection), ADR-191 (element templates), ADR-209 (entity images).
Spec: `docs/adrs/specs/SPEC-237-A-Per-User-Collection-Write-Scope.md`.
