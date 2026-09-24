# ADR-252: Patch-Style Diagram Updates (`patch_diagram`)

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-252 |
| **Initiative** | Let agents make small edits to large diagrams (issue #301) |
| **Proposed By** | Engineering |
| **Date** | 2026-09-24 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** diagram writes from the MCP server and CLI, where the
only way to change a canvas is `update_diagram` / `iris update diagram` →
`PUT /api/diagrams/{id}` (SPEC-003-A), which replaces the whole
`{nodes, edges}` payload under an `If-Match` version check, and whose
persistence path (`diagrams.service.update_diagram`) also normalises flat AI
shapes (ADR-218), detects notations, re-indexes search, regenerates
thumbnails, pulls canvas elements into the diagram's set and auto-creates
relationships for element-to-element edges (with the ADR-249
`relationshipId` either-direction skip); and where the relationship tools
(ADR-249) let agents create relationships but not draw them on existing
large diagrams,

**facing** agents that must resend the entire canvas for any edit — about
170 KB and 547 items to add 13 nodes and 10 edges to the 274-node "Full
Family Tree" — so a node or edge dropped or mangled in transit is silently
deleted; agent and UI edits that silently overwrite each other when the MCP
tool's GET-merge-PUT reads a version just before someone else saves; node
labels copied from elements at draw time that never follow a rename
("Peter Barlow (single-parent family)" after the element became "Peter
Barlow ⚭ Elizabeth Short"), with a full replacement as the only fix; and a
check-then-write race in `update_diagram` itself (it read
`current_version`, then updated the row unconditionally, so two concurrent
saves could both claim the same next version),

**we decided to**
(1) add `PATCH /api/diagrams/{id}` taking `{operations: [1..200],
change_summary?}` — ordered operations `add_node`, `update_node`,
`remove_node` (`cascade_edges`, default true), `add_edge`, `update_edge`,
`remove_edge` and `sync_labels` (`node_ids?`) — and returning
`{id, current_version, updated_at, applied, results[]}` with one result per
operation (its index, op and affected id);
(2) keep all operation logic in a pure, I/O-free module
(`app/diagrams/canvas_patch.py`) that works on a deep copy of the stored
canvas and raises `CanvasPatchError` naming the failing operation's index;
the service batch-fetches what validation needs (element name + set for
referenced `entityId`s, relationship endpoints for referenced
`relationshipId`s — one chunked `IN` query each, no per-node queries) and
passes it in;
(3) persist the patched canvas by calling the existing `update_diagram` with
the current name, description and metadata — no second write path — so a
patch stores exactly what a full update with the same canvas would, with
every side effect identical, and produces exactly one new version;
(4) guarantee atomicity by ordering: every operation is validated and
applied in memory before `update_diagram` is called, so any failing
operation (422, `detail.op_index`) writes nothing;
(5) follow the REST optimistic-concurrency convention: `If-Match` carries
the expected version (optional here — omitted, the patch applies to the
current version); on a mismatch return 409 with
`detail.current_version` and write nothing; the MCP tool and CLI expose it
as `expected_version` / `--expected-version`;
(6) make `update_diagram` a real compare-and-swap
(`UPDATE … WHERE id = ? AND current_version = ?`, nothing written when no
row matches), and let a patch sent without an expected version re-read and
re-apply on the new version (up to 3 attempts) when it loses that race;
(7) validate per the issue: `add_node` rejects a duplicate id, a missing
numeric position, an unknown `parentId`, and a `data.entityId` that is not
a live element in the diagram's set; `add_edge` requires a new id and
existing `source` / `target` nodes, and a `data.relationshipId` must name a
live relationship whose endpoints are the two nodes' elements in either
direction; `update_node` / `update_edge` accept only named fields
(`position` partial, `width`, `height`, `type`, `data`; `data`,
`sourceHandle`, `targetHandle`, `type`), shallow-merge `data` with `null`
deleting a key, and re-validate a changed `entityId` / `relationshipId`;
`remove_node` refuses a node other nodes are nested in; only `{nodes,
edges}` canvases (or an empty payload) can be patched;
(8) make `sync_labels` set each targeted node's `data.label` to its
element's current name and touch nothing else — positions, sizes, `visual`
and every other key stay as stored, since the diagram owns presentation
(ADR-230 F1); nodes whose element is deleted are reported as `skipped`;
(9) add `IrisClient.patch_diagram`, MCP tool `patch_diagram` (structured
`{success: false, error, current_version | op_index, message}` payloads for
409 / 422, `auth_required` on 401/403, `web_url` decoration) and CLI
`iris patch diagram <id> --from-json FILE [--expected-version N]`, all on
the one client method (§13); point the MCP server instructions (seed and
fallback) and `update_diagram`'s description at `patch_diagram` for small
edits;
(10) treat HTTP `PATCH` as its own §14 write verb, `patch`: the parity
checker maps `@router.patch(...)` (other than `/parent`) to `patch`, and
recognises `patch_<entity>` MCP tools and `@patch_app.command(...)` CLI
commands, so `PATCH /api/diagrams/{id}` must be matched by `patch_diagram`
and `iris patch diagram`,

**and neglected**
(a) a separate persistence path for patches (e.g. writing the version row
directly) — rejected: it would duplicate `update_diagram`'s normalisation,
notation detection, indexing, thumbnails, set membership and relationship
auto-create, and drift from it; acceptance requires identical stored data;
(b) RFC 6902 JSON Patch over the raw canvas — rejected: index-addressed
paths (`/nodes/137/position`) break when the canvas is reordered, can't
express "remove a node and its edges" or "sync labels", and can't be
validated against elements and relationships;
(c) `POST /api/diagrams/{id}/patch` — rejected: the parity checker treats a
POST sub-route as an operational action and would not enforce MCP/CLI
parity for it; `PATCH` on the resource is the HTTP verb for "apply a set of
changes";
(d) attributing `PATCH` to the existing `update` verb — rejected: it would
pass the parity check without any patch tool or command, since
`update_diagram` already exists on both surfaces;
(e) a mandatory `If-Match` (as on `PUT`) — rejected: a patch only carries
the changed items, so applying it to the latest version is the useful
default (the issue marks `expected_version` optional); callers who need
the check pass it;
(f) per-op partial success (the ADR-200 batch pattern) — rejected: later
operations routinely depend on earlier ones (an edge to a node added in the
same patch), and the issue requires all-or-nothing;
(g) validating pydantic models per op kind — rejected: shape errors would
come back in FastAPI's list format while semantic errors come from the
engine; one validator gives every error the same `operations[i] (op):`
form and keeps the engine usable without HTTP;
(h) letting `add_node` pull an element from another set onto the canvas
(which a full `update_diagram` allows, moving the element into the
diagram's set) — rejected per the issue: an agent path shouldn't silently
move elements between sets or collections;
(i) the issue's "nice to have" items — out of scope (see Follow-up).

**to achieve** small, safe agent edits to large diagrams: a patch sends only
what changes, can't drop untouched nodes, fails whole with a named
operation, is refused rather than overwriting when the caller's view is
stale, fixes stale labels without disturbing layout, and is stored
indistinguishably from a full update; with §14 parity for the new verb
enforced in CI,

**accepting that** a patch re-reads and re-writes the whole stored canvas
server-side (the win is the request size and safety, not server work); a
patch that changes nothing still creates a version, as a full update does;
existing canvas nodes whose elements live in another set are still pulled
into the diagram's set on save — identical to a full update, which is the
acceptance bar; the post-commit side effects (search, thumbnails,
membership, relationship auto-create) stay best-effort as in
`update_diagram`; and on Supabase the version-pointer update and the
version-row insert are still two autocommitted statements, as for every
diagram save (not changed here).

---

## Consequences

- New REST route `PATCH /api/diagrams/{id}`; CORS allows `PATCH`. No schema
  change, so migration parity (§15) is untouched. New SQL is portable:
  `?` placeholders, chunked `IN` lists (`app/common/id_chunks.py`, shared
  with ADR-248's element hydration), rows read positionally, and the
  compare-and-swap relies on `rowcount`, which both adapters report.
- `update_diagram` (every `PUT`, AI apply and import save) now fails with a
  version conflict instead of racing when a write lands between its
  version read and its update.
- Write-scope: the same `assert_write_allowed(collection_of_diagram(...))`
  gate as `PUT /api/diagrams/{id}` (ADR-237/238).
- `iris-client`: error responses whose `detail` is an object with a
  `message` now surface that message as `IrisHTTPError.detail`; the full
  object stays on `exc.response`.
- Package versions: backend, frontend, iris-client and iris-mcp → 6.51.0.

### Follow-up (out of scope)

- `get_diagram` options to read a subset — `node_ids`, `entity_ids`, or the
  n-hop neighbourhood of a node — so agents don't need the full canvas to
  find where to place things.
- `add_node` with relative placement: `position: {near: <node_id>,
  offset: {x, y}}`.
- An option for canvas labels to follow element names automatically
  (instead of an explicit `sync_labels`).
- A `parentId` change in `update_node` (re-nesting) if agents need it.

## Dependencies

- SPEC-003-A (diagram CRUD, `If-Match`), ADR-178 (MCP update tools),
  ADR-182 (surface parity, protocol §14), ADR-218 (canvas normalisation),
  ADR-230 (F1: the diagram owns presentation), ADR-237 / ADR-238 (collection
  write-scope), ADR-248 (batched element lookups), ADR-249 (relationship
  tools, edge `relationshipId` reuse).

## References

- Issue: [#301](https://github.com/cgbarlow/iris/issues/301)
- Implementation spec: [SPEC-252-A](./specs/SPEC-252-A-Patch-Style-Diagram-Updates.md)
