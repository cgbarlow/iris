# SPEC-208-A: `element_tab_default` + element screen Relationships merge

Implements: [ADR-208](../ADR-208-Element-Tab-Default.md)
Status: Living

## Schema

### SQLite — `backend/app/migrations/m072_sets_element_tab_default.py`

```python
"""Adds element_tab_default per-set preference (ADR-208, v6.16.0)."""

from __future__ import annotations

MIGRATION_ID = "m072_sets_element_tab_default"


async def up(db) -> None:
    cursor = await db.execute("PRAGMA table_info(sets)")
    columns = {row[1] for row in await cursor.fetchall()}
    if "element_tab_default" not in columns:
        await db.execute(
            "ALTER TABLE sets ADD COLUMN element_tab_default TEXT "
            "NOT NULL DEFAULT 'relationships'",
        )
```

### Supabase — `backend/app/migrations/supabase/m077_sets_element_tab_default.sql`

```sql
-- Mirrors SQLite m072.
ALTER TABLE public.sets
    ADD COLUMN IF NOT EXISTS element_tab_default TEXT
    NOT NULL DEFAULT 'relationships';
```

### Startup wiring — `backend/app/startup.py`

```python
from app.migrations.m072_sets_element_tab_default import up as m072_up
# ...
await m072_up(main)  # issue #192, v6.16.0: element_tab_default (ADR-208)
```

## Pydantic — `backend/app/sets/models.py`

```python
ElementTabDefault = Literal["details", "diagrams", "relationships", "versions"]

class SetUpdate(BaseModel):
    # ... existing fields ...
    element_tab_default: ElementTabDefault | None = None

class SetResponse(BaseModel):
    # ... existing fields ...
    element_tab_default: ElementTabDefault = "relationships"
```

## Service — `backend/app/sets/service.py`

Extend `_SET_COLUMNS` to include `s.element_tab_default` (becomes the 18th
field at index 17). Update `_row_to_dict` mapping to read row[17] with a
defensive fallback to `"relationships"`. In `update_set`, add a per-field
block matching `package_tab_default`:

```python
if element_tab_default is not None:
    await db.execute(
        "UPDATE sets SET element_tab_default = ?, updated_at = ? WHERE id = ?",
        (element_tab_default, now, set_id),
    )
```

`create_set` returns the default `"relationships"` in its row dict.

## Endpoint — `GET /api/elements/{id}/package-memberships`

```python
@router.get("/{element_id}/package-memberships",
            response_model=list[PackageMembership])
async def get_package_memberships(
    element_id: str, request: Request,
    _user = Depends(get_optional_user),
) -> list[PackageMembership]:
    db = request.app.state.db_manager.main_db
    elem = await get_element(db, element_id)
    if elem is None:
        raise HTTPException(status_code=404, detail="Element not found")
    package_id = elem.get("package_id")
    if not package_id:
        return []
    cursor = await db.execute(
        "SELECT p.id, pv.name FROM packages p "
        "JOIN package_versions pv ON p.id = pv.package_id "
        "  AND p.current_version = pv.version "
        "WHERE p.id = ? AND p.is_deleted = 0",
        (package_id,),
    )
    row = await cursor.fetchone()
    if not row:
        return []
    return [PackageMembership(id=row[0], name=row[1] or "")]
```

`PackageMembership` is a tiny BaseModel: `{id: str, name: str}`.

## Element screen — `frontend/src/routes/elements/[id]/+page.svelte`

Tab order: `relationships`, `details`, `versions`. The `diagrams` tab is
removed; its content moves under the Relationships tab.

```svelte
{#if activeTab === 'relationships'}
    <section class="el-rel-block">
        {#if packageMemberships.length > 0}
            <h3>Package membership</h3>
            <ul>
                {#each packageMemberships as m (m.id)}
                    <li><a href="/packages/{m.id}">{m.name}</a></li>
                {/each}
            </ul>
        {/if}
        {#if usedInModels.length > 0}
            <h3>Used in Views</h3>
            {/* existing usedInModels table */}
        {/if}
        {#if relationships.length > 0}
            <h3>Relationships</h3>
            {/* existing relationships table */}
        {/if}
    </section>
{:else if activeTab === 'details'}
    {/* existing details */}
{:else if activeTab === 'versions'}
    {/* existing version history */}
{/if}
```

`activeTab` seeding mirrors `frontend/src/routes/views/[id]/+page.svelte:60-90`:

```ts
if (!userSelectedTab) {
    if (entity.set_id) {
        try {
            const setData = await apiFetch<{element_tab_default?: ElementTabDefault}>(
                `/api/sets/${entity.set_id}`,
            );
            const preferred = setData.element_tab_default;
            if (preferred === 'relationships' || preferred === 'details' || preferred === 'versions') {
                activeTab = preferred;
            } else {
                activeTab = 'relationships';
            }
        } catch {
            activeTab = 'relationships';
        }
    } else {
        activeTab = 'relationships';
    }
}
```

(The `diagrams` value is accepted by the Pydantic model for forward
compat with previously-saved data; if encountered, the frontend coerces
to `relationships` so the user doesn't land on a missing tab.)

## Set edit screen — `frontend/src/routes/sets/[id]/+page.svelte`

Add state and binding:

```ts
let elementTabDefault = $state<ElementTabDefault>('relationships');

// in load:
elementTabDefault = setData.element_tab_default ?? 'relationships';

// in PUT body:
element_tab_default: elementTabDefault,
```

UI dropdown rendered below the existing `viewTabDefault` dropdown:

```svelte
<label>Element tab default
    <select bind:value={elementTabDefault}>
        <option value="relationships">Relationships</option>
        <option value="details">Details</option>
        <option value="versions">Version History</option>
    </select>
</label>
```

## Tests

- `backend/tests/test_migrations/test_element_tab_default_schema.py` — column exists, default value, idempotent re-run, paired Supabase mirror present.
- `backend/tests/test_sets/test_element_tab_default.py` (or extend existing) — SetUpdate accepts the field, SetResponse returns it, create_set defaults to `relationships`, update persists.
- `backend/tests/test_elements/test_package_memberships.py` — element with no package → empty list; element in a package → returns that package; missing element → 404.

## Verification

1. Run `./scripts/dev.sh restart`.
2. Open `/elements/{any-id}` → tab order is Relationships, Details, Version History.
3. Inside Relationships: package membership (if any), Used in Views (if any), Relationships table (if any). Each section hidden when empty.
4. Set edit screen → new "Element tab default" dropdown.
5. Save with "Details" → reopen the same element → activeTab is `details`.
6. `curl localhost:8000/api/elements/{id}/package-memberships` returns `[]` or `[{id, name}]`.
7. Backend tests green.
8. Manual: `scripts/supabase-migrate.sh` applies m077 cleanly.
