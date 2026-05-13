# SPEC-173-A: Parameterise booleans for SQLite/Postgres portability in OAuth service

ADR: [ADR-173](../ADR-173-OAuth-Boolean-Column-Parameterisation.md)

## Summary

`oauth_refresh_tokens.revoked` is `BOOLEAN` on Postgres (Supabase), `INTEGER` on SQLite. Three SQL statements in `backend/app/oauth/service.py` used bare-int literals (`0`/`1`). SQLite accepts both; Postgres rejects with `DatatypeMismatchError`. Replace with parameterised Python `bool` so the DB adapter coerces correctly on either backend. Add a source-scan regression test so the antipattern can't drift back.

## Backend changes

### `backend/app/oauth/service.py`

Three call sites:

| Function | Before | After |
|---|---|---|
| `create_refresh_token` (INSERT) | `VALUES (?, ?, ?, ?, ?, ?, 0)` with 6 params | `VALUES (?, ?, ?, ?, ?, ?, ?)` with 7 params, last is `False` |
| `rotate_refresh_token` (theft kill) | `"UPDATE oauth_refresh_tokens SET revoked = 1 WHERE family_id = ?", (family_id,)` | `"UPDATE oauth_refresh_tokens SET revoked = ? WHERE family_id = ?", (True, family_id)` |
| `revoke_refresh_token` | `"UPDATE oauth_refresh_tokens SET revoked = 1 WHERE id = ? AND client_id = ?", (token, client_id)` | `"UPDATE oauth_refresh_tokens SET revoked = ? WHERE id = ? AND client_id = ?", (True, token, client_id)` |

Add a short v6.0.13 comment at each site referencing ADR-173 so future readers know why the boolean is parameterised rather than literal.

## Tests

### `backend/tests/test_oauth/test_postgres_bool_int_compatibility.py` (new)

4 source-scan cases. Faster than spinning up a Postgres test container, catches the specific antipattern that bit us:

1. `test_no_set_revoked_equals_bare_int` — `"revoked = 0"` and `"revoked = 1"` substrings absent from `app.oauth.service` source.
2. `test_no_bare_int_trailing_in_oauth_refresh_insert` — regex `INSERT INTO oauth_refresh_tokens (...) VALUES (..., [01])` not found.
3. `test_create_refresh_token_passes_bool_not_int` — the `create_refresh_token` function body contains `, False`.
4. `test_rotate_and_revoke_pass_true_not_int` — `rotate_refresh_token` and `revoke_refresh_token` bodies contain `True`.

If the test setup ever moves to a real Postgres fixture, the source-scan guards become redundant — but they're cheap insurance to keep on SQLite-only CI.

## Versioning

`mcp/pyproject.toml`: 6.0.12 → 6.0.13. `frontend/package.json` matched.

## Acceptance criteria

- [ ] Render API logs no longer show `asyncpg.exceptions.DatatypeMismatchError` from `oauth/service.py:260` during token exchange.
- [ ] claude.ai → Sign in → Allow → connector goes to "Connected" (no `mcp_token_exchange_failed`).
- [ ] 44/44 backend OAuth tests pass (40 existing + 4 new source-scan).
