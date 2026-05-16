# SPEC-184-A: Element → package optional membership

ADR: [ADR-184](../ADR-184-Element-Package-Membership.md)

## Summary

Schema, API, CLI, MCP, and GUI surface for first-class element → package
membership. One package per element. Additive nullable column on
`elements`; service-layer invariant against `set_id`; full surface
parity; new section in the `/view` Relationships tab.

## Migration `m064_element_package_membership.py`

```sql
ALTER TABLE elements ADD COLUMN package_id TEXT REFERENCES packages(id);
CREATE INDEX IF NOT EXISTS idx_elements_package ON elements(package_id);
```

- Idempotent: `CREATE INDEX IF NOT EXISTS` and a guard checking
  `PRAGMA table_info(elements)` before issuing `ALTER TABLE`.
- No back-fill. Every existing element keeps `package_id = NULL`.

## Models (`backend/app/elements/models.py`)

```python
class ElementCreate(BaseModel):
    element_type: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    data: dict[str, object] = Field(default_factory=dict)
    set_id: str | None = None
    package_id: str | None = None           # NEW
    metadata: dict[str, object] | None = None
    notation: str = "simple"


class ElementUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    data: dict[str, object] = Field(default_factory=dict)
    change_summary: str | None = None
    metadata: dict[str, object] | None = None
    package_id: str | None | UnsetType = Unset  # NEW: tri-state
```

`package_id` on `ElementUpdate` uses a three-state representation:
**unset** (do not touch), **explicit None** (clear membership),
**explicit string** (set to value). Implementation uses a sentinel
class because Pydantic models otherwise can't distinguish "omitted"
from "explicitly null". The router translates to a kwarg-style call
into the service.

`ElementResponse` gains:

```python
    package_id: str | None = None
    package_name: str | None = None
```

## Service layer (`backend/app/elements/service.py`)

### Invariant helper

```python
async def _validate_element_package_set_consistency(
    db: DatabasePort, *, set_id: str | None, package_id: str | None,
) -> None:
    """Raise InvariantError if (set_id, package_id) are inconsistent."""
    if package_id is None or set_id is None:
        return
    cursor = await db.execute("SELECT set_id FROM packages WHERE id = ?", (package_id,))
    row = await cursor.fetchone()
    if row is None:
        raise InvariantError(f"Package {package_id} not found")
    pkg_set_id = row[0]
    if pkg_set_id is not None and pkg_set_id != set_id:
        raise InvariantError(
            f"Element belongs to set {set_id} but package {package_id} "
            f"belongs to set {pkg_set_id}",
        )
```

`InvariantError` is a new exception type translated by the router into
HTTP 422.

### `create_element` — extend signature with `package_id`

- Call `_validate_element_package_set_consistency(db, set_id, package_id)`
  before insert.
- Add `package_id` to the `INSERT INTO elements (...)` column list.
- Include `package_id` in the returned dict.

### `update_element` — extend signature with `package_id` + sentinel

- If `package_id` is `Unset`, do not touch the column.
- If `package_id` is explicit:
  - Look up the element's current `set_id`.
  - **Cross-set move clearing**: if the caller is also changing
    `set_id` in the same update (future extension — not in scope for
    v6.7.0), drop the package_id silently. For v6.7.0 the row's
    `set_id` is not editable via `ElementUpdate`, so this branch
    reduces to: validate the new `package_id` against the element's
    existing `set_id`. If validation fails, raise `InvariantError`.
- Run validation, then `UPDATE elements SET package_id = ? WHERE id = ?`
  inside the same transaction as the version bump.

### `get_element` / `list_elements` — add `package_id` + `package_name` join

```python
"LEFT JOIN packages p ON e.package_id = p.id"
```

Add `e.package_id` and `p.name AS package_name` to the SELECT column
list (positional indexing per ADR-183). Update the returned dict.

### `list_elements` — adopt nullable-filter helper

```python
from app.common.nullable_filter import parse_nullable_id

pkg_filter = parse_nullable_id(package_id)
match pkg_filter:
    case ("none",):
        pass
    case ("is_null",):
        where_clauses.append("e.package_id IS NULL")
    case ("eq", pkg_id):
        where_clauses.append("e.package_id = ?")
        params.append(pkg_id)
```

### `list_package_elements`

```python
async def list_package_elements(
    db: DatabasePort, package_id: str, *, page: int = 1, page_size: int = 50,
) -> tuple[list[dict[str, object]], int]:
```

Same shape as the existing `list_diagrams_by_package(db, package_id, ...)`
in `app/packages/service.py` (mirror its SQL exactly, swapping
`d.parent_package_id` for `e.package_id`).

## Router

### `backend/app/elements/router.py`

- `create` handler wires `body.package_id` into `create_element`.
- `update` handler converts `body.package_id` (which may be `Unset`)
  into a kwarg passed to `update_element`.
- `list_all` handler accepts `package_id: str | None = None` query
  param and passes it through.

### `backend/app/packages/router.py`

```python
@router.get("/{package_id}/elements", response_model=ElementListResponse)
async def list_package_elements_route(
    package_id: str,
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    _current_user: dict[str, Any] | None = Depends(get_optional_user),
) -> ElementListResponse:
    db = request.app.state.db_manager.main_db
    items, total = await list_package_elements(
        db, package_id, page=page, page_size=page_size,
    )
    return ElementListResponse(
        items=[ElementResponse(**item) for item in items],
        total=total, page=page, page_size=page_size,
    )
```

### `backend/app/diagrams/router.py` (or service.py)

The existing `GET /api/diagrams/{id}/relationships` handler returns
`{diagram_relationships, element_relationships}`. Extend to:

```python
{
    "diagram_relationships": [...],
    "element_relationships": [...],
    "element_package_memberships": [
        {
            "element_id": ...,
            "element_name": ...,
            "package_id": ...,
            "package_name": ...,
        },
        ...
    ],
}
```

Population: SELECT against the diagram's current canvas data to find
the set of `element_id`s drawn on the diagram, then SELECT those
elements' `package_id` + `package_name` where `package_id IS NOT NULL`.

## CLI (`cli/src/iris_cli/main.py`)

### `elements update --package-id`

```python
@update_app.command("element")
def update_element_cmd(
    element_id: str = typer.Argument(...),
    name: str | None = typer.Option(None, "--name"),
    description: str | None = typer.Option(None, "--description"),
    package_id: str | None = typer.Option(None, "--package-id"),
    ...
):
```

`--package-id null` (literal string) → clears via explicit None.
`--package-id <uuid>` → sets.
`--package-id` omitted → leaves untouched.

### `elements list --package-id`

```python
@elements_app.command("list")
def elements_list(
    set_id: str | None = typer.Option(None, "--set-id"),
    package_id: str | None = typer.Option(None, "--package-id"),
    ...
):
```

Passed through to `GET /api/elements?package_id=...`. CLI accepts the
same `"null"` literal for the IS-NULL branch.

### `packages list-elements`

```python
@packages_app.command("list-elements")
def packages_list_elements_cmd(
    package_id: str = typer.Argument(...),
    ...
):
```

Wraps `GET /api/packages/{id}/elements`.

## MCP (`mcp/src/iris_mcp/tools.py`)

### `update_element` — extend allow-list

```python
for key in ("name", "description", "data", "metadata", "package_id"):
    if key in args:
        body[key] = args[key]
```

`package_id` accepts string or `null`.

### `list_elements` — extend arg schema

```python
Tool(
    name="list_elements",
    ...
    inputSchema={
        "properties": {
            "set_id": ...,
            "package_id": _str_arg(
                "package_id",
                'Scope to a package. Pass "null" to list elements without a package.',
                required=False,
            ),
            ...
        },
    },
),
```

### `list_package_elements` — new tool

```python
Tool(
    name="list_package_elements",
    description="List elements belonging to a package.",
    inputSchema={
        "type": "object",
        "properties": {
            "package_id": _str_arg("package_id", "Package id", required=True),
            "limit": _int_arg("limit", "Page size", required=False),
            "page": _int_arg("page", "Page number (1-based)", required=False),
        },
        "required": ["package_id"],
    },
    handler=_list_package_elements,
),
```

Handler signature:

```python
async def _list_package_elements(c: IrisClient, args: dict[str, Any]) -> str:
    resp = await c._request(
        "GET",
        f"/api/packages/{args['package_id']}/elements",
        params={
            "page": int(args.get("page", 1)),
            "page_size": int(args.get("limit", 50)),
        },
    )
    return with_web_urls_list(json.dumps(resp.json()["items"]), "element")
```

## Frontend

### `frontend/src/lib/components/ElementForm.svelte` (or pinned equivalent)

Add a PackagePicker control under the Set picker. Confirm the actual
form filename at implementation time (recon flagged this as unpinned).
Hook: when an `initialSetId` is present, pass it to `<PackagePicker
initialSetId={setId} />` so the picker scopes to that set's packages.

### `frontend/src/routes/views/[id]/+page.svelte`

Extend the existing `loadDiagramRelationships(id)` (line 789) to read
the new `element_package_memberships` array:

```typescript
interface ElementPackageMembership {
    element_id: string;
    element_name: string;
    package_id: string;
    package_name: string;
}

const result = await apiFetch<{
    diagram_relationships: DiagramRelationship[];
    element_relationships: ElementRelationship[];
    element_package_memberships: ElementPackageMembership[];
}>(`/api/diagrams/${id}/relationships`);
elementPackageMemberships = result.element_package_memberships ?? [];
```

Tolerate missing key for backwards-compat with older API responses
(`?? []`).

Update `hasRelationships` derivation to include the new array.

In the tab body (`{:else if activeTab === 'relationships'}` block), add
a third section after the existing two:

```svelte
{#if elementPackageMemberships.length > 0}
    <h3 class="mb-2 mt-4 text-sm font-semibold">
        Element → Package memberships ({elementPackageMemberships.length})
    </h3>
    <ul>
        {#each elementPackageMemberships as m}
            <li>
                <strong>{m.element_name}</strong>
                →
                <a href="/packages/{m.package_id}">{m.package_name}</a>
            </li>
        {/each}
    </ul>
{/if}
```

Pill counter at line 2135 updates to sum all three categories.

## Tests

### `backend/tests/test_element_package_membership.py`

- `test_migration_adds_package_id_column` — `PRAGMA table_info(elements)`
  contains `package_id` after migrations run.
- `test_create_element_with_package_id_succeeds_when_consistent` —
  set_id + package_id where package belongs to the same set.
- `test_create_element_with_package_id_fails_when_inconsistent` —
  package belongs to a different set → 422.
- `test_create_element_with_package_id_succeeds_when_package_setless` —
  package has `set_id=NULL` and element has a set_id → allowed.
- `test_update_element_clear_package_id` — set to None clears.
- `test_update_element_set_package_id` — sets value.
- `test_update_element_omits_package_id_leaves_untouched` — sentinel
  semantics.
- `test_list_elements_filter_package_id_eq` — `?package_id=<uuid>`.
- `test_list_elements_filter_package_id_null` — `?package_id=null`.
- `test_list_elements_filter_package_id_omitted` — no filter.
- `test_list_package_elements_paginates` —
  `GET /api/packages/{id}/elements`.
- `test_get_diagram_relationships_includes_memberships` —
  augmented response contains `element_package_memberships` for
  elements drawn on the diagram.

### `backend/tests/test_nullable_filter.py` (per ADR-185)

- `test_parse_none` → `("none",)`.
- `test_parse_null_literal` → `("is_null",)`.
- `test_parse_uuid_literal` → `("eq", uuid)`.
- `test_parse_does_not_match_uppercase_NULL` → `("eq", "NULL")`.
- `test_parse_does_not_match_empty_string` → `("eq", "")` (caller's
  problem to validate further).

### `cli/tests/test_elements_package.py`

- `test_cli_update_element_with_package_id` — round-trip.
- `test_cli_update_element_clear_package_id_with_null` —
  `--package-id null`.
- `test_cli_elements_list_filter_package_id` — both `<uuid>` and
  `null` work.
- `test_cli_packages_list_elements` — round-trip.

### `mcp/tests/test_update_element_package.py`

- `test_mcp_update_element_sets_package_id` — tool call passes
  through.
- `test_mcp_update_element_clears_package_id_with_null` — JSON null
  is accepted.
- `test_mcp_list_package_elements` — new tool returns expected rows.

### `frontend/tests/e2e/element-package-membership.spec.ts`

- Create an element with a package via the form, reload, assert
  package shown.
- Open the `/view` of a diagram containing the element; click
  Relationships tab; assert the third section renders the element →
  package row with a clickable link to `/packages/{id}`.

## Out of scope

- `move_element` between diagrams remains forbidden (ADR-178).
- Many-to-many element → package memberships.
- Element-level membership change history (we do not track who set the
  package or when as a separate audit log — the element's regular
  version history captures the update).
- KnowledgeGraph rendering of element → package edges. Future ADR if
  requested.

## Verification

- All pytest suites listed above pass.
- `python scripts/check_surface_parity.py` passes.
- Playwright e2e green.
- Manual smoke against dev: `./scripts/dev.sh start`, create a set + a
  package + an element with the new column set, confirm the
  Relationships tab and `/api/packages/{id}/elements` work.
