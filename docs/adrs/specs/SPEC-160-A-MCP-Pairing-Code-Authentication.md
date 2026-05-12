# SPEC-160-A: MCP pairing-code authentication

ADR: [ADR-160](../ADR-160-MCP-Pairing-Code-Authentication.md)

## Database

### SQLite (migration `m052_mcp_pairing_codes.py`)

```sql
CREATE TABLE IF NOT EXISTS pairing_codes (
    code            TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at      TEXT NOT NULL,
    expires_at      TEXT NOT NULL,
    exchanged_at    TEXT,
    issued_pat_id   TEXT,
    issued_pat_name TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pairing_codes_user ON pairing_codes(user_id);
CREATE INDEX IF NOT EXISTS idx_pairing_codes_expires ON pairing_codes(expires_at);
```

Idempotent; safe to re-run.

### Supabase / Postgres (migration `m056_mcp_pairing_codes.sql`)

```sql
CREATE TABLE IF NOT EXISTS public.pairing_codes (
    code            TEXT PRIMARY KEY,
    user_id         UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ NOT NULL,
    exchanged_at    TIMESTAMPTZ,
    issued_pat_id   UUID,
    issued_pat_name TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pairing_codes_user ON public.pairing_codes(user_id);
CREATE INDEX IF NOT EXISTS idx_pairing_codes_expires ON public.pairing_codes(expires_at);
ALTER TABLE public.pairing_codes ENABLE ROW LEVEL SECURITY;
-- Same posture as personal_access_tokens: backend uses service_role for
-- the anonymous /exchange endpoint (service role bypasses RLS).
```

## Code format

`IRIS-XXXX-YYYY` — 8 base32 characters from the Crockford alphabet excluding `I`, `L`, `O`, `U` (to avoid ambiguity with 1/L/0/U). Two 4-character groups separated by a hyphen for readability. ~40 bits of entropy.

Generation: `secrets.choice` against `"ABCDEFGHJKMNPQRSTVWXYZ23456789"` (28 characters, ≈4.8 bits/char × 8 = ~38.5 bits).

## Backend

### Module layout

```
backend/app/auth/pairing/
├── __init__.py
├── models.py     # Pydantic models for request / response shapes
├── service.py    # Code generation, expiry, exchange (calls tokens.service.create_token)
└── router.py     # FastAPI router mounted at /api/auth/pairing-codes
```

### Endpoints

| Method | Path | Auth | Body | 2xx response | Error codes |
|---|---|---|---|---|---|
| `POST` | `/api/auth/pairing-codes` | JWT or PAT | `{}` (optional `client_hint?: str`) | `{code: str, expires_at: ISO-8601 str}` | 401 (unauth), 429 (per-user rate) |
| `POST` | `/api/auth/pairing-codes/{code}/exchange` | None | (empty) | `{token: str, prefix: str, expires_at: ISO-8601 str, mode: "pairing_code"}` | 410 (gone — invalid/expired/already-exchanged), 429 (per-IP rate) |

**Behaviour:**

- `POST /api/auth/pairing-codes`:
  - Generate `code` (regenerate up to 5 times on PK collision).
  - Insert row with `expires_at = now() + 10 minutes`, `issued_pat_name = f"MCP — {YYYY-MM-DD HH:MM} UTC" + (f" — {client_hint}" if client_hint else "")`.
  - Purge oldest unexchanged codes for this user if they have more than 5 outstanding.
  - Return `{code, expires_at}`.

- `POST /api/auth/pairing-codes/{code}/exchange`:
  - Look up row by primary key.
  - If `code` not found → 410.
  - If `exchanged_at IS NOT NULL` → 410 (already used).
  - If `expires_at <= now()` → 410 (expired).
  - Otherwise: call `tokens.service.create_token(db, user_id=row.user_id, name=row.issued_pat_name, expires_at=now()+90 days, hasher)`.
  - Update row: `exchanged_at = now()`, `issued_pat_id = pat.id`.
  - Return `{token, prefix, expires_at, mode: "pairing_code"}`.

**Cleanup**: opportunistic — every `POST /api/auth/pairing-codes` call deletes rows with `expires_at < now() - 1 day` (cheap, indexed). No background job.

### Pydantic models (`backend/app/auth/pairing/models.py`)

```python
class CreatePairingCodeRequest(BaseModel):
    client_hint: str | None = None

class PairingCodeResponse(BaseModel):
    code: str
    expires_at: str  # ISO-8601 UTC

class ExchangedPATResponse(BaseModel):
    token: str
    prefix: str
    expires_at: str  # ISO-8601 UTC
    mode: Literal["pairing_code"] = "pairing_code"
```

### Reuse

- `backend/app/tokens/service.py:create_token(db, user_id, name, expires_at, hasher)` — single source of truth for PAT issuance. Pairing exchange wraps this verbatim.
- `backend/app/auth/dependencies.py:get_current_user` — protects `POST /api/auth/pairing-codes`. The issued PAT plays through the same dependency on subsequent calls.
- `backend/app/config.py:AuthConfig.argon2_*` — the same hasher used for password / PAT hashing.

## iris-client

### Methods (`iris-client/src/iris_client/client.py`)

```python
async def create_pairing_code(
    self, client_hint: str | None = None
) -> PairingCodeResponse:
    """POST /api/auth/pairing-codes. Bearer auth required."""

async def exchange_pairing_code(
    self, code: str
) -> ExchangedPATResponse:
    """POST /api/auth/pairing-codes/{code}/exchange. Anonymous."""
```

### Models (`iris-client/src/iris_client/models/core.py`)

```python
class PairingCodeResponse(_Permissive):
    code: str
    expires_at: str

class ExchangedPATResponse(_Permissive):
    token: str
    prefix: str
    expires_at: str
    mode: str = "pairing_code"
```

## MCP server

### Token-storage helper (`mcp/src/iris_mcp/token_store.py`)

```python
def token_file_path(iris_url: str) -> Path:
    """~/.iris-mcp/<sha256(iris_url)[:16]>.json"""

def load_token(iris_url: str) -> str | None:
    """Read the persisted PAT for this Iris URL.
    Returns None if missing or if the stored `expires_at` is in the past.
    """

def save_token(
    iris_url: str,
    token: str,
    expires_at: str | None,
) -> None:
    """Write the token JSON with mode 0600. expires_at is the wall-clock
    UTC ISO-8601 string from the backend; None means 'backend-managed'
    (PAT-paste path: backend owns expiry, we store the token without
    a local expiry check)."""
```

File contents:
```json
{
  "iris_url": "https://iris-uat.chrisbarlow.nz",
  "token": "iris_pat_abcdef12_...",
  "expires_at": "2026-08-10T14:32:11+00:00"
}
```

Permissions: file mode 0600, parent directory mode 0700.

### New tool `iris_authenticate(credential: str)` (`mcp/src/iris_mcp/tools.py`)

Signature: `async def _iris_authenticate(credential: str) -> dict[str, Any]`.

Dispatch:
- `credential.startswith("iris_pat_")` → PAT-paste path.
- `credential.upper().startswith("IRIS-")` → pairing-code path. (Case-insensitive on input; users may have copy-pasted with the wrong case.)
- Otherwise → return `{"success": False, "error": "invalid credential — expected a pairing code (IRIS-XXXX-YYYY) or a PAT (iris_pat_...)."}` with no side effects.

**Pairing-code path**:
1. Normalise the code (`credential.strip().upper()`).
2. `c = IrisClient(url=config.url, token=None)` (anonymous — we don't want to send any existing token along).
3. `resp = await c.exchange_pairing_code(code)`.
4. `save_token(iris_url=config.url, token=resp.token, expires_at=resp.expires_at)`.
5. Update the long-lived `client.token` to the new PAT in-process so subsequent tool calls in the same MCP session use it.
6. Return `{success: True, mode: "pairing_code", expires_at: resp.expires_at, message: "Authenticated and persisted. Future MCP tool calls will use this token until <expires_at>. Revoke any time at <iris_url>/settings/tokens."}`.
7. Map a 410 from the exchange to `{success: False, error: "pairing code is invalid, expired, or already used — generate a new one at <iris_url>/settings/mcp-pairing"}`.

**PAT-paste path**:
1. `validation_client = IrisClient(url=config.url, token=credential.strip())`.
2. Try `await validation_client.get_me()` (existing `/api/auth/me`).
3. On 200 OK: `save_token(iris_url=config.url, token=credential.strip(), expires_at=None)`; update in-process `client.token`; return `{success: True, mode: "pat_paste", message: "PAT validated and persisted. Future MCP tool calls will use this token."}`.
4. On 401: return `{success: False, error: "PAT is invalid or revoked — verify at <iris_url>/settings/tokens"}`.

### Startup wiring (`mcp/src/iris_mcp/__main__.py`)

Order of precedence for the IrisClient bearer:
1. `IRIS_TOKEN` env var (explicit operator override).
2. `token_store.load_token(config.url)` if exists and not expired.
3. `None` (anonymous; only read-only tools work).

The MCP server logs which path supplied the credential at startup, e.g. `iris-mcp: using IRIS_TOKEN env var` / `iris-mcp: loaded token from ~/.iris-mcp/<hash>.json` / `iris-mcp: no token configured`. The token itself is never logged.

### Write-tool 401 handling (`mcp/src/iris_mcp/tools.py`)

When `_save_doview_analysis` (and any future write tool) catches a 401 from the backend, it returns a structured guidance message:

```text
Save to Iris failed — this MCP connection isn't authenticated yet.

To fix:
  1. Visit <IRIS_WEB_URL>/settings/mcp-pairing
  2. Click "Generate pairing code"
  3. Paste the code back here, and I'll call iris_authenticate.

(After that, this MCP connection stays authenticated for ~90 days
on this machine.)
```

`<IRIS_WEB_URL>` resolves from `IRIS_WEB_URL` env var (if set) or `config.url`. The text is identical whether or not Iris's `config.web_url` is configured — the URL substitution differs but the structure is constant so models can reliably extract the next-step instruction.

## Frontend

### Page: `frontend/src/routes/settings/mcp-pairing/+page.svelte`

User-self namespaced. Any logged-in user (regardless of role) can pair their own MCP. The page:

- Displays the page heading and short explanation of pairing.
- Has a primary action **Generate pairing code**.
- On click, POSTs to `/api/auth/pairing-codes` with empty body. On 2xx, displays the returned `code` in a large monospace font with a copy-to-clipboard button.
- Shows a live 10-minute countdown. When expired, clears the displayed code and shows "Code expired — generate a new one".
- Below the code: numbered instructions for the paste flow.
- Below that: smaller hint for the power-user PAT-paste fallback ("Already have a PAT? Paste it directly: `iris_authenticate('iris_pat_...')`. Manage existing PATs at `/settings/tokens`.").

State is held in `+page.svelte` only — no SvelteKit data loader. POSTs use the existing `apiFetch` wrapper.

### Sidebar nav

Add a "MCP Pairing" entry in the user-settings sidebar (the same nav surface that already surfaces `/settings/tokens`). Location: the user-settings layout file or whichever nav config the existing PAT page uses.

### Tests (`frontend/tests/unit/mcpPairing.test.ts`)

- Initial state shows the **Generate pairing code** button and no code.
- Clicking the button calls `fetch('/api/auth/pairing-codes', { method: 'POST', ... })` and displays the returned code.
- Copy button copies the code to the clipboard.
- 10-minute countdown advances; expiry clears the code.

## Tests

| File | Cases | Layer |
|---|---|---|
| `backend/tests/test_migrations/test_mcp_pairing_codes_schema.py` | 4 — table created; required columns present; user/expires indexes; idempotent on re-run | backend |
| `backend/tests/test_auth/test_pairing_codes.py` | 8 — create requires auth; create returns code+expires_at; exchange returns PAT+prefix+expires_at; exchange is one-shot (410 on reuse); 410 on expired; 410 on unknown code; exchanged PAT authenticates against /api/auth/me; per-user code purge at >5 outstanding | backend |
| `iris-client/tests/test_pairing_codes.py` | 4 — create_pairing_code; exchange_pairing_code; 410 mapping; permissive model tolerates extra fields | iris-client |
| `mcp/tests/test_token_store.py` | 5 — file path is per-iris-url; save creates dir + file mode 0600; load returns None when missing; load returns None when expired; load returns token when fresh | mcp |
| `mcp/tests/test_tools_authenticate.py` | 7 — pairing-code happy path; pairing-code 410 maps to clean error; pat-paste happy path; pat-paste 401 maps to clean error; invalid prefix rejected; case-insensitive on IRIS- codes; in-process client.token updated | mcp |
| `frontend/tests/unit/mcpPairing.test.ts` | 4 — initial state; generate-button click + render; copy button; expiry countdown | frontend |

**Total**: 32 new tests for v5.15.0.

## End-to-end verification

Listed in the plan file (`/home/vscode/.claude/plans/jaunty-wishing-liskov.md`) — 11 steps covering: Supabase migration apply, web pairing-page round-trip, MCP write-tool 401 prompt, pairing exchange, token persistence, single-use enforcement, token persistence across MCP restart, revocation, and PAT-paste fallback.

## Out of scope (deferred)

- Polling-based RFC 8628 device flow.
- OS keychain integration for token storage.
- Granular MCP-scoped PATs.
- Pairing-code deep-link or QR rendering.
- Configurable PAT expiry from the pairing page UI.
