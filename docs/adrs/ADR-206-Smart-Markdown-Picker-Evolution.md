# ADR-206: Smart Markdown picker evolution — hierarchical browse, nested drill, recent chips

Status: Accepted (2026-05-19)

Supersedes: the "Picker UX (locked v1)" section of [ADR-205](./ADR-205-Smart-Markdown-View-Type.md).
The token-format contract, storage model, resolver dispatch, and security posture from ADR-205 are unchanged.

## Context

ADR-205 / v6.14.0 shipped a deliberately minimal two-step picker:
prefix typeahead, then a flat field list. Issue #185 follow-up
comments (2026-05-19) surfaced five UX gaps:

1. Prefix-only search misses "mince" → "pork mince".
2. Empty `/` opens a picker with no content; users must guess what
   to type. A discoverable browse mode is needed.
3. When the user is already focused on a scope (a set, a collection),
   they expect search to narrow to that scope.
4. Selecting a re-used entity requires re-searching from scratch.
5. Element attributes that are arrays-of-dicts (the ArchiMate-style
   `data.attributes = [{name, type, ...}, ...]` pattern, very common
   in the Groceries set) render as the whole array literal because
   the resolver only walks one segment deep.

A sixth, unrelated gap landed in the same comment thread: the
`New view → markdown` type dropdown order is registry-driven
(`display_order, name`) rather than alphabetical, which surprises
users who expect alphabetical selection lists.

## Decision

Evolve the picker without changing the persisted token format.
Five UX changes + one token-format extension + one cosmetic sort.

### 1. Substring search (was prefix)

`/api/search/entities` switches from `LIKE 'q%'` to `LIKE '%q%'`
across all five entity-type SELECTs. Case-insensitive (already).
Same response shape; no client-side change required for callers
that only want substring matching.

### 2. Hierarchical browse mode

A new endpoint `GET /api/picker/browse` returns the items visible
at a given scope. Scope is one of:

- `root` → list of collections (no parent context required)
- `collection` (`collection_id` required) → list of sets in that
  collection
- `set` (`set_id` required) → no items; `counts` carries
  `{packages, diagrams, elements}` so the frontend can render
  bucket cards
- `set_bucket` (`set_id` + `entity_type` required) → list of
  entities of that type in that set

The response shape is uniform:

```json
{
  "breadcrumb": [{"label": "Root"}, {"label": "Groceries", "scope": "collection", "id": "..."}, ...],
  "items": [{"id": "...", "entity_type": "element", "name": "..."}],
  "counts": {"packages": 3, "diagrams": 12, "elements": 47}
}
```

The breadcrumb is regenerated server-side from the parent IDs, so
the frontend doesn't have to track ancestor names.

### 3. Subtree-scoped search

`/api/search/entities` accepts optional `collection_id` and `set_id`
query params. When `set_id` is given, results restrict to that set
(elements/packages/diagrams with `set_id == ?`). When `collection_id`
is given, results restrict to that collection's subtree (sets
directly + entities whose `set_id` is in that collection's sets).

The picker reads its current breadcrumb scope and passes the
appropriate `set_id` / `collection_id` with every search query.
Root-level search omits both → global match.

### 4. Recent chips derived from existing tokens

No new persistence. The picker scans the current `markdown_source`
client-side (regex `\{\{(element|package|diagram|set|collection):([^:}]+):[^}]+\}\}`),
dedupes by `(type, id)`, fetches the current names for those IDs
(reuses the same query path as the picker), and renders them as
chips at the top of root view. Clicking a chip jumps straight to
drill mode for that entity.

Why derive rather than persist: every persistence option (localStorage,
backend table) has drift risk — the diagram may be edited from
another device, or the user may remove tokens. Deriving from the
live source is always accurate, requires no new schema, and matches
how every other Iris view treats `data.content`.

### 5. Nested-attribute drill (token-format extension)

The `attr:<key>` field-spec extends to `attr:SEG1/SEG2/SEG3...` —
a `/`-separated path. Existing single-key tokens (`attr:Unit`) are
the path with one segment and resolve identically; this is
backward-compatible.

At each path step, the resolver inspects the current node:

| Current node | Segment shape | Action |
|---|---|---|
| dict | matches a key | take `node[key]` |
| list | purely numeric | index `node[int(seg)]` |
| list of dicts each having a `name` field | non-numeric | find first item where `item['name'] == seg` |
| primitive | (more segments remain) | unresolvable → strikethrough |

The terminal value is `str()`'d. If the terminal is a dict or list
(legacy single-key tokens that landed on a container), the JSON
literal is rendered — preserves existing behaviour bit-for-bit.

### 6. Drill UX: hybrid IDE-style + arrow-keys

After an entity is picked, the picker collapses into a single-line
autocomplete strip: `[entity-chip].<field-completions>`. The drill
menu surfaces fields one at a time (driven by
`GET /api/elements/{id}/data-tree` for elements, fixed
`name`/`description` for others). At every step both modalities
are present:

- Arrow Up/Down highlights the current menu.
- Typing letters narrows the menu by substring.
- `.` or Tab drills into the highlighted container; on a primitive
  these insert the token and close.
- Enter on a primitive inserts; Enter on a container drills.
- Mouse click on a menu item is equivalent to Tab.
- Backspace at the start of a segment pops one path step.

This mirrors how TypeScript/Python IDEs handle property completion
while keeping the no-mouse path equally fluent.

### 7. Alphabetical type dropdown

`frontend/src/lib/components/DiagramDialog.svelte` sorts
`filteredTypes` by `label.localeCompare` after deriving from the
registry. The fallback constant `NOTATION_TYPE_FALLBACK[notation]`
arrays are reordered to match. The backend registry endpoint
remains `ORDER BY display_order, name` (other consumers may rely
on display_order); the alphabetical reordering is a presentation
concern in the dialog only.

## Surface parity (§14)

`create_diagram` (MCP + CLI) already accepts `smart_markdown` and
`dynamic_list` via the registry — both are generic write tools
that take `diagram_type` as a string. No new MCP tool or CLI
subcommand is required.

However, neither type has a diagram_type-layer creation_format
prompt in `backend/app/seed/creation_prompts.py`, so MCP/CLI users
driving programmatic creation have no documentation of the unique
`data` shapes (`markdown_source` for smart_markdown, `source` +
`show_description` for dynamic_list). This ADR adds those rows
alongside the picker changes.

## What is not changing

- The persisted token format. `{{<type>:<id>:<field-spec>}}` still
  encodes everything. New tokens can carry paths; old tokens still
  resolve identically.
- The synth-on-read dispatch (ADR-187 hook). Resolution still
  happens in `_maybe_synthesise_content`.
- Export parity. Resolved markdown still lands in `data.content`
  for docx/pdf consumption.
- DOMPurify path (Protocol §7). Resolver output is plain markdown
  routed through the existing pipeline.

## Why not a forward fuzzy ranker (Levenshtein / FTS)

User specifically described "fuzzy" with a substring example. True
fuzzy ranking adds tuning surface and edge-case ranking debugging.
Substring is enough for the recipe-builder use case, costs zero
extra infrastructure, and reuses the existing entity-search code
path.

## Why derive Recent chips rather than persist

Persisting per-user picker history adds a table, a Supabase
migration, RLS policy, an MCP exposure question (§14), and a drift
risk when the diagram is edited elsewhere. Deriving from the live
`markdown_source` is one regex and zero new state. The trade-off
is that pasting tokens from elsewhere works the same as picking
them — both populate Recent — which is the desirable behaviour.

## Why nested drill via `/` paths rather than JSON pointer or jq

`/` paths read naturally next to the existing colon-separated
token structure (`attr:attributes/Unit/type`) and accept both
named-array lookup (the recipe use case) and numeric indexing
(any other array). JSON Pointer (`/attributes/0/type`) loses the
named-lookup ergonomic. jq syntax (`.attributes."Unit".type`)
introduces double-quoting that's hostile in a brace-delimited token.

## Consequences

Backend:

- `backend/app/search/router.py` — substring + scope params; new
  `/api/picker/browse` endpoint.
- `backend/app/diagrams/smart_markdown.py` — path-walker resolver
  (`_resolve_attr_path`).
- `backend/app/elements/router.py` — new `/{id}/data-tree`
  endpoint; legacy `/attribute-keys` retained.
- `backend/app/seed/creation_prompts.py` — `smart_markdown` and
  `dynamic_list` creation_format rows.

Frontend:

- `frontend/src/lib/canvas/text/SmartMarkdownSlashPicker.svelte`
  — rewrite (browse + drill modes).
- `frontend/src/lib/canvas/text/SmartMarkdownCanvas.svelte` —
  pass `source` to picker.
- `frontend/src/lib/components/DiagramDialog.svelte` — alphabetical
  sort.

Tests: per-endpoint + resolver path cases + creation-prompts seed
test + picker Vitest.

CHANGELOG `[6.15.0]`. No DB schema changes; no paired §15
migrations needed. Render auto-deploy; no Supabase migrate step.

## Verification

```
.venv/bin/python -m pytest \
  backend/tests/test_diagrams/test_smart_markdown.py \
  backend/tests/test_search/test_entity_search.py \
  backend/tests/test_search/test_picker_browse.py \
  backend/tests/test_elements/test_data_tree.py \
  backend/tests/test_seed/test_creation_prompts_markdown_types.py
.venv/bin/python scripts/check_surface_parity.py
cd frontend && npm run test:unit
```

Manual smoke is documented in SPEC-206-A.

## See also

- Issue [#185](https://github.com/cgbarlow/iris/issues/185)
  follow-up comments (2026-05-19).
- [ADR-205](./ADR-205-Smart-Markdown-View-Type.md) (superseded
  picker UX section only).
- [ADR-187](./ADR-187-Synthesised-Content-On-Read.md) (synth-on-read
  hook; unchanged).
- §13 DRY, §14 Surface parity, §15 migration parity: `docs/protocols.md`.
