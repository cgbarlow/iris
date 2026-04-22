# SPEC-129-A: Public HTTP API Stabilisation

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-129-A |
| **ADR** | [ADR-129](../ADR-129-Public-HTTP-API-Stabilisation.md) |
| **Status** | Proposed |
| **Date** | 2026-04-22 |

## Overview

OpenAPI always-on under `/api/docs`; per-auth-type rate-limit
buckets; router tags and descriptions enriched for discoverability;
AI file-extract switched to optional-auth for parity with other AI
endpoints.

## Changes

### 1. OpenAPI docs always-on

Modify `backend/app/main.py`:

```python
app = FastAPI(
    title="Iris API",
    description=API_DESCRIPTION,
    version=__version__,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)
```

- The `debug` gate on `docs_url` is removed.
- Paths moved from `/docs` → `/api/docs`, `/redoc` → `/api/redoc`,
  `/openapi.json` → `/api/openapi.json`.
- `API_DESCRIPTION` is a multi-line string describing auth (JWT for
  the frontend, PATs for programmatic callers), rate limits, and a
  link to `docs/api.md` in the repo.

Backwards-compat: the frontend does not consume `/docs` — only
developers and agents do. No migration required.

### 2. Router tags and descriptions

Every router gets a tag and a description:

```python
app.include_router(search_router, prefix="/api/search", tags=["Search"])
app.include_router(diagrams_router, prefix="/api/diagrams", tags=["Diagrams"])
app.include_router(elements_router, prefix="/api/elements", tags=["Elements"])
app.include_router(packages_router, prefix="/api/packages", tags=["Packages"])
app.include_router(sets_router, prefix="/api/sets", tags=["Sets"])
app.include_router(collections_router, prefix="/api/collections", tags=["Collections"])
app.include_router(ai_router, prefix="/api/ai", tags=["AI"])
app.include_router(export_router, prefix="/api/export", tags=["Export"])
app.include_router(tokens_router, prefix="/api/users/me/tokens", tags=["Tokens"])
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
# ...
```

Per-endpoint `summary` and `description` are added where missing.
Target: every endpoint in scope for the CLI / MCP has a 1–3 line
description that a reader of `/api/docs` can use without reading
source.

### 3. Rate-limit buckets (extends ADR-123 / SPEC-127-A)

Authoritative bucket selection (duplicated here for completeness;
implemented in `middleware/rate_limit.py`):

```python
def _get_rate_category(request: Request) -> str:
    path = request.url.path
    if path == "/api/auth/login":
        return "login"
    if path == "/api/auth/refresh":
        return "refresh"
    auth = request.headers.get("Authorization", "")
    is_anon = not auth
    if path.startswith("/api/ai/") and is_anon:
        return "anon_ai"
    if auth.startswith("Bearer iris_pat_"):
        return "pat"
    if is_anon:
        return "anon"
    return "general"
```

Buckets are independent — filling the `anon` bucket does not affect
`pat` or `general`.

Defaults (see SPEC-127-A for the full table). All overridable via env.

### 4. Deprecation policy

Documented in `docs/api.md` (new file):

> Iris endpoints are unversioned. Additive changes (new endpoints,
> new optional fields, new response fields) are made freely.
> Breaking changes ship as a new path suffixed `-v2` (or `-v{n}`)
> while the old path continues to respond for at least one minor
> release, carrying `Deprecation: <date>` and `Sunset: <date>`
> headers per RFC 9745 / RFC 8594.

Backend implementation aid: a `@deprecated(sunset="2026-10-01")`
decorator in `backend/app/common/deprecation.py` that adds the
headers to every response of a decorated endpoint. Test fixture
enforces that any path matching `-v\d+$` has a non-versioned sibling
carrying the `Deprecation` header.

### 5. AI file-extract auth parity

Modify `backend/app/ai/router.py`:

```python
@router.post("/files/extract")
async def extract_file(
    file: UploadFile = File(...),
    current_user: dict | None = Depends(get_optional_user),  # was get_current_user
) -> FileExtractResponse: ...
```

Anonymous calls are subject to the `anon_ai` rate-limit bucket (no
code change — the middleware already categorises them because the
path begins with `/api/ai/`).

## Docs page

New `docs/api.md`:

- Auth: link to `/api/docs`, explain JWT vs PAT. Link to ADR-127.
- Rate limits: table of buckets and defaults.
- Deprecation policy: the text above.
- Quickstart: `curl` + Python `iris-client` + MCP config snippets.

## Testing (TDD)

### Backend

- `test_openapi_accessible_in_non_debug` — boot app with
  `config.debug=False`; `GET /api/openapi.json` returns 200.
- `test_openapi_has_all_tags` — schema includes tags Search,
  Diagrams, Elements, Packages, Sets, Collections, AI, Export,
  Tokens, Auth.
- `test_file_extract_anonymous` — `POST /api/ai/files/extract`
  without Authorization returns 200 (subject to rate-limit).
- `test_deprecated_decorator_sets_headers` — decorated endpoint
  returns `Deprecation` and `Sunset` headers.
- `test_v2_path_requires_v1_deprecation_header` — a CI meta-test
  that scans the OpenAPI for `-v\d+` paths and ensures siblings
  carry the headers.

## Acceptance criteria

1. `/api/docs` loads in production builds and shows every router
   grouped by tag.
2. `/api/openapi.json` is valid OpenAPI 3.1 and contains schemas
   for every endpoint in scope.
3. `POST /api/ai/files/extract` works anonymously.
4. Rate-limit buckets are independent; filling one does not affect
   the others (verified by test).
5. `docs/api.md` exists and documents auth, rate-limits, and the
   deprecation policy.
