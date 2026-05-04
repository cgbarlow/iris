# ADR-129: Public HTTP API Stabilisation

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-129 |
| **Initiative** | Agentic-AI-friendly API (Issue #21) |
| **Proposed By** | Engineering |
| **Date** | 2026-04-22 |
| **Status** | Proposed |

---

## ADR (WH(Y) Statement format)

**In the context of** the FastAPI backend exposing `/docs` (Swagger
UI) and `/redoc` at the root of the app only when `config.debug` is
true (see `app/main.py:83`) — which means the production UAT
deployment at `iris-uat.chrisbarlow.nz` serves no OpenAPI at all;
endpoints are unversioned (`/api/...` not `/api/v1/...`); router tags
are sparse; anonymous AI calls go through a dedicated `anon_ai`
rate-limit bucket (per ADR-123) but every other authenticated request
(JWT today, PAT as of ADR-127) shares a single `general` bucket
tuned for a browser session, not an agent's burst of search calls,

**facing** the need — from Issue #21 — for the HTTP API itself to be
a **first-class, externally discoverable surface** alongside the CLI
(ADR-130) and MCP server (ADR-131), which requires that (a) OpenAPI
docs are visible at a predictable URL in every deployment (local, UAT,
prod) so agents can introspect the schema without running the
backend in debug; (b) each router has enough description metadata
that generated docs are actually usable; (c) rate-limits can be
tuned per auth type (anon / PAT / JWT) because agents authenticated
with a PAT will hit the API harder than a human browser and should
not starve browser traffic or vice versa; (d) the "what happens if an
endpoint changes" question has a stated answer that agents and SDK
consumers can plan against,

**we decided for** (a) **moving OpenAPI to `/api/docs` (Swagger UI)
and `/api/openapi.json` (raw schema), always-on in every environment**
— the existing `debug`-gated `/docs` endpoint is removed, replaced by
the `/api/`-prefixed routes so agents / MCP tooling / `datamodel-code-generator`
can fetch the schema from a live server; no secrets are shipped in
the schema, and `HEAD` health checks remain at `/api/health`;
(b) **enriching router tags and descriptions** so every public router
has a Title-Case tag name (`Search`, `Diagrams`, `AI`, `Export`,
`Tokens`, …) and a 1–3 line description visible in Swagger — a
mechanical change, applied as each router ships new capabilities;
(c) **splitting the rate-limit bucket by auth type** in
`middleware/rate_limit.py`: `anon` (no credentials), `anon_ai`
(anonymous AI — retained from ADR-123), `pat` (PAT-authenticated),
`general` (JWT-authenticated), plus the existing `login` and `refresh`
buckets — the bucket for a given request is chosen inside the
middleware based on `Authorization` header and path prefix; defaults
are tuned so authenticated callers get higher ceilings than anonymous
ones, and `pat` sits between `general` and `anon` by default;
(d) **keeping the API unversioned** (`/api/...`) and publishing an
explicit **deprecation policy**: breaking changes require a new path
(`/api/...v2` per-endpoint where needed) and a deprecation header
(`Deprecation: <date>`, `Sunset: <date>`) served for at least one
minor release before removal; additive changes (new endpoints, new
optional fields) are free; this matches how the repo has evolved so
far and avoids a v1→v2 migration on day one;
(e) **AI file-extract anon parity** — `POST /api/ai/files/extract`
currently requires a JWT (`Depends(get_current_user)`); switch it to
`Depends(get_optional_user)` so anonymous callers can use it subject
to the `anon_ai` rate-limit bucket, matching the other AI endpoints
that ADR-123 already made anonymous-friendly,

**and neglected** (a) **full URL versioning (`/api/v1/...`)** —
"correct" answer from a textbook but requires migrating every
existing client (the SvelteKit frontend, the `iris-client` library)
on day one for no immediate benefit; the deprecation-header policy
achieves the same guarantee with zero code churn; (b) **a dedicated
public subdomain (`api.iris.example.com`)** — a deployment concern
orthogonal to this ADR; may be adopted later without changing paths;
(c) **OAuth authorisation code flow in Swagger's "Authorize"
dialog** — useful for interactive testing but requires a full
OAuth2 server; Swagger's bearer-token field covers both JWT and PAT
use without any new backend surface; (d) **rate-limit per-user
budgets** (e.g. 10,000 calls per day per PAT) — valuable for hostile
multi-tenant deployments but premature for v1 where every PAT
belongs to a trusted logged-in user; (e) **GraphQL** — explicitly
out of scope; agents get plenty of leverage from the REST surface +
server-side export bundles,

**to achieve** an API that is usable from a cold start without debug
mode, documentation that makes the surface self-serve, rate-limits
that let each auth type be tuned without coupling, a clear forward-
compatibility story that does not force a v1/v2 migration, and parity
between all AI endpoints on anonymous access,

**accepting that** shipping `/api/docs` in production exposes the
full endpoint list to the internet — not a leak (every endpoint is
already discoverable via 404-vs-200 probing) but it does advertise
surface area; acceptable under ADR-123's public-by-default posture;
accepting that the deprecation-header policy depends on humans
remembering to set the headers — mitigated by a test that fails if
a `*-v2` path ships without its sibling `v1` having headers;
accepting that PATs and JWTs share the same audit trail (the existing
audit log) and are only distinguished by the `jti` shape (PAT jti is
the PAT id; JWT jti is the JWT jti) — fine for v1.

---

## Summary

| Capability | Description | Specification |
|------------|-------------|---------------|
| OpenAPI always-on | `/api/docs` (Swagger UI) + `/api/openapi.json` (raw) in every environment. `debug`-gated `/docs` removed. | [SPEC-129-A](./specs/SPEC-129-A-Public-API-Stabilisation.md) |
| Router tags + descriptions | Every public router gets a Title-Case tag and a 1–3 line description. Applied mechanically as routers ship. | SPEC-129-A |
| Rate-limit buckets by auth type | `anon` / `anon_ai` / `pat` / `general` / `login` / `refresh`. Bucket chosen in middleware from `Authorization` header + path. | SPEC-129-A |
| Deprecation policy | Breaking changes → `-v2` path + `Deprecation` / `Sunset` headers on old path for ≥ 1 minor release. Additive changes free. | SPEC-129-A |
| AI file-extract anon parity | `POST /api/ai/files/extract` switched from `get_current_user` to `get_optional_user`. Subject to `anon_ai` bucket. | SPEC-129-A |

---

## Dependencies

| Relationship | ADR ID | Title | Notes |
|--------------|--------|-------|-------|
| Depends On | ADR-123 | Anonymous Read-Only Bypass | Rate-limit buckets extend the `anon_ai` bucket introduced there. |
| Depends On | ADR-127 | Personal Access Tokens | `pat` bucket is for PAT-authenticated requests. |
| Enables | ADR-130 | CLI Architecture | CLI reads `/api/openapi.json` as reference; `iris-client` schemas are generated from it. |
| Enables | ADR-131 | MCP Server Architecture | MCP tool schemas derive from the same OpenAPI. |
| Enables | ADR-132 | Shared Python Client Library | Schema generation pipeline targets `/api/openapi.json`. |

---

## References

| Reference ID | Title | Type | Location |
|--------------|-------|------|----------|
| SPEC-129-A | Public API Stabilisation Implementation | Technical Specification | [specs/SPEC-129-A-Public-API-Stabilisation.md](./specs/SPEC-129-A-Public-API-Stabilisation.md) |

---

## Status History

| Status | Approver | Date |
|--------|----------|------|
| Proposed | Engineering | 2026-04-22 |
