# ADR-249: Relationship Create / Update / List / Delete for MCP and CLI Agents

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-249 |
| **Initiative** | Let agents connect the elements they create (issue #298) |
| **Proposed By** | Engineering |
| **Date** | 2026-09-23 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** the Iris MCP server and CLI, which since ADR-178 /
ADR-200 can create and update collections, sets, packages, diagrams and
elements (including in batches) but expose no relationship tools, while the
backend already has single-item relationship REST routes
(`/api/relationships`, SPEC-003-A) used by the canvas, and UML role names are
stored on a relationship as `data.sourceRole` / `data.targetRole` by the Sparx
importer (`import_sparx/service.py`) and on canvas edges by the same keys,

**facing** agents that can add elements but not connect them — new elements
show no relationships, diagram edges can't carry a real `relationshipId`, and
a wrong role or attribute from an import can't be corrected (issue #298: a
family-tree extension left ten partner/child links stranded in element
`data`); plus two gaps the issue asks to close on the way: relationship type
can't be changed after creation, and relationships can't be listed by set or
type,

**we decided to**
(1) add `POST /api/batch/relationships/create` (1–100 items, per-item failure
isolation, `BatchResultWithIds` envelope — the ADR-200 pattern) whose items
take `source_role` / `target_role` and store them as `data.sourceRole` /
`data.targetRole` through one helper, `apply_role_fields`;
(2) validate each batch item with a new `validate_new_relationship` —
both endpoints exist and aren't deleted, source ≠ target, both in the same
set — and apply collection write-scope per item (ADR-237/238, via the source
element), reporting failures as per-item errors;
(3) make `relationship_type` updatable on `PUT /api/relationships/{id}`
(optional; omitted keeps the type) and accept `source_role` / `target_role`
there too (merged into `data`; `""` clears);
(4) add `set_id` (either end in the set) and `relationship_type` filters to
`GET /api/relationships`, and return derived `source_role` / `target_role` on
every relationship response (from `data`, which stays the source of truth);
(5) add shared `IrisClient` methods — `create_relationships`,
`list_relationships`, `get_relationship`, `update_relationship` (reads the
current version for `If-Match`, partial merge), `delete_relationship` — and
build the MCP tools (`create_relationships`, `update_relationship`,
`list_relationships`, `get_relationship`, `delete_relationship`) and CLI
commands (`iris create relationship|relationships`, `iris update
relationship`, `iris delete relationship`, `iris relationships list|get`) on
them only (protocol §13);
(6) add `relationship` to the §14 parity checker's known entities, attribute
`/api/batch/<entities>/<verb>` routes to their entity, and count plural batch
tool / command names (`create_relationships`) for the singular entity;
(7) make the diagram-edge auto-create honour `data.relationshipId`: an edge
whose `relationshipId` names a live relationship between the same two
elements, in either direction, is taken to represent it and no relationship
is auto-created for it (previously only a same-direction source/target match
suppressed the create, so an edge drawn target → source added a reversed
duplicate),

**and neglected**
(a) rejecting self-referencing and cross-set relationships inside
`create_relationship` (the service every path shares) — rejected: the canvas
supports self-loop edges (`UnifiedCanvas` `self_loop`, persisted through
`POST /api/relationships`), the Sparx importer imports reflexive
associations ("self-references", README), and diagram-edge auto-create calls
the same function; UML permits reflexive associations, so a service-level ban
would break legitimate existing flows. The check therefore lives on the new
agent path only, and the single `POST /api/relationships` keeps its contract;
(b) also rejecting on the single `POST /api/relationships` — rejected for the
same reason (it is the canvas's endpoint); agents never use it, because MCP
and CLI create through the batch endpoint;
(c) validating `relationship_type` against the notation's registered types —
not possible today: the backend has no relationship-type registry (the
`notations` table from m020 has no types; the type lists live in the
frontend and in the `views` toolbar config, and imports write types such as
`composition` or ArchiMate types freely). The type stays a free, non-empty
string on every path; a registry would be its own ADR;
(d) snapshotting `relationship_type` in `relationship_versions` — rejected
for now: it needs a schema migration on both SQLite and Supabase for a field
nothing reads historically. Instead, a type change records
`relationship_type: old -> new` as the new version's `change_summary` when
the caller gives none;
(e) a separate singular MCP `create_relationship` tool — rejected: the batch
tool covers one item, and one entry point keeps validation identical for MCP
and CLI (`iris create relationship` also sends a one-item batch);
(f) doing the role-name mapping in `iris-client` — rejected: putting it in
the backend means any REST client gets the same storage convention;
(g) opening `GET /api/relationships` and `GET /api/relationships/{id}` to
anonymous callers (`get_optional_user`, like element reads per ADR-123) so
`list_relationships` / `get_relationship` work without sign-in — rejected
here: it changes the access contract of pre-existing routes, which is a
security decision outside issue #298. The asymmetry is instead stated in the
two tools' descriptions and in the server instructions' AUTH RECOVERY text
(seed and fallback), which previously promised every `get_*` / `list_*`
works anonymously,

**to achieve** relationships created by agents that are indistinguishable
from UI- and import-created ones (same table, same `data` keys, same counts,
same Relationships tab, same queries), ids that can be dropped into a
diagram edge's `data.relationshipId` without the edge auto-create adding a
duplicate (it skips an edge whose `relationshipId` links the same two
elements in either direction, and otherwise dedups by source/target pair),
clear per-item errors for
self-referencing and cross-set requests, and §14 parity enforced for
relationships in CI,

**accepting that** the rules differ by path — the canvas, importers and
edge auto-create may still create reflexive (and, through the canvas,
cross-set) relationships while the agent path can't; that `set_id` listing
matches either end, so a pre-existing cross-set relationship appears under
both sets; that `update_relationship` costs one extra GET to read the
version; that a type change's history lives in `change_summary` rather
than in a versioned column; and that relationship reads need sign-in while
element reads don't, so an anonymous agent gets `auth_required` from
`list_relationships` / `get_relationship`.

---

## Consequences

- New REST route `POST /api/batch/relationships/create`; additive fields on
  `PUT /api/relationships/{id}` and on relationship responses; additive query
  params on `GET /api/relationships`. No schema change, so migration parity
  (§15) is untouched; service SQL reads rows positionally and uses no
  SQLite-only syntax.
- The batch path checks collection write-scope per item. (The pre-existing
  batch element endpoints still don't; noted, not changed here.)
- The canvas renders role names from the edge's own `data.sourceRole` /
  `data.targetRole` (`BaseEdge.svelte`), not from the relationship, so an
  agent drawing an edge copies the roles onto it — exactly what the Sparx
  importer does. The `create_relationships` tool description says so.
- `update_relationship` treats `data` as a replacement except for the role
  keys, which carry over unless a role is passed — so fixing an attribute
  can't silently drop a role.
- MCP server instructions (seed body re-applied on startup, ADR-177, and the
  iris-mcp fallback) point agents at `list_relationships` →
  `create_relationships` → `data.relationshipId` in `update_diagram`, and
  their AUTH RECOVERY text now says `list_relationships` /
  `get_relationship` need sign-in.
- Diagram saves (`diagrams.service.update_diagram`) do one extra indexed
  lookup per edge that carries a `relationshipId`. A `relationshipId`
  naming a relationship between other elements (a stale or copied edge) is
  ignored and the edge is treated as before.
- Package versions: backend, frontend, iris-client and iris-mcp → 6.50.0.

### Follow-up (out of scope)

- The issue's "nice to have": an `update_diagram` variant or helper that adds
  nodes/edges for existing elements and relationships without resending the
  full canvas (the family-tree canvas is 274 nodes). Needs its own ADR —
  merge semantics, layout of new nodes, and optimistic concurrency.
- A backend relationship-type registry per notation, if type validation is
  wanted (see (c)).

## Dependencies

- SPEC-003-A (relationship CRUD), ADR-178 (MCP update/move tools),
  ADR-182 (surface parity, protocol §14), ADR-200 (batch element tools),
  ADR-237 / ADR-238 (collection write-scope).

## References

- Issue: [#298](https://github.com/cgbarlow/iris/issues/298)
- Implementation spec: [SPEC-249-A](./specs/SPEC-249-A-Relationship-Tools-For-Agents.md)
