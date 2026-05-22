# SPEC-211-a: Element template markdown stamps

Implements: [ADR-211](../ADR-211-Element-Template-Stamps.md)

## 1. Schema change

### SQLite (`backend/app/migrations/m074_element_template_markdown_stamp.py`)

```sql
ALTER TABLE element_templates ADD COLUMN markdown_stamp TEXT;
```

### Supabase (`backend/app/migrations/supabase/m079_element_template_markdown_stamp.sql`)

```sql
-- Mirrors SQLite m074.
ALTER TABLE element_templates ADD COLUMN IF NOT EXISTS markdown_stamp TEXT;
```

Schema test: `backend/tests/test_migrations/test_element_template_markdown_stamp_schema.py` asserts the column exists, idempotency holds, and no boolean-literal regression slips in.

## 2. Model changes

```python
class ElementTemplateCreate(BaseModel):
    source_element_id: str | None = None        # was required, now optional
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    included_fields: list[str] = Field(default_factory=list)  # was min_length=1
    template_data: dict[str, object] | None = None            # NEW
    markdown_stamp: str | None = None                          # NEW
    set_id: str | None = None
    is_global: bool = False

class ElementTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    included_fields: list[str] | None = None
    template_data: dict[str, object] | None = None             # NEW (write-through)
    markdown_stamp: str | None = None                          # NEW
    set_id: str | None = None
    is_global: bool | None = None

class ElementTemplateResponse(BaseModel):
    ...                                                        # existing fields
    markdown_stamp: str | None = None                          # NEW
```

A template's purpose is non-trivial if any of:
- `source_element_id` is provided (snapshot from element),
- `template_data` is provided non-empty,
- `markdown_stamp` is provided non-empty.

If none of the three is set, `create_element_template` raises `ElementTemplateScopeError` ("template has no content").

## 3. Service changes (`backend/app/element_templates/service.py`)

### `create_element_template`

```python
async def create_element_template(
    db, *, source_element_id, name, description, included_fields,
    set_id, is_global, created_by,
    template_data_direct=None, markdown_stamp=None,
):
    _validate_scope(...)
    has_anything = False

    # Path A: snapshot from source element
    if source_element_id:
        src = await _load_source_element(db, source_element_id)
        filtered = _filter_included_fields(included_fields or [])
        template_data = _project_template_data(src, filtered) if filtered else {}
        has_anything = bool(template_data)
    # Path B: direct template_data
    elif template_data_direct is not None:
        template_data = template_data_direct
        filtered = []
        has_anything = bool(template_data)
    else:
        template_data = {}
        filtered = []

    if markdown_stamp:
        has_anything = True

    if not has_anything:
        raise ElementTemplateScopeError(
            "Template must have at least one of: source_element_id, "
            "template_data, or markdown_stamp"
        )

    # INSERT including the new markdown_stamp column.
    ...
```

### `get_element_template` / `list_element_templates`

Selects extended to include `markdown_stamp` (column index 14, after `updated_at`). Response dict carries `markdown_stamp` key.

### `update_element_template`

Accepts optional `markdown_stamp` and `template_data_direct` parameters. Update SQL extended to include both columns.

### `substitute_self(stamp_body: str, element_id: str) -> str`

```python
_SELF_TOKEN_RE = re.compile(r"\{\{self:([^}]+)\}\}")

def substitute_self(stamp_body: str, element_id: str) -> str:
    """Rewrite `{{self:<field-spec>}}` to `{{element:<element-id>:<field-spec>}}`."""
    return _SELF_TOKEN_RE.sub(
        lambda m: f"{{{{element:{element_id}:{m.group(1)}}}}}",
        stamp_body,
    )
```

### `list_stamps_for_element(db, element_id) -> list[dict]`

```python
async def list_stamps_for_element(db, element_id):
    """Return in-scope stamps for an element (ADR-211 scope rules)."""
    # 1. Load element's set_id and element_type.
    cursor = await db.execute(
        "SELECT e.set_id, e.element_type FROM elements e "
        "WHERE e.id = ? AND e.is_deleted = 0",
        (element_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        return []
    set_id, element_type = row[0], row[1]

    # 2. Select templates with non-empty markdown_stamp, in scope.
    cursor = await db.execute(
        "SELECT id, name, description, set_id, is_global, "
        "template_data, markdown_stamp "
        "FROM element_templates "
        "WHERE is_deleted = 0 "
        "AND markdown_stamp IS NOT NULL AND markdown_stamp != '' "
        "AND (is_global = 1 OR set_id = ?) "
        "ORDER BY is_global DESC, name ASC",
        (set_id,),
    )
    rows = await cursor.fetchall()

    # 3. Element-type filter: if template's template_data.element_type is
    #    set, must match element's element_type. Else any element_type.
    out = []
    for r in rows:
        td = json.loads(r[5]) if r[5] else {}
        td_etype = td.get("element_type")
        if td_etype and td_etype != element_type:
            continue
        # Substitute self with element_id at fetch time so the caller
        # gets a ready-to-insert body.
        stamp_resolved = substitute_self(r[6], element_id)
        out.append({
            "id": r[0],
            "name": r[1],
            "description": r[2],
            "set_id": r[3],
            "is_global": bool(r[4]),
            "markdown_stamp": stamp_resolved,
        })
    return out
```

## 4. Router / endpoint changes

### Existing endpoints (POST/PATCH on `/api/element-templates/{id}`)

Accept and persist `markdown_stamp` and `template_data` (direct) per the model changes.

### New read endpoint

```
GET /api/element-templates/stamps?element_id=<element-id>
```

Response:

```json
{
  "items": [
    {
      "id": "<template-id>",
      "name": "Quantified item",
      "description": "...",
      "set_id": null,
      "is_global": true,
      "markdown_stamp": "{{element:<element-id>:attr:attributes/Quantity/type=}} {{element:<element-id>:attr:attributes/Unit/type}} {{element:<element-id>:name}}"
    }
  ]
}
```

Auth: same as existing template list — authenticated read.

## 5. Seed migration

### SQLite (`backend/app/migrations/m075_seed_global_element_template_stamps.py`)

Inserts five rows with deterministic IDs (UUIDv5 over the template name + a stable namespace). `is_global = 1`, `set_id = NULL`, `source_element_id = NULL`, `included_fields = "[]"`, `template_data = <blueprint>`, `markdown_stamp = <stamp>`. Idempotent via `INSERT OR IGNORE`.

### Supabase (`backend/app/migrations/supabase/m080_seed_global_element_template_stamps.sql`)

Same rows. `is_global = TRUE`, booleans literal. `ON CONFLICT (id) DO NOTHING`.

### Seed contents

```python
SEEDED_TEMPLATES = [
    {
        "name": "Quantified item",
        "description": "Element with a numeric quantity + unit (groceries, parts, stock items, …)",
        "element_type": "class",
        "attributes": ["Quantity", "Unit"],
        "markdown_stamp": (
            "{{self:attr:attributes/Quantity/type=}} "
            "{{self:attr:attributes/Unit/type}} "
            "{{self:name}}"
        ),
    },
    {
        "name": "Sized story",
        "description": "Work item with story points",
        "element_type": "class",
        "attributes": ["Points"],
        "markdown_stamp": (
            "{{self:attr:attributes/Points/type=}} pts — {{self:name}}"
        ),
    },
    {
        "name": "Logged work",
        "description": "Work-log entry with hours",
        "element_type": "class",
        "attributes": ["Hours"],
        "markdown_stamp": (
            "{{self:attr:attributes/Hours/type=}}h — {{self:name}}"
        ),
    },
    {
        "name": "Line item",
        "description": "Expense / billing line item",
        "element_type": "class",
        "attributes": ["Amount", "Currency"],
        "markdown_stamp": (
            "{{self:attr:attributes/Currency/type}}"
            "{{self:attr:attributes/Amount/type=}} — {{self:name}}"
        ),
    },
    {
        "name": "Read entry",
        "description": "Reading-log entry",
        "element_type": "class",
        "attributes": ["Pages", "Author"],
        "markdown_stamp": (
            "{{self:attr:attributes/Pages/type=}} pages — "
            "\"{{self:name}}\" by {{self:attr:attributes/Author/type}}"
        ),
    },
]
```

The blueprint `template_data` per row is:

```python
{
    "element_type": "class",
    "notation": "simple",
    "data": {
        "attributes": [
            {
                "name": attr_name,
                "type": "",
                "scope": "Public",
                "notes": "",
                "lower_bound": "",
                "upper_bound": "",
            }
            for attr_name in attributes
        ]
    },
}
```

## 6. Surface parity

Every write endpoint must carry through to MCP and CLI per protocol §14.

- `POST /api/element-templates` and `PATCH /api/element-templates/{id}` already exist; both gain `markdown_stamp` and `template_data` optional params in pydantic models. Existing parity entries still apply — no new tools needed.
- `GET /api/element-templates/stamps` is **read-only** — does not require parity per the §14 read/write split. MCP tool `list_element_template_stamps` is still provided as a convenience for agent discovery.
- MCP tool `create_element_template` input schema extended to accept `markdown_stamp` (string, optional) and `template_data` (object, optional).
- MCP tool `update_element_template` likewise.
- CLI `iris create element-template` adds `--markdown-stamp <text>` and `--template-data-file <path>` flags.
- CLI `iris update element-template` likewise.

## 7. Tests

`backend/tests/test_element_templates/test_stamps.py` covers:

- Create template with `markdown_stamp` set, no source element → 201.
- Create with all three optional fields empty → 422.
- Update `markdown_stamp` field on existing template → returned in subsequent GET.
- `substitute_self("foo {{self:name}} bar", "abc")` → `"foo {{element:abc:name}} bar"`.
- `substitute_self` with multiple `{{self:…}}` tokens — all replaced.
- `substitute_self` with no self tokens — returns input unchanged.
- `GET /api/element-templates/stamps?element_id=X` returns in-scope stamps with `self` substituted to `X`.
- Stamp filter by `element_type`: template with `template_data.element_type = "class"` does NOT appear for an element of `element_type = "interface"`.
- Stamp filter by scope: set-scoped stamp does NOT appear for an element in a different set.
- Global stamp appears for elements in any set.
- Deleted element → `GET /stamps` returns `[]`.

`backend/tests/test_migrations/test_element_template_markdown_stamp_schema.py` covers the schema migration.

`backend/tests/test_migrations/test_seed_global_element_templates_schema.py` asserts all five seeded rows after migration.

## 8. Out of scope (deferred to v6.19.1)

- Frontend stamp editor in self-mode (smart-markdown editor with picker locked to `{{self:…}}`).
- Picker UI showing the "Stamps" section above fields. The endpoint + helpers ship; the picker integration is a follow-up — for v6.19.0 stamps are usable via REST/MCP/CLI by agents (Claude Desktop etc.), which is the primary `/goal` consumer.
- Per-element override of a template's stamp.
