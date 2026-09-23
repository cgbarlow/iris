# ADR-248: Hydrate the Diagram View From One Batched Elements Request

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-248 |
| **Initiative** | Stop the diagram view fetching every canvas element four times |
| **Proposed By** | Engineering |
| **Date** | 2026-09-23 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** the diagram view (`/views/[id]`), which after loading
a diagram refreshes each element-linked canvas node from its element
(`refreshNodeDescriptions`, ADR-192 / ADR-230 F1) and collects the tags of
the elements on the canvas as "inherited" tags (`loadInheritedTags`), and
anonymous readers, who share a 30-requests-per-minute rate-limit bucket
(ADR-129),

**facing** a page load that made **4 × N** `GET /api/elements/{id}`
requests for a diagram with N element nodes. Measured locally in headless
Chromium on a 37-node diagram, anonymously: 166 API requests, 148 of them
element GETs (exactly 4 per element), with every other page-load request
appearing twice; 136 of the 166 came back `429`. The 274-node "Full Family
Tree" on UAT needs about 1,100 requests, so anonymous viewers get "Failed to
load diagram" and a canvas of 429s. Three causes, confirmed in the code:

1. **Double load.** The `$effect` that reads `page.params.id` called
   `loadDiagram(id)` directly. `loadDiagram` reads `areThemesLoaded()` —
   the `themesLoaded` `$state` in `themeStore.svelte.ts` — before its first
   `await`, so the effect subscribed to it. When `loadThemes()` flipped the
   flag, the effect re-ran and the whole page load ran a second time.
2. **Two loops per load.** Each load ran `refreshNodeDescriptions()` (one
   element GET per node, in parallel) and `loadInheritedTags()` (one element
   GET per node again, sequentially, only to read `.tags`).
3. **Per-request server cost.** `get_element` computes
   `diagram_usage_count` with `dv.data LIKE '%<id>%'` over every current
   diagram version — a full scan of diagram data per element request,

**we decided to**

- call `untrack(() => loadDiagram(id))` in the effect, so only
  `page.params.id` is tracked and nothing `loadDiagram` reads synchronously
  (the theme store today, anything else tomorrow) can re-run the load;
- add **`GET /api/diagrams/{diagram_id}/elements`** (anonymous-readable via
  `get_optional_user`, like `GET /api/elements/{id}`; 404 when the diagram
  is missing or soft-deleted). It returns an `ElementResponse` — the same
  fields and values as `GET /api/elements/{id}` — for every distinct
  `node.data.entityId` on the diagram's current canvas, in canvas order,
  skipping nodes without an entityId and deleted or unknown elements;
- compute it in the elements service (`get_elements_by_ids`) with a bounded
  number of queries: per chunk of up to 400 ids, one query each for element
  rows, tags, relationship counts (grouped) and diagram usage counts (one
  scan of current diagram versions for the whole chunk, with `get_element`'s
  exact `LIKE '%' || id || '%'` semantics). Chunking keeps every statement
  under SQLite's historical 999-variable limit;
- share code rather than copy it (protocol §13): `get_element` and
  `get_elements_by_ids` use one element `SELECT` and one row-to-dict mapper;
  the canvas-entityId extraction that was inlined in
  `get_diagram_relationships` (ADR-184) — and duplicated in
  `list_element_relationships_for_diagram` — moves to
  `app/diagrams/canvas_entities.py` and serves all three;
- have the page make that one call (`loadDiagramElements`) and derive both
  the node refresh and the inherited tags from its result, via pure helpers
  in `frontend/src/lib/canvas/diagramElementHydration.ts`. No request is made
  when no node links to an element. If the request fails, the canvas stays
  as stored,

**and neglected** (1) memoising `GET /api/elements/{id}` responses in the
browser — rejected: it removes the duplicate loop but still sends N requests
per diagram, so a 274-node diagram still exceeds the anonymous bucket on
its own; (2) raising the anonymous rate limit — rejected: it hides the
problem and raises the cost of every scrape; (3) dropping
`diagram_usage_count` from the batch to make it cheaper — rejected: the
canvas shows it, and a payload that differs from the single-element
endpoint invites drift; (4) matching usage in Python by loading every
diagram's data into the app — rejected: it ships every diagram's JSON over
the wire on each page load (costly against a remote Supabase database), and
reproducing `LIKE`'s per-backend case rules in Python risks subtle
differences; (5) adding MCP/CLI surfaces — not needed: this is a read
endpoint, and protocol §14 applies to write endpoints,

**to achieve** a diagram page load that makes **one** element request
instead of 4N — the Full Family Tree goes from about 1,100 requests to about
18 at most in total (measured after the change: 11), comfortably inside the
anonymous bucket — and a server cost that no longer scales as one diagram
scan per node,

**accepting that** the endpoint returns the full element payload even
though the canvas uses only part of it (it keeps the contract identical to
`GET /api/elements/{id}` and lets the page reuse `elementToNodeData`), and
that the usage-count query is still a `LIKE` scan over diagram data — now
one scan per 400 elements rather than one per element.

---

## Consequences

- Element requests on page load: **4N → 1** (0 for a canvas with no
  element-linked nodes). The other page-load requests (diagram, parent set,
  versions, bookmark status, all tags, ancestors, relationships, comment
  count) are no longer sent twice.
- Measured after the change (local, headless Chromium, anonymous, fresh
  worktree backend + frontend): a 37-node and a 274-node diagram each load
  with **11** API requests in total — one `GET /api/diagrams/{id}/elements`,
  no `GET /api/elements/{id}`, no 429, and every node rendered. The batched
  response for 274 elements took 14 ms locally (179 KB).
- New read endpoint only: no schema or migration change (protocol §15 N/A);
  surface parity (protocol §14) is N/A because it is a `GET`. MCP and CLI
  are unchanged.
- The query count is independent of the node count and is pinned by
  `tests/test_diagrams/test_diagram_elements.py`
  (`TestDiagramElementsQueryBound`).
- `list_element_relationships_for_diagram` now tolerates a canvas whose
  `nodes` is not a list of objects instead of raising.

## Dependencies

- ADR-129 (public HTTP API, anonymous rate-limit bucket).
- ADR-184 (element → package memberships on the diagram relationships
  route — the entityId extraction now shared).
- ADR-192 (canvas nodes hydrate via `elementToNodeData`).
- ADR-230 F1 (element refresh preserves diagram-owned node presentation).
- ADR-237 (`collection_id` on the element payload).

## References

- Implementation spec: [SPEC-248-A](./specs/SPEC-248-A-Batch-Diagram-Element-Hydration.md)
