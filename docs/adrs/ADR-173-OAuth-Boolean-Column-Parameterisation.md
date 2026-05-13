# ADR-173: Parameterise booleans for SQLite/Postgres portability in OAuth service

Status: Accepted (2026-05-13)
Extends: [ADR-164](ADR-164-OAuth-2.1-for-MCP.md)

## Context

OAuth on the iris-mcp HTTP transport finally reached end-to-end token exchange in v6.0.12 (after the ADR-170/171/172 chain). The user signed in to Iris, tapped Allow on the consent screen, was redirected back to claude.ai with an authorization code — and the connector then displayed:

> Authorization with the MCP server failed. ... `mcp_token_exchange_failed` ... `ofid_922f130efbf385c7`

Live iris-api logs at the time of the failure:

```
File ".../backend/app/oauth/router.py", line 343, in token_endpoint
  refresh_token, _ = await oauth_service.create_refresh_token(...)
File ".../backend/app/oauth/service.py", line 260, in create_refresh_token
asyncpg.exceptions.DatatypeMismatchError:
  column "revoked" is of type boolean but expression is of type integer
```

The OAuth schema defines `oauth_refresh_tokens.revoked BOOLEAN NOT NULL DEFAULT FALSE` (per the Supabase migration `m058_oauth_tables.sql`). SQLite treats booleans as integers (0/1) and accepts both `0`/`1` and `False`/`True` interchangeably. Postgres has a strict BOOLEAN type — bare `0`/`1` SQL literals are rejected.

Three call sites in `backend/app/oauth/service.py` used bare-int literals:

| Location | Statement |
|---|---|
| `create_refresh_token` (line 264) | `VALUES (..., 0)` — INSERT |
| `rotate_refresh_token` (line 310) | `SET revoked = 1` — theft kill |
| `revoke_refresh_token` (line 348) | `SET revoked = 1` — explicit revoke |

All three crash on Postgres. All three pass on SQLite. The existing 40 OAuth tests cover the full token-exchange + rotation + revoke paths, but they all run on SQLite, so the bug went undetected from v6.0.0 (when OAuth shipped) until live production testing now.

## Decision

Replace bare-int literals with parameterised Python `bool` values throughout the OAuth service:

```python
# Before (line 264):
"VALUES (?, ?, ?, ?, ?, ?, 0)"
(token_value, client_id, user_id, family, expires_at, now_iso),

# After:
"VALUES (?, ?, ?, ?, ?, ?, ?)"
(token_value, client_id, user_id, family, expires_at, now_iso, False),
```

```python
# Before (lines 310, 348):
"UPDATE oauth_refresh_tokens SET revoked = 1 WHERE ..."

# After:
"UPDATE oauth_refresh_tokens SET revoked = ? WHERE ..."
(True, ...)
```

The DB adapter coerces Python `bool` to the right SQL type on either backend (`INTEGER 0/1` on SQLite, `BOOLEAN false/true` on Postgres).

## Add a static guard so this can't drift back

The existing OAuth tests pass on SQLite by design; reading them won't catch a future bare-int regression. Add a focused regression test that **scans the OAuth service source** for the antipattern:

- No `revoked = 0` or `revoked = 1` substrings (catches UPDATE statements).
- No `INSERT INTO oauth_refresh_tokens ... VALUES (..., 0)` (regex match on the INSERT shape).
- Positive assertions inside `create_refresh_token`, `rotate_refresh_token`, `revoke_refresh_token` that the param tuples include the Python `False` / `True` constants.

This is a source-level check, fast, and runs on every test invocation regardless of DB backend.

## Why source-scanning (not a real Postgres test)

- Running the OAuth integration tests against a real Postgres in CI is a much bigger infrastructure lift (test containers, fixture management, parallel test isolation).
- Source-scanning catches the specific antipattern that bit us; future strict-typing bugs of other kinds would need their own targeted guards.
- The fix is one line per call site. The cost of the test is one file.

If we eventually move test fixtures to Postgres for the OAuth path, the source-scan guard becomes redundant — but keeping it is cheap insurance.

## Consequences

- 3 lines changed in `app/oauth/service.py` (one INSERT + two UPDATE statements).
- 4 new tests in `tests/test_oauth/test_postgres_bool_int_compatibility.py`.
- 40 existing OAuth tests stay green.
- 44/44 total OAuth tests pass.
- Version bump v6.0.12 → v6.0.13. Patch-level (correctness fix, no schema or API surface change).

## Verification

- After deploy, claude.ai mobile → Sign in on Iris connector → consent page → Allow → connector status goes to "Connected" (no more `mcp_token_exchange_failed`). Write tools succeed.
- Render API logs no longer show the `DatatypeMismatchError` traceback at `oauth/service.py:260`.

## See also

- [ADR-164](ADR-164-OAuth-2.1-for-MCP.md) — original OAuth 2.1 design (introduced the affected refresh_tokens table).
- Issue [#119](https://github.com/cgbarlow/iris/issues/119) — ten-revision fix history.
