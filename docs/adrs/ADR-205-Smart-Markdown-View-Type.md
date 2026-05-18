# ADR-205: Smart Markdown view type

Status: Accepted (2026-05-18)

## Context

Issue #185 asks for a new view/diagram type that lets users author
markdown with inline references to fields on any Iris entity. The
motivating use case is a recipe / meal plan:

> Enters "500", types "/", picker pops up, searches "pork mince",
> picks element, then field "Unit"; rendered output: "500g Pork mince".

Two existing pieces of the system point at this:

- [ADR-186 / m065](./ADR-186-Dynamic-List-Diagram-Type.md) registered
  `dynamic_list` under the existing `markdown` notation and used
  [ADR-187](./ADR-187-Synthesised-Content-On-Read.md)'s
  `_maybe_synthesise_content` hook to render computed markdown at
  read time. The pattern composes cleanly with another type.
- [ADR-137](./ADR-137-Markdown-Text-View.md) already pipes rendered
  markdown through marked → DOMPurify with the `iris://` scheme
  allowlist, so any computed output is sanitised the same as
  user-typed markdown.

What does not exist:

- A token syntax for embedding entity-field references in markdown.
- A resolver that walks markdown source and substitutes those
  references for live field values.
- A backend search endpoint for picker autocomplete spanning
  multiple entity types.
- A backend endpoint exposing the custom-attribute keys of a given
  element.
- A frontend canvas that intercepts `/` to open a contextual picker.

## Decision

Register a new diagram type `smart_markdown` ("Smart Markdown")
under the existing `markdown` notation. Users author plain markdown
with embedded reference tokens. The backend resolves tokens at read
time via the existing synth-on-read dispatch (ADR-187) and writes
the resolved markdown to `data.content`, which the existing
rendering pipeline (`MarkdownView.svelte`) and export pipeline
(`backend/app/export/renderers/markdown.py`, docx, pdf) consume.

### Token syntax (the contract)

```
{{<entity-type>:<id>:<field-spec>}}
```

| Slot | Values |
|---|---|
| `entity-type` | `element` \| `package` \| `diagram` \| `set` \| `collection` |
| `id` | the entity's GUID |
| `field-spec` | `name` \| `description` \| `attr:<attribute-key>` (elements only) |

Examples:

```
{{element:abc-123:name}}              → "Pork mince"
{{element:abc-123:description}}       → "Lean, free-range."
{{element:abc-123:attr:Unit}}          → "g"
{{package:def-456:name}}              → "Groceries"
```

Unresolvable tokens (entity not found, deleted, or attribute
missing) render as `~~{{...}}~~` so the user sees the token rather
than silently dropping it. Strikethrough is the established marker
for "something was here, ask why."

### Reference scope (locked v1)

- **Elements**: `name`, `description`, and any key in `element.data`
  via `attr:<key>`.
- **Packages, diagrams, sets, collections**: `name` and `description`
  only.

This matches the recipe example exactly (element custom attribute)
while keeping the resolver small. A future ADR can extend the
field-spec grammar (e.g., `package:abc:element_count`) without
breaking the token format.

### Picker UX (locked v1)

Two-step minimal:

1. **Entity step** — typeahead across all five entity types,
   prefix LIKE match, capped at 25 results.
2. **Field step** — fixed list for non-elements (name, description).
   For elements, fetch attribute keys and render them as
   `attr:<key>` rows alongside name + description.

No rich preview, no fuzzy ranking. This ships fast and the surface
is upgradable without breaking the inserted token format.

### Storage

`diagrams.data.markdown_source: string` — user-edited markdown
including tokens. Persisted on save.

`diagrams.data.content: string` — resolver output. Synthesised at
read time by `_maybe_synthesise_content` — never written by the
client. This matches the dynamic_list convention.

### Migration (paired §15)

- SQLite: `m070_smart_markdown_diagram_type.py` — `INSERT OR IGNORE`
  into `diagram_types` + `diagram_type_notations`. Display order
  17 (next after dynamic_list's 16).
- Supabase: `m074_smart_markdown_diagram_type.sql` — same with
  `ON CONFLICT DO NOTHING`. Header references the SQLite mirror.

### Backend resolver

`backend/app/diagrams/smart_markdown.py` —
`compute_smart_markdown_content(db, diagram_id) -> str`:

- Reads `diagrams.data.markdown_source`.
- Single regex pass over the source to enumerate tokens.
- Per-entity lookups against the appropriate `*_versions` tables
  (current_version only, `is_deleted = 0` for elements/diagrams/
  packages — sets and collections don't carry that flag).
- Element attribute lookup parses `element_versions.data` JSON.
- Substitution is positional; surrounding markdown is preserved
  byte-for-byte.

Dispatched from `_maybe_synthesise_content` in
`backend/app/diagrams/service.py`.

### Backend GET endpoints (no parity requirement)

`GET /api/search/entities?q=<prefix>&types=<csv>&limit=25` —
case-insensitive LIKE match across entity names. Returns
`[{id, entity_type, name}]`. Default `types` is all five.

`GET /api/elements/{id}/attribute-keys` — returns the sorted list
of keys in the element's current `data` JSON. Empty list if `data`
is null, missing, or not a dict.

Both are read-only → Protocol §14 surface parity does not require
MCP or CLI mirrors for GETs.

### Frontend

- `frontend/src/lib/canvas/text/SmartMarkdownCanvas.svelte` —
  textarea + toolbar in edit mode (reuses `MarkdownEditorToolbar`),
  `MarkdownView` in view mode reading from `data.content`. Keydown
  interceptor on the textarea opens the picker on `/` (when the
  preceding char is whitespace or line start, to avoid hijacking
  intra-word slashes).
- `frontend/src/lib/canvas/text/SmartMarkdownSlashPicker.svelte` —
  small popover, two-step. Reuses the existing `insertAtCursor`
  helper to splice the token at the caret.
- `frontend/src/lib/types/canvas.ts` — `'smart_markdown'` added
  to the diagram-type literal union.

### Security (Protocol §7)

Resolver output is plain markdown — fed through `markdownHelpers.ts`
(marked → DOMPurify with the iris:// scheme allowlist). If a
resolved field contains HTML or scripts (e.g. an element description
with raw `<script>` text), DOMPurify strips it before render. No
new `{@html}` usage.

## Why a new diagram type rather than extending `markdown` text

The existing `markdown` type is plain markdown. Adding token
resolution to *every* markdown view would silently change behaviour
for documents that happen to contain `{{...}}` literally (e.g.
Jinja-flavoured docs, code examples). A separate type makes the
opt-in explicit.

## Why server-side resolution rather than client-side

Three reasons:

1. **Export parity** — server-side resolution puts resolved markdown
   into `data.content`, which the existing docx/pdf renderers
   already consume. Client-side resolution would require duplicating
   the resolver in the export pipeline (Protocol §13 DRY violation).
2. **Single source of truth** — one resolver, one set of tests, one
   place to change the token grammar.
3. **Caching / batching** — server can batch entity lookups; client
   would round-trip per token.

## Why a single token format rather than markdown-link extension

Considered `[iris://element/abc?field=Unit]` as a link-flavoured
alternative. Rejected because:

- Markdown links carry display text; tokens carry *only* substitution.
  Conflating them would confuse the rendering pipeline.
- The token format is plain text with no markdown-special characters
  — safe to drop anywhere in the source.
- `{{...}}` is visually distinct in the textarea, so users can see
  references at a glance.

## Why `~~{{...}}~~` for unresolvable tokens

Strikethrough renders visibly in every markdown reader. The user
gets a fail-loud signal without the document breaking. Alternative
("silently drop", "log warning") were rejected: silent drop hides
data loss; warnings don't reach the document.

## Release ordering (Supabase)

Standing memory applies. m074 is a type-registration migration
(seed rows into the registry tables) — the code path that reads it
(`registry_service.list_diagram_types`) tolerates missing rows by
omitting the type from the picker. Safe to deploy before migrate;
the type just won't appear in the picker until the seed runs.

## Consequences

- `backend/app/migrations/m070_smart_markdown_diagram_type.py` — new SQLite.
- `backend/app/migrations/supabase/m074_smart_markdown_diagram_type.sql` — Supabase mirror.
- `backend/app/startup.py` — m070 registered.
- `backend/app/diagrams/smart_markdown.py` — new resolver module.
- `backend/app/diagrams/service.py` — dispatch in `_maybe_synthesise_content`.
- `backend/app/elements/router.py` — new `/elements/{id}/attribute-keys` endpoint.
- `backend/app/search/router.py` — new (or extended) `/search/entities` endpoint.
- `backend/tests/test_migrations/test_smart_markdown_schema.py` — registration test.
- `backend/tests/test_diagrams/test_smart_markdown.py` — resolver tests.
- `backend/tests/test_search/test_entity_search.py` — search endpoint tests.
- `backend/tests/test_elements/test_attribute_keys.py` — attribute-keys endpoint tests.
- `frontend/src/lib/canvas/text/SmartMarkdownCanvas.svelte` — new canvas.
- `frontend/src/lib/canvas/text/SmartMarkdownSlashPicker.svelte` — new picker.
- `frontend/src/lib/types/canvas.ts` — `'smart_markdown'` added.
- CHANGELOG `[6.14.0]`.

## Verification

```
.venv/bin/python -m pytest \
  backend/tests/test_migrations/test_smart_markdown_schema.py \
  backend/tests/test_diagrams/test_smart_markdown.py \
  backend/tests/test_search/test_entity_search.py \
  backend/tests/test_elements/test_attribute_keys.py
.venv/bin/python scripts/check_surface_parity.py
```

Manual smoke: create a Smart Markdown view in any set with elements,
type `500`, press `/`, search "pork", select element, pick
`attr:Unit`, then ` `, `/`, same element, `name`. Save. Verify
rendered output, then export to docx and pdf.

## See also

- Issue [#185](https://github.com/cgbarlow/iris/issues/185).
- Pattern source: [ADR-186](./ADR-186-Dynamic-List-Diagram-Type.md),
  [ADR-187](./ADR-187-Synthesised-Content-On-Read.md),
  [ADR-137](./ADR-137-Markdown-Text-View.md).
- §7 `{@html}` Protocol, §13 DRY, §15 Migration parity: `docs/protocols.md`.
