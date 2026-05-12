# ADR-160: MCP pairing-code authentication

Status: Accepted (2026-05-12)
Extends: [ADR-127](ADR-127-Personal-Access-Tokens.md), [ADR-131](ADR-131-MCP-Server-Architecture.md)

## Context

`save_doview_analysis` and any future write-capable Iris MCP tool require the iris-mcp server to hold a bearer credential — historically a Personal Access Token (PAT) supplied via `IRIS_TOKEN` in the user's Claude Desktop MCP config JSON. Setting that up today involves:

1. Open `~/.config/claude_desktop_config.json` (or platform equivalent) in an editor.
2. Log into Iris in a browser.
3. Navigate to `/settings/tokens` (or use the API directly because no UI route existed pre-v5.15 for non-admins).
4. Create a PAT, copy its ~84-character secret.
5. Paste it into the env block of the MCP config.
6. Restart Claude Desktop.

In real use this is a complete UX cliff. When a user inside Claude asks "save this DoView analysis to Iris", the `save_doview_analysis` tool fails 401, and there's no in-conversation recovery — the user has to leave the conversation, edit a JSON file by hand, restart their client, and come back. Most users won't make it through that funnel.

The intended outcome: authenticate the MCP connection with **two clicks and one paste**, entirely from inside Claude, without editing config files or restarting the client.

## Decision

Introduce a **pairing-code flow** modelled on the OAuth 2.0 device authorisation grant (RFC 8628) but stripped down to a single shot:

1. The authenticated web UI (`/settings/mcp-pairing`) lets any logged-in user press **Generate pairing code** and receive a short typeable code (`IRIS-XXXX-YYYY`, ~40 bits of entropy, 10-minute TTL, single-use).
2. The user pastes the code into Claude chat.
3. Claude calls a new MCP tool `iris_authenticate(credential)` which POSTs to `/api/auth/pairing-codes/{code}/exchange`. The exchange endpoint is anonymous, rate-limited, and one-shot.
4. The exchange returns a freshly minted PAT (default 90-day expiry, owned by the user, named `MCP — <timestamp>`).
5. The MCP server persists the PAT at `~/.iris-mcp/<sha256(iris_url)[:16]>.json` with mode 0600. Subsequent MCP tool calls use the stored PAT automatically — no client restart needed.

The same `iris_authenticate` tool also accepts a full PAT (`iris_pat_...`) pasted directly, as a power-user fallback. The MCP server dispatches by string prefix: `IRIS-` → pairing exchange; `iris_pat_` → validate against `/api/auth/me` and persist directly.

## Why a simplified one-shot exchange, not full RFC 8628 device flow

- **No polling required.** RFC 8628 has the device polling the authorisation server until the user approves; the client must run a background loop. The iris-mcp stdio process is short-lived (one per Claude Desktop launch) and we already have a synchronous `iris_authenticate` invocation channel — the user paste IS the trigger. A polling loop would only add complexity without UX benefit.
- **Trust model is simpler.** RFC 8628 separates the device code (private) from the user code (typed by the user). For us, the user code IS the exchange credential — there's no public/private code split because the threat model is shorter (the user is acting alone, not delegating to a kiosk). The 10-minute TTL plus rate limiting bounds the brute-force window.
- **Existing PAT machinery is reused.** The exchange endpoint calls the existing `backend/app/tokens/service.py:create_token` function. The issued PAT is a normal `personal_access_tokens` row — listable, revocable, and audit-trackable via the existing `/settings/tokens` UI.

## Why file-based token storage at `~/.iris-mcp/<hash>.json`, not OS keychain

- **Cross-platform parity.** macOS Keychain, Windows Credential Manager, and Linux Secret Service each require platform-specific code and platform-specific failure modes. A file at `~/.iris-mcp/` works identically on every OS Claude Desktop supports.
- **Mode 0600 is adequate for the threat model.** The token is per-user and only ever readable by the same user account; anyone with read access to the user's home directory already has equivalent or greater access to MCP itself, its environment, and Claude Desktop's own session storage.
- **Hashed-URL key supports multiple Iris instances.** A single iris-mcp install can authenticate against multiple Iris deployments (local dev, UAT, production) by namespacing under `sha256(iris_url)[:16]`. No collision risk.
- **Keychain is a future enhancement.** Out-of-scope for v1; revisit if the threat model changes.

## Why a separate page at `/settings/mcp-pairing`, not on `/settings/tokens`

- **Single-purpose UX.** The pairing page is a one-button flow: press, see code, copy. The tokens page is multi-purpose (list, name, set expiry, revoke). Mixing them confuses both.
- **The tokens page stays the place to manage existing PATs.** The pairing page links there. The pairing flow under the hood issues a PAT into the same store, so revocation and audit are unified.
- **User-self, not admin-only.** Any logged-in user can pair their own MCP; the issued PAT is scoped to that user. Future non-admin users get the same path.

## Why include the PAT-paste fallback (`iris_authenticate('iris_pat_…')`)

- **Tiny cost — single string-prefix branch.** No new endpoint; the PAT is validated by an existing `/api/auth/me` call.
- **Covers the "I already have a PAT" case.** Power users who created a PAT via `/settings/tokens` (or the API) shouldn't have to detour through a pairing code just to land it in the MCP token file.
- **Same persistence path.** Both routes write `~/.iris-mcp/<hash>.json`. The MCP client doesn't care which credential type produced the file.

## Consequences

- One new table: `pairing_codes` (SQLite migration m052 + Supabase migration m056).
- Two new endpoints under `/api/auth/pairing-codes` (auth-required create; anonymous exchange).
- New iris-client methods: `create_pairing_code()` and `exchange_pairing_code(code)`.
- New MCP tool: `iris_authenticate(credential)` accepting either a pairing code or a pasted PAT.
- New MCP token-storage helper at `mcp/src/iris_mcp/token_store.py` (file-based, 0600).
- iris-mcp `__main__.py` resolves the bearer token in precedence order: `IRIS_TOKEN` env > stored token > anonymous.
- New user-self frontend page `/settings/mcp-pairing` with sidebar nav entry.
- Write-tool 401 errors return structured guidance pointing the user to the pairing page.
- The token file is created with mode 0600 and never readable by other OS users. The pairing-code value is logged at server-side info level but never printed by the MCP server (the secret is the PAT, not the code).
- ~32 new tests across backend, iris-client, mcp, frontend.

## Out of scope (deferred)

- **Full OAuth 2.0 device authorisation grant (RFC 8628)** with polling — unnecessary for this UX.
- **OS keychain integration** — file at 0600 is adequate v1.
- **Per-tool scope on the issued PAT** — inherits the user's full role; granular MCP scopes are a future enhancement, gated on real demand.
- **`iris-mcp://authenticate?code=…` deep-link** — typeable code is fine; OS handler registration is a future enhancement.
- **QR-code rendering of the pairing code** — typeable form is sufficient for paste-not-retype.
- **Configurable PAT expiry from the pairing page** — fixed at 90 days in v1.

## See also

- [ADR-127](ADR-127-Personal-Access-Tokens.md) — the PAT machinery this ADR reuses for the exchanged credential.
- [ADR-131](ADR-131-MCP-Server-Architecture.md) — iris-mcp stdio architecture that gains the new auth path.
- [SPEC-160-A](specs/SPEC-160-A-MCP-Pairing-Code-Authentication.md) — schema, endpoint contracts, MCP tool wiring, frontend page, test plan.
