# SPEC-205-A: Smart Markdown view type

Implements: [ADR-205](../ADR-205-Smart-Markdown-View-Type.md)
Status: Living

## Diagram type registration

Seeded by `m070` / `m074`:

```
diagram_types row:
  id            = 'smart_markdown'
  name          = 'Smart Markdown'
  description   = 'Markdown with inline references to Iris entity fields.'
  display_order = 17

diagram_type_notations row:
  diagram_type_id = 'smart_markdown'
  notation_id     = 'markdown'
  is_default      = 0  -- markdown notation already defaults to text
```

## Storage shape

```jsonc
diagrams.data = {
  "markdown_source": "string — user-edited",   // persisted on save
  "content":         "string — synthesised",    // computed on GET
  // existing dynamic_source / other fields ignored for this type
}
```

`content` is overwritten every read by `_maybe_synthesise_content`
— writes to it are ignored.

## Token grammar

```
TOKEN     := "{{" ENTITY_TYPE ":" ID ":" FIELD_SPEC "}}"
ENTITY    := "element" | "package" | "diagram" | "set" | "collection"
ID        := <GUID string, no colons>
FIELD     := "name" | "description" | "attr:" ATTR_KEY
ATTR_KEY  := /[^}]+/   (any non-}, allowing dots, spaces, dashes)
```

Regex used by the resolver:

```python
TOKEN_RE = re.compile(
    r"\{\{(element|package|diagram|set|collection):"
    r"([^:}]+):"
    r"(name|description|attr:[^}]+)\}\}"
)
```

`attr:` is only honoured for `entity-type=element`. For any other
entity, `attr:X` resolves as unresolvable (strikethrough).

## Resolver — `backend/app/diagrams/smart_markdown.py`

```python
async def compute_smart_markdown_content(
    db: DatabasePort, diagram_id: str,
) -> str:
    """Return the resolved markdown for a smart_markdown diagram."""
    source = await _read_source(db, diagram_id)
    if not source:
        return "_No content yet._"
    return await _resolve_tokens(db, source)
```

Per-entity lookups:

| Entity | Source | Filter |
|---|---|---|
| element | `element_versions ev JOIN elements e` | `e.is_deleted = 0`, current_version |
| package | `package_versions pv JOIN packages p` | `p.is_deleted = 0`, current_version |
| diagram | `diagram_versions dv JOIN diagrams d` | `d.is_deleted = 0`, current_version |
| set | `sets` | (no soft-delete column) |
| collection | `collections` | (no soft-delete column) |

For unresolvable tokens, replacement is `~~{{ORIGINAL}}~~`. Token
matches that overlap are processed left-to-right; the regex's
left-anchored greedy `attr:` body avoids overlapping in practice.

## Dispatch — `backend/app/diagrams/service.py`

In `_maybe_synthesise_content`:

```python
if diagram_type == "smart_markdown":
    data["content"] = await compute_smart_markdown_content(db, diagram_id)
```

## Search endpoint

`GET /api/search/entities?q=<prefix>&types=<csv>&limit=<int>`

Parameters:
- `q` (required): prefix to match (case-insensitive). Empty string
  returns 422.
- `types` (optional): CSV of `element,package,diagram,set,collection`.
  Default is all five. Unknown types ignored.
- `limit` (optional, default 25, max 50).

Response:

```json
[
  {"id": "abc-123", "entity_type": "element", "name": "Pork mince"},
  ...
]
```

Implementation: UNION across the entity tables, each ORDER BY
`LOWER(name)`, LIMIT applied to the union. Deleted entities excluded
(sets/collections have no soft-delete flag — included as is).

## Attribute-keys endpoint

`GET /api/elements/{id}/attribute-keys`

Response:

```json
["Unit", "Calories", "Origin"]
```

Sorted alphabetically (case-sensitive). Empty list if the element's
`data` is null, missing, or not a dict. 404 if the element doesn't
exist or is deleted.

## Frontend canvas — `SmartMarkdownCanvas.svelte`

Sibling to `TextCanvas.svelte`. Edit mode is the same textarea +
`MarkdownEditorToolbar` pattern. View mode delegates to
`MarkdownView` reading `data.content`.

Slash trigger:

```svelte
function onKeydown(e: KeyboardEvent) {
  if (e.key !== '/') return;
  const ta = e.currentTarget as HTMLTextAreaElement;
  const cursor = ta.selectionStart;
  const prevChar = cursor === 0 ? '\n' : ta.value[cursor - 1];
  if (prevChar !== ' ' && prevChar !== '\n' && cursor !== 0) return;
  e.preventDefault();
  openPicker(ta);
}
```

Token insertion uses `insertAtCursor(ta, token)` from
`markdownEditorToolbarHelpers.ts`.

## Frontend picker — `SmartMarkdownSlashPicker.svelte`

Two-step popover. State machine:

```
IDLE → ENTITY_SEARCH → ENTITY_SELECTED → FIELD_SELECT → DONE
                                       ↓ (esc anywhere)
                                   IDLE/closed
```

- Entity search: debounced 150ms call to `/api/search/entities?q=...`.
  Up/Down/Enter to pick. Each entry shows a coloured `[element]`-
  style badge + name.
- Field select for non-elements: hardcoded `[name, description]`.
- Field select for elements: fetch `/api/elements/{id}/attribute-keys`
  on entity-pick; render `name`, `description`, then each
  `attr:<key>` row alongside.
- Enter inserts the token at the saved caret position; popover closes.

## Acceptance criteria

1. Smart Markdown appears in the diagram-type picker after migration runs.
2. Creating a Smart Markdown view persists `markdown_source` round-trip.
3. `GET /api/diagrams/{id}` for a smart_markdown returns
   `data.content` with tokens resolved.
4. Resolver substitutes element name, description, and
   `attr:<key>`.
5. Resolver substitutes package, diagram, set, collection name and
   description.
6. Unresolvable tokens render as `~~{{...}}~~`.
7. Multiple tokens on one line are all resolved.
8. Surrounding markdown is preserved byte-for-byte except for
   token regions.
9. `/api/search/entities?q=pork` returns elements whose name
   starts with "pork" (case-insensitive).
10. `/api/elements/{id}/attribute-keys` returns the data dict
    keys, sorted.
11. The picker opens on `/` after whitespace or at line start.
12. The picker's two-step flow inserts a well-formed token.
13. Export to docx and pdf includes resolved content (via existing
    pipeline, no new code).
14. `scripts/check_surface_parity.py` stays clean (read-only
    endpoints are out of scope per §14).

## Tests

`backend/tests/test_migrations/test_smart_markdown_schema.py`:

1. Type registered with id, name, description, display_order.
2. Notation mapping to `markdown` with `is_default=0`.
3. Migration is idempotent.
4. Supabase mirror has matching INSERT statements with `ON CONFLICT`.
5. Supabase mirror references the SQLite migration in header.

`backend/tests/test_diagrams/test_smart_markdown.py`:

1. Resolves element name.
2. Resolves element description.
3. Resolves element `attr:<key>`.
4. Resolves package/diagram/set/collection name + description.
5. Unknown entity-type token → strikethrough.
6. Missing element id → strikethrough.
7. Missing attribute key → strikethrough.
8. Deleted element → strikethrough.
9. `attr:X` on non-element → strikethrough.
10. Multiple tokens on one line all resolve.
11. Markdown surrounding tokens is preserved.
12. Empty `markdown_source` returns placeholder.

`backend/tests/test_search/test_entity_search.py`:

1. Prefix match returns matching elements.
2. Type filter narrows to one entity type.
3. Deleted entities excluded for soft-deletable types.
4. Limit honoured.
5. Empty `q` returns 422.

`backend/tests/test_elements/test_attribute_keys.py`:

1. Returns sorted keys for an element with `data`.
2. Returns empty list for an element with no data.
3. Returns empty list when data is not a dict.
4. 404 for unknown element.
5. 404 for deleted element.

## Release ordering

Type registration migrations are seed-only; the registry service
tolerates missing rows. Safe to deploy code before running the
Supabase migration — the type just won't appear in the picker
until `scripts/supabase-migrate.sh` runs. Once it does, the type
shows up.

## Verification

```
.venv/bin/python -m pytest \
  backend/tests/test_migrations/test_smart_markdown_schema.py \
  backend/tests/test_diagrams/test_smart_markdown.py \
  backend/tests/test_search/test_entity_search.py \
  backend/tests/test_elements/test_attribute_keys.py
.venv/bin/python scripts/check_surface_parity.py
```
