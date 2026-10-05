# ADR-259: Updating a Set Keeps the Fields the Caller Left Out

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-259 |
| **Initiative** | A metadata edit must not drop a set out of its collection (issue #314) |
| **Proposed By** | Product owner (2026-10-05) |
| **Date** | 2026-10-05 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** `PUT /api/sets/{id}`, which replaced the whole row, and
the MCP `update_set` tool and CLI `iris update set` command (ADR-178), which
build that PUT body by reading the set and merging the caller's changes over
it,

**facing** a set that lost its collection after a plain name or description
edit. `update_set` kept `collection_id` out of the merge so that moves would
go through `move_set`. The PUT body then had no `collection_id`, and the
backend stored a missing field as `NULL`. The set dropped out of its
collection, the collection's set and view counts fell, and a later
`update_collection` failed with "Thumbnail diagram does not belong to a set in
this collection". The existing MCP test asserted that `collection_id` was
absent from the body, against a mocked response, so it passed,

**we decided to** fix both sides:

1. **MCP and CLI.** `update_set` and `iris update set` still refuse to move a
   set, but they now send the set's current `collection_id` back in the PUT
   body. A `collection_id` supplied by the caller is dropped.
2. **Backend.** For `description`, `thumbnail_source`, `thumbnail_diagram_id`,
   `collection_id`, `system_prompt` and `mcp_system_context`, a key that is
   missing from the PUT body means "leave unchanged". An explicit `null` still
   clears the value. The router tells the two apart with Pydantic's
   `model_fields_set`. `name` stays required,

**and neglected** (a) fixing only the MCP handler. Rejected: any other client
that sends a partial body (a script, a future surface) would still un-group
the set, and the CLI had the same bug; (b) a separate `PATCH /api/sets/{id}`
endpoint. Rejected: it adds a write endpoint that needs its own MCP tool and
CLI command under protocol §14, for behaviour the PUT can give safely; (c)
treating `null` as "leave unchanged" for these fields, as the tab-default
fields already do. Rejected: `move_set` un-groups a set by sending
`collection_id: null`, and the set page clears a prompt the same way,

**to achieve** set edits that change only what the caller asked to change, on
every surface,

**accepting that** a client that relied on leaving a field out to clear it
must now send `null`. The web UI always sends every field, so it is
unaffected.

---

## Consequences

- No schema change, so there is no migration and protocol §15 is not engaged.
  The service reads the current row positionally.
- No new endpoint, tool or command, so surface parity (protocol §14) is
  unchanged.
- The CLI's set field list now includes `hierarchy_sort`,
  `package_tab_default` and `view_tab_default`. `iris update set` accepted
  those options before but never sent them.
- `PUT /api/collections/{id}` still replaces the whole row. The MCP and CLI
  collection updates merge every field, so they are not exposed to this bug.

## Dependencies

- ADR-178 (update and move tools), ADR-182 (surface parity), ADR-202 /
  ADR-204 / ADR-208 (set fields where `null` already means "leave unchanged").

## References

- Implementation spec: [SPEC-259-A](./specs/SPEC-259-A-Set-Update-Keeps-Omitted-Fields.md)
- Issue #314
