# ADR-250: Batch Endpoints Enforce Collection Write-Scope Per Item

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-250 |
| **Initiative** | Close the write-scope bypass on `/api/batch/*` |
| **Proposed By** | Engineering |
| **Date** | 2026-09-24 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** per-user collection write-scope (ADR-237, made
consistent in ADR-238), which every single-item write endpoint enforces with
`assert_write_allowed` against the owning collection, and the batch
endpoints (`/api/batch/{elements,diagrams}/{delete,clone,set,tags}`, ADR-060;
`/api/batch/elements/{create,update}`, ADR-200), which MCP agents and the CLI
use for bulk work,

**facing** the finding recorded in ADR-249: none of those ten batch endpoints
checked write-scope. Only the ADR-249 relationship batch did. A user scoped
to collection A could delete, clone, retag, create, update or move elements
and diagrams in any other collection through them, exactly the writes the
single-item endpoints refuse with 403. Reproduced with a scoped architect: all
ten endpoints wrote into an out-of-scope collection,

**we decided to** pass the acting `user` into every batch service function
and gate each item before it is written, with the same rule as the matching
single-item endpoint:

| Operation | Collection(s) that must be writable |
|-----------|-------------------------------------|
| delete, tags, update | the item's own collection |
| clone | the item's own collection (the copy lands beside it) |
| set (move to another set) | the item's current collection **and** the destination set's collection |
| element create | the collection of the *effective* set (`resolve_effective_set`, as `POST /api/elements` does, ADR-238) |

A refusal becomes a per-item error carrying the same text as the 403 detail
(`Outside your collection write-scope`), so batches keep their per-item
failure isolation: out-of-scope items are left untouched and in-scope items in
the same call still succeed. One helper, `_require_writable`, does the
conversion for all eleven batch operations, including the ADR-249
relationship batch, which previously inlined it (DRY, §13),

**and neglected** (1) rejecting the whole batch with 403 when any item is out
of scope. Rejected because it breaks the per-item contract that MCP and CLI
callers rely on (ADR-200, ADR-249), and it would make a mixed batch
all-or-nothing for scoped users only; (2) checking scope once per batch in the
router, for example requiring all ids to share a collection. Rejected because
batches legitimately span collections for unscoped users and admins, and
per-item gating already gives the right answer for everyone; (3) gating only
the destination of a move. Rejected because moving an item out of a
collection removes content from it, which is a write to that collection
(ADR-237's set-move rule for `PUT /api/sets/{id}` checks both sides too),

**to achieve** write-scope that holds on every write path, so a scoped user's
confinement cannot be sidestepped through bulk endpoints,

**accepting that** each batch item now costs one or two extra
collection-lookup queries (primary-key lookups; negligible next to the writes
themselves), and that the batch service functions' signatures change from
`*_by: str` to `user: dict`. The router is their only caller.

---

## Consequences

- No schema, endpoint, MCP tool or CLI change; the request and response
  shapes are unchanged. Surface parity (§14) and migration parity (§15) are
  N/A.
- Unscoped users and admins see no behaviour change.
- Scoped users now get per-item `Outside your collection write-scope`
  errors from batch calls that previously succeeded outside their scope.

## Dependencies

- ADR-060 (Sets & batch operations), ADR-200 (batch element create/update).
- ADR-237 (per-user collection write-scope), ADR-238 (scope consistency and
  effective-set gating).
- ADR-249 (relationship batch, where the gap was recorded).

## References

- Implementation spec: [SPEC-250-A](./specs/SPEC-250-A-Batch-Endpoints-Enforce-Write-Scope.md)
