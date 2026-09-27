# ADR-255: AI Providers Can Be Deleted After They Have Been Used

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-255 |
| **Initiative** | Let admins remove AI providers they no longer want |
| **Proposed By** | Engineering (bug report from the product owner, 2026-09-27) |
| **Date** | 2026-09-27 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** `DELETE /api/ai/providers/{id}`, which runs a plain
`DELETE FROM ai_providers`, while `ai_conversations.provider_id` and
`ai_usage_log.provider_id` both reference `ai_providers(id)` with no
`ON DELETE` action,

**facing** a Postgres `ForeignKeyViolationError`
(`ai_conversations_provider_id_fkey`) for any provider that had ever answered a
question. The endpoint returned an unhandled 500. Because the error skips the
CORS middleware, the browser reported it as a CORS failure, and Admin →
Settings → AI showed "Delete failed" for every non-default provider on UAT,

**we decided to** have `service.delete_provider` set `provider_id = NULL` on the
referencing rows in `ai_conversations` and `ai_usage_log`, then delete the
provider, all in one commit. Each row keeps its own model name (`model_used` /
`model`), so history still says which model answered,

**and neglected** (a) a migration that adds `ON DELETE SET NULL` to both
foreign keys. Rejected: SQLite can't alter a foreign key without rebuilding the
table, and the SQLite and Supabase migrations would both need a table rebuild
(protocol §15) for the same effect as two `UPDATE` statements; (b)
`ON DELETE CASCADE` or deleting the rows. Rejected: deleting a provider should
not erase users' conversation history or the usage audit trail; (c) soft-delete
through the existing `is_active` flag. Rejected: admins asked to delete, and
inactive providers would still clutter the list,

**to achieve** a delete that works for any non-default provider,

**accepting that** old conversations and usage rows no longer link to a
provider record, only to a model name.

---

## Consequences

- Backend service change only. The endpoint, MCP and CLI surfaces are unchanged,
  so surface parity is unaffected.
- No schema change and no migration.

## Dependencies

- ADR-093 (AI providers and usage logging).

## References

- Implementation spec: [SPEC-255-A](./specs/SPEC-255-A-Delete-Used-AI-Provider.md)
