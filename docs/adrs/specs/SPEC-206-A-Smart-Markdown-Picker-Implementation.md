# SPEC-206-A: Smart Markdown picker evolution — implementation

Implements: [ADR-206](../ADR-206-Smart-Markdown-Picker-Evolution.md)
Builds on: [SPEC-205-A](./SPEC-205-A-Smart-Markdown.md)
Status: Living

## Token grammar (extended)

```
TOKEN     := "{{" ENTITY_TYPE ":" ID ":" FIELD_SPEC "}}"
ENTITY    := "element" | "package" | "diagram" | "set" | "collection"
ID        := <GUID string, no colons>
FIELD     := "name" | "description" | "attr:" ATTR_PATH
ATTR_PATH := SEG ("/" SEG)*
SEG       := /[^/}]+/   (any chars except '/' and '}')
```

Backward compatibility:

- Existing v6.14.x tokens with single-segment paths (`attr:Unit`)
  resolve identically — the path walker reduces to one step.
- The regex from SPEC-205-A
  (`(name|description|attr:[^}]+)`) already permits `/` because
  `[^}]+` accepts it. No regex change needed; only the resolver
  behaviour changes.

## Resolver — `_resolve_attr_path(data, path_segments)`

In `backend/app/diagrams/smart_markdown.py`:

```python
def _resolve_attr_path(node: Any, segments: list[str]) -> Any | None:
    for seg in segments:
        if isinstance(node, dict):
            if seg in node:
                node = node[seg]
                continue
            return None
        if isinstance(node, list):
            if seg.isdigit():
                idx = int(seg)
                if 0 <= idx < len(node):
                    node = node[idx]
                    continue
                return None
            # named-array lookup: every item is a dict with a `name`
            if node and all(isinstance(i, dict) and "name" in i for i in node):
                match = next((i for i in node if i.get("name") == seg), None)
                if match is None:
                    return None
                node = match
                continue
            return None
        # primitive but more segments remain
        return None
    return node
```

Called from `_fetch_element_field`:

```python
if field_spec.startswith("attr:"):
    raw_path = field_spec[len("attr:"):]
    segments = [s for s in raw_path.split("/") if s]
    if not segments:
        return None
    data = json.loads(row[2]) if isinstance(row[2], str) else row[2]
    if not isinstance(data, dict):
        return None
    resolved = _resolve_attr_path(data, segments)
    if resolved is None:
        return None
    if isinstance(resolved, (dict, list)):
        return str(resolved)  # preserve legacy literal-render behaviour
    return str(resolved)
```

The "return None" branches collapse to strikethrough at the
caller (`_resolve_one`).

## `/api/search/entities` — substring + scope

```
GET /api/search/entities?q=<str>&types=<csv?>&collection_id=<guid?>&set_id=<guid?>&limit=<1..50?>
```

Behaviour:

- `LIKE '%q%'` (was `'q%'`) across `elements.name`, `packages.name`,
  `diagrams.name`, `sets.name`, `collections.name`.
- `set_id` narrows to entities directly inside that set
  (`elements.set_id`, `packages.set_id`, `diagrams.set_id`). Sets
  and collections are excluded from results when `set_id` is set.
- `collection_id` narrows to the collection's subtree:
  - sets where `sets.collection_id = ?`
  - elements/packages/diagrams whose `set_id IN (SELECT id FROM sets WHERE collection_id = ?)`
- Both `set_id` and `collection_id` together → `set_id` wins (more
  specific).
- Response shape unchanged: `[{id, entity_type, name}]`.

## `/api/picker/browse` — hierarchical browse

```
GET /api/picker/browse?scope=root
GET /api/picker/browse?scope=collection&collection_id=<guid>
GET /api/picker/browse?scope=set&set_id=<guid>
GET /api/picker/browse?scope=set_bucket&set_id=<guid>&entity_type=element|package|diagram
```

Response:

```json
{
  "breadcrumb": [
    {"label": "Root"},
    {"label": "Groceries", "scope": "collection", "id": "guid"},
    {"label": "Pantry", "scope": "set", "id": "guid"},
    {"label": "Elements", "scope": "set_bucket", "id": "guid", "entity_type": "element"}
  ],
  "items": [{"id": "...", "entity_type": "element", "name": "..."}],
  "counts": {"packages": 3, "diagrams": 12, "elements": 47}
}
```

Per-scope semantics:

| Scope | `items` | `counts` |
|---|---|---|
| `root` | all collections | omitted |
| `collection` | sets in this collection | omitted |
| `set` | empty list | counts of packages/diagrams/elements in this set |
| `set_bucket` | entities of `entity_type` in this set | omitted |

Soft-deleted entities excluded.

## `/api/elements/{id}/data-tree`

Returns a single-level descriptor of a node within an element's
`data` JSON. Optional `path` query param walks deeper.

```
GET /api/elements/{id}/data-tree
GET /api/elements/{id}/data-tree?path=attributes
GET /api/elements/{id}/data-tree?path=attributes/Unit
```

Response shapes (one of):

```json
{"kind": "dict",          "keys":  ["name", "description", "attributes", ...]}
{"kind": "list_of_named", "names": ["Unit", "Products", ...]}
{"kind": "list",          "length": 4}
{"kind": "primitive",     "value": "g"}
{"kind": "empty"}                    // when data is null / not a dict
```

The legacy `/api/elements/{id}/attribute-keys` endpoint remains
in place for browsers on v6.14.x cached frontends.

## Frontend — `SmartMarkdownSlashPicker.svelte`

### Props (new)

```ts
interface Props {
  oninsert: (token: string) => void;
  onclose: () => void;
  existingSource: string;   // for Recent chip derivation
}
```

### Browse mode state

```ts
type BreadcrumbStep = {
  label: string;
  scope?: 'collection' | 'set' | 'set_bucket';
  id?: string;
  entity_type?: 'element' | 'package' | 'diagram';
};

let breadcrumb: BreadcrumbStep[] = $state([{ label: 'Root' }]);
let items: PickerItem[] = $state([]);
let counts: { packages: number; diagrams: number; elements: number } | null = $state(null);
let recentChips: { type: string; id: string; name: string }[] = $state([]);
let query = $state('');
```

### Drill mode state

```ts
let mode: 'browse' | 'drill' = $state('browse');
let chosenEntity: PickerItem | null = $state(null);
let drillPath: string[] = $state([]);
let drillNode: TreeDescriptor | null = $state(null);
let drillHighlightIdx = $state(0);
let drillFilter = $state('');
```

### Recent chip derivation

```ts
const TOKEN_RE = /\{\{(element|package|diagram|set|collection):([^:}]+):[^}]+\}\}/g;
function deriveRecent(source: string): {type: string; id: string}[] {
  const seen = new Set<string>();
  const out: {type: string; id: string}[] = [];
  for (const m of source.matchAll(TOKEN_RE)) {
    const key = `${m[1]}:${m[2]}`;
    if (!seen.has(key)) { seen.add(key); out.push({type: m[1], id: m[2]}); }
  }
  return out;
}
```

Names are resolved by issuing one `/api/search/entities?q=<name-or-id>`
batch per chip; or, more cheaply, by a `GET /api/elements/{id}`
style lookup that already returns the current name. For v1 we
issue at most N=10 individual GET requests in parallel, then cap
the chip list at 10. (Pragmatic, no new batch endpoint required.)

### Keystroke handling — drill mode

```
ArrowDown / ArrowUp     → highlight ±1 within current menu
'.'                     → if highlighted is container, drill in
                          (push segment, fetch next descriptor)
                        → if highlighted is primitive, insert + close
Tab                     → same as '.'
Enter                   → if primitive: insert + close
                        → if container: drill (same as Tab)
letter / digit          → append to drillFilter; menu narrows
Backspace (filter empty)→ pop last drillPath segment
Backspace (filter set)  → trim filter
Escape                  → emit onclose
```

The "highlighted is container vs primitive" decision uses the
descriptor `kind` of the highlighted item. The menu items are
labelled and styled accordingly (`▸` for containers).

### Token assembly

```ts
function emitToken() {
  if (!chosenEntity) return;
  if (drillPath.length === 0) {
    // primitive 'name' or 'description' chosen
    oninsert(`{{${chosenEntity.entity_type}:${chosenEntity.id}:${drillTerminal}}}`);
    return;
  }
  oninsert(`{{${chosenEntity.entity_type}:${chosenEntity.id}:attr:${drillPath.join('/')}}}`);
}
```

## Frontend — `DiagramDialog.svelte` sort

```ts
let filteredTypes = $derived.by(() => {
  const types = (registryTypes.length > 0)
    ? registryTypes.filter((t) => t.notations.some((n) => n.notation_id === notation))
                   .map((t) => ({ value: t.id, label: t.name }))
    : (NOTATION_TYPE_FALLBACK[notation] ?? NOTATION_TYPE_FALLBACK['simple']);
  return [...types].sort((a, b) => a.label.localeCompare(b.label));
});
```

Each `NOTATION_TYPE_FALLBACK[notation]` array is also reordered
alphabetically by label in source. `markdown` becomes:

```ts
markdown: [
  { value: 'dynamic_list', label: 'Dynamic List' },
  { value: 'smart_markdown', label: 'Smart Markdown' },
  { value: 'text',          label: 'Standard Markdown' },
],
```

## Creation prompts (Protocol §14 §13)

Two rows added to `backend/app/seed/creation_prompts.py` under the
`layer = 'diagram_type'` group, with `notation = 'markdown'`:

```python
{
  "id": "creation-format-md-smart-markdown",
  "name": "Smart Markdown",
  "description": "Authoring rules for the smart_markdown diagram type (markdown notation).",
  "layer": "diagram_type",
  "notation": "markdown",
  "diagram_type": "smart_markdown",
  "purpose": "creation_format",
  "display_order": 1,
  "content": """
    ## Smart Markdown — data shape
    Provide `data.markdown_source` as a string. The render
    pipeline resolves inline tokens of the form
    `{{<type>:<id>:<field>}}` where:
      - `<type>` ∈ element | package | diagram | set | collection
      - `<id>` is the entity GUID
      - `<field>` is `name`, `description`, or for elements
        `attr:KEY` (single key) or `attr:SEG/SEG/...` (nested
        path into `element.data`, named lookup for arrays of
        dicts with a `name` field).
    Unresolved tokens render as strikethrough.
    `data.content` is server-synthesised; never set it.
  """,
},
{
  "id": "creation-format-md-dynamic-list",
  "name": "Dynamic List",
  "description": "Authoring rules for the dynamic_list diagram type (markdown notation).",
  "layer": "diagram_type",
  "notation": "markdown",
  "diagram_type": "dynamic_list",
  "purpose": "creation_format",
  "display_order": 1,
  "content": """
    ## Dynamic List — data shape
    Provide:
      - `data.source` ∈ `diagram_relationships` |
        `package_elements`
      - `data.show_description` (bool) — if true, each bullet
        is suffixed with the entity's description in parens.
    For `diagram_relationships`, emits two bullets per
    intra-diagram relationship (source name, then target name).
    For `package_elements`, emits one bullet per element in
    the package, sorted alphabetically.
    `data.content` is server-synthesised; never set it.
  """,
},
```

Idempotency: existing `INSERT OR IGNORE` + `UPDATE` re-seed cycle
in this file. No migration file; runs on every startup.

## Tests

- `backend/tests/test_diagrams/test_smart_markdown.py` — extend
  with the new path cases (named lookup, numeric index, missing
  intermediate, legacy single-key on container, dict-key vs
  name-collision).
- `backend/tests/test_search/test_entity_search.py` — extend with
  substring and scope (set / collection) cases.
- `backend/tests/test_search/test_picker_browse.py` (new) — all
  four scopes; empty results; counts.
- `backend/tests/test_elements/test_data_tree.py` (new) — each
  descriptor `kind`; missing path; deleted element.
- `backend/tests/test_seed/test_creation_prompts_markdown_types.py`
  (new) — both rows present after seeding; content contains
  `markdown_source` and `source ∈ diagram_relationships`.
- `frontend/src/lib/canvas/text/SmartMarkdownSlashPicker.test.ts`
  (extend) — hierarchical browse calls; subtree-scoped search;
  Recent chip derivation; drill keystroke flow (`.`, Tab, Enter,
  Backspace pop); token assembly with paths.
- `frontend/src/lib/components/DiagramDialog.test.ts` (extend or
  new) — filteredTypes alphabetical order.

## Verification — manual smoke

1. `./scripts/dev.sh restart`
2. In a Smart Markdown view, type `/`. Picker shows Recent chips
   (empty initially) + breadcrumb "Root" + collections list.
3. Click "Groceries" → breadcrumb shows `Root > Groceries`,
   list shows sets.
4. Type `pork` in the input → results from anywhere under Groceries
   (not just sets at this level).
5. Click "Pantry" set → buckets Packages/Diagrams/Elements with
   counts. Buckets with count 0 hidden.
6. Click Elements bucket → element list.
7. Click "pork mince" → drill strip appears
   `[pork mince].`. Menu lists name, description, attributes.
8. Type `att` → menu narrows to `attributes`. Press Tab → drill
   into attributes. Menu shows `Unit`, `Products`, `Preferred
   product`.
9. Press Tab on `Unit` → drill in. Menu shows sub-fields
   (`type`, `notes`, `scope`, ...).
10. Highlight `type` and press Enter → token inserted as
    `{{element:GUID:attr:attributes/Unit/type}}`.
11. Switch to view mode → renders `g`.
12. Reopen picker → "pork mince" appears as a Recent chip; click
    → straight into drill on that element.
13. `New view` dialog → markdown notation → dropdown shows
    `Dynamic List`, `Smart Markdown`, `Standard Markdown` in
    alphabetical order.
14. `pytest -x backend/tests`, `npm run test:unit` (frontend) —
    both green.
