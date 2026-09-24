# SPEC-248-A: Hydrate the Diagram View From One Batched Elements Request

Implements **[ADR-248](../ADR-248-Batch-Diagram-Element-Hydration.md)**.
Amends the canvas refresh of [ADR-192](../ADR-192-Canvas-Node-Hydration-From-Element.md)
(`refreshNodeDescriptions`) and reuses the canvas extraction introduced for
ADR-184.

## 1. Root cause

| # | Where | What | Effect per page load |
|---|-------|------|----------------------|
| 1 | `frontend/src/routes/views/[id]/+page.svelte` | The `page.params.id` `$effect` called `loadDiagram(id)`, which reads `areThemesLoaded()` (`themesLoaded` `$state`) before its first `await`. `loadThemes()` flipping it re-ran the effect. | Whole load runs twice on first visit |
| 2 | same page | `refreshNodeDescriptions()` — `Promise.all` of `GET /api/elements/{id}` per node; `loadInheritedTags()` — sequential `GET /api/elements/{id}` per node for `.tags` | 2N element GETs per load |
| 3 | `backend/app/elements/service.py::get_element` | `diagram_usage_count` = `COUNT(DISTINCT d.id) … WHERE dv.data LIKE '%<id>%'` over current diagram versions | One diagram-data scan per element GET |

1 × 2 = 4N element requests. Measured (local, headless Chromium, 37-node
diagram, anonymous): 166 API requests, 148 element GETs, 136 × `429`.

## 2. API

### `GET /api/diagrams/{diagram_id}/elements`

- **Auth:** optional (`get_optional_user`) — anonymous-readable, like
  `GET /api/elements/{id}`. Counts against the caller's normal rate-limit
  bucket once.
- **200:** `ElementResponse[]` — one item per distinct live element whose id
  appears as `node.data.entityId` on the diagram's **current** canvas.
  - Order: canvas order, first occurrence wins (duplicates removed).
  - Skipped: nodes with no `data`, no `entityId`, or a non-string / empty
    `entityId`; ids of soft-deleted or non-existent elements.
  - Each item is field-for-field equal to `GET /api/elements/{id}` for that
    id: `tags` (sorted), `relationship_count` (live relationships with the
    element at either end, a self-loop counted once), `diagram_usage_count`
    (distinct live diagrams whose current-version data contains the id;
    see §3 for the two edge cases where the batch differs from `LIKE`),
    `set_name`, `collection_id`, `package_name`, `parent_element_name`,
    `stereotype` (from `metadata.stereotype`), `notation`, etc.
  - Empty canvas / no element-linked nodes → `[]`.
- **404:** diagram missing or soft-deleted (`{"detail": "Diagram not found"}`).

Route registered on the diagrams router as a two-segment path; no other
`/api/diagrams/{id}/…` route or single-segment pattern captures `elements`.

## 3. Backend changes

| File | Change |
|------|--------|
| `backend/app/diagrams/canvas_entities.py` | New. `canvas_entity_ids(canvas) -> list[str]` (JSON string or dict; ordered, de-duplicated, malformed → `[]`). `get_canvas_entity_ids(db, diagram_id) -> list[str] \| None` — one query for the live diagram's current-version data; `None` when missing/deleted. |
| `backend/app/elements/service.py` | `_ELEMENT_DETAIL_SELECT` (shared `SELECT … FROM elements … LEFT JOIN sets`) and `_element_detail_from_row(row)` (shared row → dict, incl. `stereotype`), used by `get_element` (behaviour unchanged) and the new `get_elements_by_ids(db, ids)`. |
| `backend/app/elements/diagram_usage.py` | New, pure. `count_diagram_usage(element_ids, diagram_data) -> dict[str, int]`: the single-pass usage matcher (below). |
| `backend/app/diagrams/router.py` | New `get_diagram_elements` route. `get_diagram_relationships` uses `get_canvas_entity_ids` instead of its inline extraction (ADR-184 behaviour unchanged). |
| `backend/app/package_relationships/service.py` | `list_element_relationships_for_diagram` uses `get_canvas_entity_ids` instead of its own copy. |

### `get_elements_by_ids` query plan

Ids are de-duplicated (order kept) and processed in chunks of
`_ID_CHUNK_SIZE = 400`. Per chunk:

1. `_ELEMENT_DETAIL_SELECT … WHERE e.id IN (…) AND e.is_deleted = 0`
2. `SELECT element_id, tag FROM element_tags WHERE element_id IN (…) ORDER BY element_id, tag`
3. Relationship counts — `SELECT eid, COUNT(*) FROM (SELECT id, source_element_id … UNION SELECT id, target_element_id …) AS rel_ends GROUP BY eid`. `UNION` (not `UNION ALL`) removes the duplicate `(relationship, element)` pair of a self-loop, matching `get_element`'s `source = ? OR target = ?`. Binds the chunk twice (≤ 800 variables).
Chunks with no live elements stop after query 1. Then, once per request and
only if any element was found:

4. Usage counts — `SELECT dv.data FROM diagrams d JOIN diagram_versions dv ON d.id = dv.diagram_id AND d.current_version = dv.version WHERE d.is_deleted = 0`, then `count_diagram_usage(found ids, rows)`.

Endpoint total: `1 + 3 × ceil(distinct ids / 400) + 1` queries — 5 for any
diagram up to 400 elements, regardless of node count.

#### Usage matcher (`count_diagram_usage`)

Evaluating `LIKE '%' || e.id || '%'` for a batch of ids, whether in SQL
(`CROSS JOIN elements`) or in Python (`id in data` per id), costs one
substring scan of all diagram data **per id**: O(N × total diagram bytes),
the same work as N single-element requests. The matcher instead walks each
diagram's data once:

- Ids that are UUID-shaped (`8-4-4-4-12` hex, which every Iris-generated id
  is): one regex pass per diagram finds every UUID-shaped substring,
  **including overlapping ones** (zero-width lookahead), and the result is
  intersected with the requested ids.
- Any other id: a plain `id in data` substring test (exact, O(bytes) per
  such id; none exist today).
- Each diagram adds at most 1 per id (the count is of distinct diagrams);
  `None`/empty data is skipped; every requested id is in the result, 0 when
  unmentioned.

Semantics equal `get_element`'s `LIKE '%<id>%'` (a mention anywhere in the
current-version data, e.g. inside an edge id, counts) except:

- **Case-sensitive.** This is PostgreSQL `LIKE`. SQLite `LIKE` folds ASCII
  case, so on SQLite the two endpoints could differ only if a diagram held
  an id in a different letter case; Iris writes ids verbatim.
- **`_` and `%` are literal** in the id, where `LIKE` treats them as
  wildcards.

Cost: one transfer of the live diagrams' current data per request and
O(total diagram bytes) matching, independent of the number of ids. Local
SQLite benchmark, 50 diagrams / 7.7 MB: the single-pass matcher took
100–107 ms for 37, 274 and 400 ids; the per-chunk `CROSS JOIN … LIKE` it
replaces took 148 ms, 1,015 ms and 1,390 ms, with identical counts.

`get_element` keeps its single-id `LIKE` query: one scan for one id, and
no bulk data transfer.

Supabase parity (protocol §15): rows are read positionally, only `?`
placeholders, `is_deleted = 0` (converted by the adapter), `||`
concatenation and a subquery alias — valid in both SQLite and PostgreSQL.

## 4. Frontend changes

| File | Change |
|------|--------|
| `frontend/src/routes/views/[id]/+page.svelte` | Effect calls `untrack(() => loadDiagram(id))`. `loadDiagram` calls `loadDiagramElements(id)` (replacing `refreshNodeDescriptions()` + `loadInheritedTags()`), which fetches `GET /api/diagrams/${id}/elements` once — skipped when no node has an entityId — ignores the result if the user has navigated to another diagram meanwhile, and feeds it to `refreshNodeDescriptions(elements)` and `loadInheritedTags(elements)`. On error the canvas is left as stored and inherited tags are empty. |
| `frontend/src/lib/canvas/diagramElementHydration.ts` | New, pure. `hasLinkedElements(nodes)`, `hydrateCanvasNodes(nodes, elements) -> {nodes, updated}` (the former per-node logic: `elementToNodeData`, label-prefix description trim, ADR-230 F1 presentation stripping, diff-key change detection, identity kept for unchanged nodes), `inheritedTagsFromElements(elements, ownTags)`. |

## 5. Tests (TDD — written first, red before the change)

Backend — `backend/tests/test_diagrams/test_diagram_elements.py`:

1. Payload equality: each item `==` `GET /api/elements/{id}` for elements
   with a package, a parent element, a stereotype, a non-default notation,
   tags, relationships (incl. a self-loop) and a second diagram using one of
   them; sanity asserts on the populated values.
2. De-duplication keeps first-occurrence order.
3. Deleted and unknown element ids excluded.
4. Nodes without entityId / without `data` / with empty entityId skipped.
5. Empty canvas → `[]`.
6. Missing diagram → 404; soft-deleted diagram → 404.
7. Anonymous request → 200, equal to anonymous `GET /api/elements/{id}`.
8. Query bound: an 80-node diagram issues the same number of queries as a
   3-node one, and at most 6.
9. Chunking: with `_ID_CHUNK_SIZE` patched to 7, a 30-node diagram returns
   all 30 in order with `2 + 5 × per-chunk` queries (canvas and usage once,
   rows/tags/relationships per chunk).
10. Usage pass: with 5 chunks, `diagram_versions` is queried exactly twice
    (canvas + usage) and no query uses `LIKE`.
11. Usage counts across several diagrams (a repeated mention in one
    diagram, a mention only inside an edge id, a deleted diagram, a mention
    only in a superseded version) equal `GET /api/elements/{id}`'s.

`backend/tests/test_diagrams/test_canvas_entities.py` — the extraction
helper (order, de-dup, JSON string input, skipped node shapes, malformed
canvases).

`backend/tests/test_elements/test_diagram_usage.py` — the matcher: distinct
diagram counts, repeated mentions, zero counts, empty inputs, substring
mentions (edge ids, longer hex runs), overlapping UUID-shaped substrings,
case sensitivity, non-UUID fallback, literal `_`/`%`, `None` data,
duplicate input ids.

Frontend — `frontend/tests/unit/diagramElementHydration.test.ts`: the three
helpers, plus source checks that the effect uses `untrack`, the load path
calls `/api/diagrams/${id}/elements` and no longer contains a per-node
`/api/elements/` fetch. `descriptionSync.test.ts` updated to the new shape.

## 6. Acceptance criteria

- Opening a diagram makes one `GET /api/diagrams/{id}/elements` and no
  `GET /api/elements/{id}` requests; no page-load request is sent twice.
- Canvas labels, descriptions, compartments and usage counts refresh from
  the elements as before; EA-styled node presentation is preserved.
- Inherited tags are unchanged in content and order.
- An anonymous viewer can open the 274-node Full Family Tree without 429s.

Verified locally (headless Chromium, anonymous, worktree backend and
frontend): 37-node and 274-node diagrams each load with 11 API requests,
exactly one of them `GET /api/diagrams/{id}/elements`, none duplicated, all
nodes rendered.
