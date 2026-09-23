# ADR-247: Resolve a PAT's Owner Through the Deployment's User Store

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-247 |
| **Initiative** | Make Personal Access Tokens work on Supabase deployments |
| **Proposed By** | Engineering |
| **Date** | 2026-09-23 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** Personal Access Tokens (ADR-127, SPEC-127-A), which
`verify_pat` (`app/tokens/service.py`) validates by looking the token up by
prefix and joining its owner in the same query
(`JOIN users u ON u.id = pat.user_id`), and Supabase deployments (ADR-094),
where `personal_access_tokens.user_id` is a `UUID` referencing `profiles`
(m042) while `users.id` is `TEXT` — `users` there is only a mirror of
`profiles`, synced at startup so `created_by` foreign keys are satisfied,

**facing** every PAT bearer request on UAT (and any Supabase deployment)
returning `500 Internal Server Error`, logged as
`asyncpg.exceptions.UndefinedFunctionError: operator does not exist: text = uuid`
at the `verify_pat` join — so PATs have never authenticated on Supabase,
while the SQLite suite passed because SQLite compares the two columns
without complaint; and, beneath the type error, the join targeting the
wrong table: the startup mirror misses users who signed up since the last
deploy and keeps a role that `profiles` has since changed,

**we decided to** look the PAT up on its own (`SELECT … FROM
personal_access_tokens WHERE prefix = ?`, no join) and resolve its owner
through a new shared helper, `app.auth.users.get_user(db, user_id,
db_backend)`, which reads `profiles` (via the existing
`supabase_service.get_profile`) in Supabase mode and `users` in SQLite mode.
`verify_pat` gains a `db_backend` parameter (default `"sqlite"`), which
`_get_current_user_pat` passes from `config.db_backend`. The SQLite JWT
path (`_get_current_user_sqlite`) now uses the same helper instead of its
own inline copy of the `users` query (DRY, protocol §13),

**and neglected** (1) casting the join (`u.id = pat.user_id::text` /
`CAST(pat.user_id AS TEXT)`) — rejected: it removes the 500 but still
authorises against the startup mirror, so a new sign-up's PAT is rejected
until the next deploy and a demoted user keeps their old role on the PAT
path while the JWT path (which reads `profiles`) sees the new one;
(2) a migration changing `personal_access_tokens.user_id` to `TEXT`
referencing `users` — rejected: schema churn on a live table, it breaks the
table's RLS policies (`user_id = auth.uid()`), and it would still point at
the mirror; (3) re-syncing `users` from `profiles` on every request —
rejected: a write on every authenticated read, to prop up a table that
isn't the authority,

**to achieve** PATs that authenticate on Supabase deployments with the same
user, role and active-status semantics as a Supabase JWT, with no schema,
endpoint, MCP tool or CLI change,

**accepting that** the PAT path now makes two queries (PAT row, then owner)
instead of one join — both are primary-key/indexed lookups, and the
Argon2id verification that follows dominates the cost.

---

## Consequences

- No schema, endpoint, MCP tool, or CLI change; surface parity (§14) is N/A.
  Migration parity (§15) is untouched — the fix works on the existing m041
  (SQLite) and m042 (Supabase) tables.
- Backend-specific behaviour is now tested against a real PostgreSQL
  schema: `tests/test_tokens/test_verify_pat_postgres.py` applies the
  Supabase migrations (m001, m027, m042) to a throwaway database and runs
  when `IRIS_TEST_POSTGRES_DSN` is set; it skips otherwise, so the default
  SQLite suite is unchanged.
- The PAT the UAT owner created on 2026-09-23 while trying to import data
  starts working once this is deployed (it was never revoked).

## Dependencies

- ADR-094 (Supabase deployment mode / `DatabasePort` adapter).
- ADR-127 (Personal Access Tokens — the validator this ADR corrects).
- ADR-174 (Supabase-mode JWT validation — the `profiles` lookup the PAT
  path now matches).

## References

- Implementation spec: [SPEC-247-A](./specs/SPEC-247-A-PAT-Owner-Lookup-Via-Deployment-User-Store.md)
