# SPEC-164-A: OAuth 2.1 Authorization Server + Protected Resource for iris-mcp

ADR: [ADR-164](../ADR-164-OAuth-2.1-for-MCP.md)

## Database

### SQLite migration `m054_oauth_tables.py`

```sql
-- v5.15.0 pairing remnant — dropped in v6.0.0 (ADR-164).
DROP TABLE IF EXISTS pairing_codes;

CREATE TABLE IF NOT EXISTS oauth_clients (
    client_id TEXT PRIMARY KEY,
    client_secret_hash TEXT,
    client_name TEXT NOT NULL,
    redirect_uris TEXT NOT NULL,  -- JSON array of strings
    grant_types TEXT NOT NULL DEFAULT '["authorization_code","refresh_token"]',
    token_endpoint_auth_method TEXT NOT NULL DEFAULT 'none',
    created_at TEXT NOT NULL,
    last_used_at TEXT
);

CREATE TABLE IF NOT EXISTS oauth_authorization_codes (
    code TEXT PRIMARY KEY,
    client_id TEXT NOT NULL REFERENCES oauth_clients(client_id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    redirect_uri TEXT NOT NULL,
    code_challenge TEXT NOT NULL,
    code_challenge_method TEXT NOT NULL DEFAULT 'S256',
    scope TEXT NOT NULL DEFAULT 'iris',
    expires_at TEXT NOT NULL,
    used_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_oauth_codes_expires ON oauth_authorization_codes(expires_at);

CREATE TABLE IF NOT EXISTS oauth_refresh_tokens (
    id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL REFERENCES oauth_clients(client_id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    family_id TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    used_at TEXT,
    revoked INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_oauth_refresh_user ON oauth_refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_oauth_refresh_family ON oauth_refresh_tokens(family_id);
```

Idempotent on both backends.

### Supabase migration `m058_oauth_tables.sql`

Mirrors SQLite shape with `TIMESTAMPTZ` instead of `TEXT`, `UUID` references to `profiles(id)` instead of `users(id)`, and `BOOLEAN` instead of `INTEGER` for `revoked`. RLS enabled with owner-only policies on `oauth_refresh_tokens` (service role bypasses RLS for the token endpoint). `oauth_clients` is admin-managed; service role manages.

## Backend — OAuth Authorization Server

### Module layout: `backend/app/oauth/`

```
backend/app/oauth/
├── __init__.py
├── models.py     # Pydantic shapes
├── service.py    # DCR, code issuance, PKCE, JWT minting, refresh rotation
├── router.py     # endpoint handlers
└── pkce.py       # S256 challenge verification
```

### Endpoints

| Path | Method | Auth | Body / Query |
|---|---|---|---|
| `GET /.well-known/oauth-authorization-server` | GET | none | — |
| `POST /oauth/register` | POST | none | RFC 7591 client metadata |
| `GET /oauth/authorize` | GET | session | query: `response_type=code`, `client_id`, `redirect_uri`, `code_challenge`, `code_challenge_method=S256`, `state`, `scope=iris` |
| `POST /oauth/authorize/decision` | POST | session | body: `{decision: "allow"\|"deny", request_id: str}` (request_id pins a server-side cached request) |
| `POST /oauth/token` | POST | client | body: `grant_type=authorization_code` + `code` + `code_verifier` + `client_id` + `redirect_uri` OR `grant_type=refresh_token` + `refresh_token` + `client_id` |
| `POST /oauth/revoke` | POST | client | body: `token` + `token_type_hint=refresh_token` |

### Authorization Server metadata (RFC 8414)

```json
{
  "issuer": "https://iris-uat.chrisbarlow.nz",
  "authorization_endpoint": "https://iris-uat.chrisbarlow.nz/oauth/authorize",
  "token_endpoint": "https://iris-uat.chrisbarlow.nz/oauth/token",
  "registration_endpoint": "https://iris-uat.chrisbarlow.nz/oauth/register",
  "revocation_endpoint": "https://iris-uat.chrisbarlow.nz/oauth/revoke",
  "scopes_supported": ["iris"],
  "response_types_supported": ["code"],
  "grant_types_supported": ["authorization_code", "refresh_token"],
  "code_challenge_methods_supported": ["S256"],
  "token_endpoint_auth_methods_supported": ["none", "client_secret_basic"]
}
```

### Access token (JWT)

```python
{
  "sub": "<user_id>",
  "aud": "iris-mcp",
  "azp": "<client_id>",
  "scope": "iris",
  "iat": <issued>,
  "exp": <issued + 3600>,
  "jti": "<uuid>"
}
```

HS256, signed with existing `AuthConfig.jwt_secret`. Validated by `get_current_user` (unchanged — already accepts JWTs; new claims like `aud`/`azp` are tolerated).

### Refresh token

Opaque random 32-byte URL-safe string. Stored in `oauth_refresh_tokens` with:
- `family_id` — shared across all refresh tokens in a rotation chain. If a used refresh is presented again, the entire family is revoked (theft detection — same pattern as v5.x `refresh_tokens`).
- 14-day expiry.
- Single-use: presenting it returns a new pair AND marks the old as `used_at = now`, `revoked = 1`.

### PKCE (S256)

`code_challenge = base64url(sha256(code_verifier))`. On `/oauth/token` exchange, recompute and compare in constant time. Reject on mismatch.

### Backend tests

| File | Cases |
|---|---|
| `tests/test_oauth/test_metadata.py` | 3 — `/.well-known/oauth-authorization-server` returns required fields; correct `issuer`; anonymous-readable |
| `tests/test_oauth/test_register.py` | 4 — happy DCR; missing redirect_uris → 422; reused registration creates new client_id; client_secret returned only when token_endpoint_auth_method=client_secret_basic |
| `tests/test_oauth/test_authorize.py` | 5 — unauth → redirect to `/login?redirect=...`; authed + valid request → consent screen; invalid client_id → 400; redirect_uri mismatch → 400; decision allow → code + state; decision deny → error=access_denied |
| `tests/test_oauth/test_token.py` | 7 — code grant with PKCE happy path; PKCE mismatch → invalid_grant; expired code → invalid_grant; reused code → invalid_grant; refresh rotation issues new pair; reused refresh revokes family; cross-client refresh rejected |
| `tests/test_oauth/test_revoke.py` | 2 — revoke marks token revoked; revoked token can't refresh |
| `tests/test_migrations/test_oauth_tables_schema.py` | 4 — SQLite m054 creates all 3 tables + drops pairing_codes; Supabase m058 mirrors; foreign keys present; indexes present |
| `tests/test_auth/test_get_current_user_oauth.py` | 3 — OAuth-issued JWT passes get_current_user; legacy /api/auth/login JWT still passes; PAT still passes |

**Total backend**: ~28 tests.

## iris-mcp — Protected Resource

### `mcp/src/iris_mcp/oauth_resource.py`

Pydantic model + FastAPI route:

```python
# RFC 9728 Protected Resource metadata
@app.get("/.well-known/oauth-protected-resource")
async def protected_resource_metadata():
    return {
        "resource": f"https://{host}",
        "authorization_servers": [iris_url],
        "scopes_supported": ["iris"],
        "bearer_methods_supported": ["header"]
    }
```

### `mcp/src/iris_mcp/asgi.py` — 401 with `WWW-Authenticate`

When `mcp_asgi` catches a 401 from the per-request handler, add a `WWW-Authenticate: Bearer resource_metadata="https://<host>/.well-known/oauth-protected-resource", error="invalid_token"` header to the response. The MCP spec defines this header as the signal that triggers a client OAuth dance.

### Tool description preamble update

Every write tool's description gets a new `_AUTH_GUIDANCE` block that **replaces** the v5.15.0 pairing-recovery text:

```
This tool writes to Iris and requires authentication via OAuth.

If you receive error="auth_required", advise the user (do not call
any auth-related tool — there isn't one):

  "Iris writes need OAuth set up for this MCP connector. In your
  MCP client's connector settings (e.g. claude.ai → Connectors →
  Iris → Configure), enable OAuth — your browser will open a
  consent screen, you sign in to Iris, and writes work from then on."
```

Applied to: `create_collection`, `create_set`, `create_package`, `create_diagram`.

### Tool removal

- `iris_authenticate` handler + Tool entry — deleted entirely.
- `save_doview_analysis` handler + Tool entry — deleted entirely.
- `_auth_required_payload(action)` rewrites: payload message no longer mentions pairing or `iris_authenticate`. New shape:
  ```json
  {
    "success": false,
    "error": "auth_required",
    "message": "<oauth-guidance text>",
    "next_step": "configure_oauth_in_connector_settings",
    "oauth_resource_metadata_url": "https://<iris-mcp-host>/.well-known/oauth-protected-resource"
  }
  ```

### Stripped files / modules

- `mcp/src/iris_mcp/token_store.py` — deleted.
- `mcp/src/iris_mcp/__main__.py:_resolve_token` — simplified to `token = config.token or None` (just IRIS_TOKEN env var, no file fallback).

### iris-mcp tests

| File | Cases |
|---|---|
| `tests/test_oauth_resource.py` | 3 — metadata endpoint returns RFC 9728 shape; correct AS URL; correct scopes |
| `tests/test_tools_inventory.py` (existing) | +3 negative assertions — `iris_authenticate` absent from `tool_definitions()`; `save_doview_analysis` absent; auth_required payload includes `oauth_resource_metadata_url` |
| `tests/test_asgi_www_authenticate.py` | 3 — 401 response includes `WWW-Authenticate: Bearer resource_metadata="..."`; other status codes don't; header URL matches the deployed host |

**Total iris-mcp**: ~9 new tests; old `tests/test_tools_authenticate.py` + `tests/test_token_store.py` deleted (~17 tests removed).

## iris-client

Remove:
- `IrisClient.create_pairing_code`
- `IrisClient.exchange_pairing_code`
- `IrisClient.set_token`
- `PairingCodeResponse`
- `ExchangedPATResponse`

Delete `tests/test_pairing_codes.py`.

## Frontend

### New page `frontend/src/routes/oauth/authorize/+page.svelte`

Consent screen. Loaded by SvelteKit when backend's `/oauth/authorize` GET (after session check) renders this route. Props from query string + a server-side-rendered consent payload.

```svelte
<script lang="ts">
    import DOMPurify from 'dompurify';
    import { page } from '$app/state';
    import { apiFetch } from '$lib/utils/api';

    let consent = $derived(/* fetched on load */);
    const safeClientName = $derived(DOMPurify.sanitize(consent.client_name));

    async function decide(allow: boolean) {
        const result = await apiFetch('/oauth/authorize/decision', {
            method: 'POST',
            body: JSON.stringify({ request_id: consent.request_id, decision: allow ? 'allow' : 'deny' }),
        });
        window.location.href = result.redirect_to;
    }
</script>

<svelte:head><title>Authorize MCP client — Iris</title></svelte:head>
<h1>Authorize MCP client</h1>
<p>{@html safeClientName} wants to access Iris on your behalf as <strong>{username}</strong>.</p>
<p>This grants the scope <code>iris</code> (full access to your Iris data).</p>
<button onclick={() => decide(true)}>Allow</button>
<button onclick={() => decide(false)}>Deny</button>
```

### Removed

- `frontend/src/routes/settings/mcp-pairing/` directory entirely.
- "MCP Connections" section in `frontend/src/routes/settings/+page.svelte`.
- `frontend/tests/unit/mcpPairing.test.ts` — deleted.

### Frontend tests `frontend/tests/unit/oauthConsentScreen.test.ts`

| Case | Description |
|---|---|
| 1 | Consent screen renders DCR-supplied `client_name` (sanitised) |
| 2 | Allow button posts decision with `request_id` |
| 3 | Deny button posts decision with `decision=deny` |
| 4 | Missing query params shows error state |
| 5 | DOMPurify strips a malicious `<script>` tag in client_name |
| 6 | "MCP Connections" section absent from `/settings/+page.svelte` source (negative test) |

## Documentation

- **ADR-164** — design rationale (this ADR).
- **SPEC-164-A** — this spec.
- **README** — rewrite iris-mcp setup section. OAuth-first for HTTP; `IRIS_TOKEN` env var as the stdio fallback.
- **`docs/prompts/mcp-server-instructions.md`** — AUTH RECOVERY section rewritten for OAuth.

## End-to-end verification

After UAT deploy + Supabase migration:

1. Configure iris-mcp UAT as a claude.ai connector. claude.ai auto-DCRs and initiates OAuth.
2. Browser opens `/oauth/authorize`. Sign in to Iris if needed. Consent screen renders correct client_name. Click Allow.
3. Browser redirected back to claude.ai with `?code=...&state=...`. claude.ai exchanges via `/oauth/token` and gets `{access_token, refresh_token}`.
4. From claude.ai, use Iris: search, get diagrams, create diagram. All requests carry the OAuth access token in the bearer header.
5. Write tool with expired/invalid bearer: response carries `WWW-Authenticate: Bearer resource_metadata="..."`. claude.ai initiates token refresh; if refresh fails (e.g. user revoked), claude.ai surfaces the OAuth dance again.
6. Pairing endpoints return 404. `/settings/mcp-pairing` page returns 404.

## Out of scope (deferred)

- OAuth on stdio transport — env-var bearer remains the pattern.
- OpenID Connect.
- Scope refinement beyond `iris`.
- RS256 + JWKS.
- Admin UI for revoking OAuth clients / sessions — v6.1+.
