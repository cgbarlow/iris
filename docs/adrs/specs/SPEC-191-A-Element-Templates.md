# SPEC-191-A: Element Templates

Implements [ADR-191](../ADR-191-Element-Templates.md).
Spec status: Living. Last revised 2026-05-17.

## 1. Data model

### 1.1 Table `element_templates`

| Column | Type (SQLite) | Type (Supabase) | Notes |
|---|---|---|---|
| `id` | TEXT PRIMARY KEY | TEXT PRIMARY KEY | UUID, supplied by service |
| `name` | TEXT NOT NULL | TEXT NOT NULL | 1..255 chars; sanitised in service via `escape()` |
| `description` | TEXT | TEXT | optional |
| `set_id` | TEXT REFERENCES sets(id) | TEXT REFERENCES public.sets(id) | nullable iff `is_global=1` |
| `is_global` | INTEGER NOT NULL DEFAULT 0 | BOOLEAN NOT NULL DEFAULT FALSE | Protocol §15: TRUE/FALSE on Postgres |
| `source_element_id` | TEXT REFERENCES elements(id) | TEXT REFERENCES public.elements(id) | nullable (element may be deleted) |
| `included_fields` | TEXT NOT NULL | TEXT NOT NULL | JSON array of whitelist keys |
| `template_data` | TEXT NOT NULL | TEXT NOT NULL | JSON snapshot of captured fields |
| `created_by` | TEXT REFERENCES users(id) | TEXT REFERENCES public.users(id) | |
| `created_at` | TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP | TIMESTAMPTZ NOT NULL DEFAULT now() | |
| `updated_at` | TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP | TIMESTAMPTZ NOT NULL DEFAULT now() | |
| `is_deleted` | INTEGER NOT NULL DEFAULT 0 | BOOLEAN NOT NULL DEFAULT FALSE | soft delete |

CHECK constraint (both halves):

```
(is_global = 1 AND set_id IS NULL) OR
(is_global = 0 AND set_id IS NOT NULL)
```

### 1.2 Indexes

- `idx_element_templates_set ON element_templates(set_id) WHERE is_deleted = 0`.
- `idx_element_templates_global ON element_templates(is_global) WHERE is_global = 1 AND is_deleted = 0`.

### 1.3 Field whitelist

```python
INCLUDED_FIELD_WHITELIST = frozenset({
    "name", "description", "element_type", "notation",
    "data", "metadata", "package_id", "tags",
})
```

Anything outside this set is silently dropped from
`included_fields` and never written into `template_data`.

## 2. REST endpoints

Prefix: `/api/element-templates`.

| Method | Path | Body / Query | Response | Auth |
|---|---|---|---|---|
| POST | `` | `ElementTemplateCreate` | 201 `ElementTemplateResponse` | get_current_user |
| GET | `` | `set_id?`, `include_global=true`, `page=1`, `page_size=50` | `ElementTemplateListResponse` | get_optional_user |
| GET | `/{template_id}` | — | `ElementTemplateResponse` | get_optional_user |
| PUT | `/{template_id}` | `ElementTemplateUpdate` | `ElementTemplateResponse` | get_current_user |
| DELETE | `/{template_id}` | — | 204 | get_current_user |

Update is partial: only keys present in the JSON body are touched. `set_id` may be null to demote a global template back to a set (the CHECK constraint validates the resulting state). 422 on scope violations; 404 on missing template.

### 2.1 Extension to `POST /api/elements`

`ElementCreate` gains optional `template_id`. Pre-merge flow:

```
fields = request.model_dump(exclude_unset=True)
template_id = fields.pop("template_id", None)
template_tags = []
if template_id:
    template = await get_element_template(db, template_id)
    if not template: raise 404
    fields = apply_template_to_create_body(template, fields)
    template_tags = fields.pop("tags", None) or []
# re-validate required (element_type + name), then create_element(...)
# write template_tags to element_tags table after creation
```

`apply_template_to_create_body` merges `template_data[k]` into `fields[k]` for every `k ∈ included_fields ∩ INCLUDED_FIELD_WHITELIST` where `fields.get(k)` is absent. Explicit request fields always win.

## 3. MCP tools

Five new tools mirror the REST surface plus `template_id` on `create_element`:

- `create_element_template(source_element_id, name, description?, included_fields, set_id?, is_global=false)`
- `list_element_templates(set_id?, include_global=true, page=1, page_size=50)`
- `get_element_template(template_id)`
- `update_element_template(template_id, name?, description?, included_fields?, set_id?, is_global?)`
- `delete_element_template(template_id)`
- `create_element` gains `template_id` (optional)

Tests in `mcp/tests/test_element_templates.py`.

## 4. CLI subcommands

CLI uses kebab-case entity names; the parity script normalises to underscores. New subcommands under the existing `create`/`update`/`delete`/`get`/`list` apps:

- `iris create element-template --from-element ID --name … --include name,description,data --global/--set-id`
- `iris list element-template [--set-id … | --global]`
- `iris get element-template ID`
- `iris update element-template ID --name … --include … --global`
- `iris delete element-template ID`
- `iris create element` gains `--template-id`

Tests in `cli/tests/test_element_templates.py`.

## 5. Frontend

### 5.1 Routes / components

| File | Purpose |
|---|---|
| `frontend/src/lib/components/TemplatesListDialog.svelte` | Browse + Use |
| `frontend/src/lib/components/CreateTemplateDialog.svelte` | Capture from current element |
| `frontend/src/routes/element-templates/[id]/+page.svelte` | Template detail |
| `frontend/src/routes/elements/+page.svelte` | (modified) Templates button + dialog mount |
| `frontend/src/routes/elements/[id]/+page.svelte` | (modified) Save-as-template button + dialog mount |

### 5.2 Use-from-template flow

1. User clicks **Templates** on `/elements` → dialog opens, fetches `GET /api/element-templates?set_id=…&include_global=true&page_size=100`.
2. User picks a template, clicks **Use** → inline mini-form asks for `name`.
3. Submit → `POST /api/elements` with `{ template_id, name, set_id }`. Backend pre-fills whitelisted fields server-side.
4. `goto(/elements/{newId})`.

### 5.3 Save-as-template flow

1. User opens `/elements/{id}`, clicks **Save as template** → dialog opens.
2. Form: name (default = `"{element.name} template"`), description (optional), 8 field checkboxes (defaults: name + description + element_type + notation + data + tags), "Make global" toggle (default off).
3. Submit → `POST /api/element-templates` with `source_element_id` = current element, `included_fields` = checked boxes, `set_id` or `is_global` depending on toggle.
4. `goto(/element-templates/{templateId})`.

### 5.4 Detail page

- Header: name, scope badge (Global or set name).
- Source element link (or "(source element deleted)" if `source_element_id` is null).
- Captured-fields table: each `included_fields` entry + pretty-printed JSON of `template_data[field]`.
- Action buttons: **Create element from template** (inline form), **Delete** (confirm dialog).

## 6. Security / sanitisation

- All user-supplied strings rendered into Svelte templates flow through `{expression}` (Svelte's default escaping). No `{@html}` is used — Protocol §7.
- DOMPurify sanitises `name` / `description` in the Create-element-from-template form before submission (belt-and-braces; backend also re-sanitises via `escape()`).
- `INCLUDED_FIELD_WHITELIST` is the trust boundary for which element fields can leave `elements` and enter `element_templates.template_data`.

## 7. Tests

| Suite | Path | Count |
|---|---|---|
| Backend schema | `backend/tests/test_migrations/test_element_templates_schema.py` | 7 |
| Backend CRUD + apply | `backend/tests/test_element_templates/test_crud_and_apply.py` | 27 |
| MCP | `mcp/tests/test_element_templates.py` | 12 |
| CLI | `cli/tests/test_element_templates.py` | 8 |
| Frontend | `frontend/tests/unit/elementTemplates.test.ts` | 20 |

Total: 74. (Earlier in development the count was lower; this is the final delta.)

## 8. Rollout

1. Merge feature branch.
2. Apply Supabase `m071_element_templates.sql` via `scripts/supabase-migrate.sh` (Protocol §15: migration before app deploy).
3. Render auto-deploys on push to main → tag `v6.8.0` → GitHub release.
4. Spot-check production: create a template, list templates, use a template, delete a template — once on the live frontend, once via MCP, once via CLI.
