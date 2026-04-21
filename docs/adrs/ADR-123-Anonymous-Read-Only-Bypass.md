# ADR-123: Anonymous Read-Only Bypass

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-123 |
| **Initiative** | Access Control |
| **Proposed By** | Engineering |
| **Date** | 2026-04-21 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** Iris's current auth model — every frontend route
(except `/login`) redirects to `/login` if no JWT is present in
sessionStorage, and every backend endpoint (except `/health` and the
three `/api/auth/*` bootstrap routes) depends on
`get_current_user()`, which raises 401 when no `Authorization: Bearer`
header is sent — so the first interaction a new visitor has with the
deployed UAT instance (`iris-uat.chrisbarlow.nz`) is a credential
prompt,

**facing** GitHub issue #18: "by default, Iris will bypass the login
screen and show a read-only view of Iris" — the intent being that
anonymous visitors see the app's content (collections, sets, packages,
diagrams, elements, knowledge graph, search, bookmarks) and can use
Ask AI, but cannot perform any write action and cannot see admin
surfaces,

**we decided for** **optional authentication on read paths** with
**mandatory authentication on write paths**:
- Backend adds `get_optional_user()` — a FastAPI dependency that
  returns the authenticated user if a valid token is present, returns
  `None` if no `Authorization` header at all, and raises 401 on an
  *invalid* token (so anonymous ≠ "valid user with no claims"). Every
  GET route on `collections`, `sets`, `packages`, `diagrams`,
  `elements`, `graph`, `search`, `bookmarks`, and `ai` switches from
  `get_current_user` to `get_optional_user`. Every POST/PUT/PATCH/
  DELETE route and every admin router (`users`, `audit`, `locks`,
  `settings`) keeps `get_current_user` or `require_permission(...)`
  and continues to reject anonymous callers.
- A new rate-limit category `anon_ai` (default 10/hour per IP, env
  `IRIS_RATE_LIMIT_ANON_AI`) is applied by the existing sliding-
  window middleware when an AI request arrives without an
  Authorization header. Authenticated AI requests keep the existing
  `general` bucket.
- Frontend `+layout.svelte` stops redirecting unauthenticated users
  to `/login`; AppShell renders for everyone. A new
  `isAnonymous()` helper in `auth.svelte.ts` drives per-component
  hiding of write UI (create/edit/delete buttons, forms, drag-to-
  rearrange affordances) and swap-in of a "Sign in" call-to-action.
  Admin routes keep their login gate in the admin layout (not the
  root layout), so visiting `/admin/users` anonymously still redirects
  to `/login`,

**and neglected** (a) a curated "demo mode" showing only a landing-
page preview — the user explicitly asked for read-only of everything;
(b) a new "anonymous" role row in the `roles` table — anonymity is
the *absence* of a user, and inventing a pseudo-user complicates
audit logs, ownership semantics, and the JWT refresh path; (c)
making the login redirect configurable via an env var — everybody
who deploys UAT needs read-only open, and admin routes still
redirect, so there is no regression for private installs; (d)
expiring anonymous Ask AI sessions server-side via tokens — per-IP
rate limiting covers the cost exposure concern without adding
server-side state; (e) disabling Ask AI for anonymous callers
entirely — the user specifically opted into "read-only + Ask AI"
with rate limiting as the cost guardrail,

**to achieve** a UAT experience where a first-time visitor can see
what Iris does and play with the knowledge graph, search, and Ask AI
without a credential prompt — while the deployed instance continues
to refuse every write and every admin view unless properly
authenticated,

**accepting that** anonymous read access means every deployed set,
package, diagram, and element on UAT becomes publicly browsable —
the user's current UAT data is test/demo material and this is the
explicit intent; any future private-data deployment would need a
per-deployment feature flag (deferred); accepting that per-IP Ask
AI rate limiting is imperfect (shared NAT, rotating IPs) but
bounded-enough for the cost exposure on UAT's small Anthropic
budget; accepting that the auth-dependency change touches every
read router (roughly eight files) and each needs a one-line `Depends`
swap; accepting that the frontend now has an `isAnonymous()` branch
on every write-UI component and the per-page add was not minimised
into a single layout directive (write UI is context-dependent and
lives on per-page buttons, so a layout-level directive wouldn't
catch all sites).

---

## Summary

| Capability | Description | Specification |
|------------|-------------|---------------|
| Anonymous Read-Only Bypass | `get_optional_user()` backend dependency plus per-router application. Rate-limit category `anon_ai` for unauthenticated AI calls. Frontend `isAnonymous()` helper; login redirect removed from root layout; admin routes keep theirs. Write UI hidden when anonymous; "Sign in" button shown in AppShell. | [SPEC-123-A](./specs/SPEC-123-A-Anonymous-Read-Only-Bypass.md) |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Refines | ADR-005 | Auth & Rate-Limiting (if present; else ADR-116) | Current auth is "every route requires auth"; this splits reads from writes. |
| Coordinates | ADR-122 | User Guide | The Guide nav item appears in the anonymous AppShell variant. |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-123-A | Anonymous Read-Only Bypass | Technical Specification | [specs/SPEC-123-A-Anonymous-Read-Only-Bypass.md](./specs/SPEC-123-A-Anonymous-Read-Only-Bypass.md) |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Engineering | 2026-04-21 |
| Approved | Engineering | 2026-04-21 |
