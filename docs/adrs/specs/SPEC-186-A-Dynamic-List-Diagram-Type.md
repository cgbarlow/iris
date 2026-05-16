# SPEC-186-A: Dynamic List diagram type

ADR: [ADR-186](../ADR-186-Dynamic-List-Diagram-Type.md)

## Summary

Implementation contract for the `dynamic_list` diagram type: registry
seed, source-config shape, bullet rendering rules, edit-mode UX,
acceptance criteria.

## Migration `m065_dynamic_list_diagram_type.py`

Mirror m044's pattern:

```python
_DIAGRAM_TYPE = ("dynamic_list", "Dynamic List",
                  "Auto-generated markdown bullet list", 16)
_MAPPINGS = [("dynamic_list", "markdown", 0)]
```

Idempotent: `INSERT OR IGNORE` for both the diagram_type row and the
mapping row. No `ai_creation_prompts` seed — dynamic_list content is
computed, not AI-generated.

Supabase mirror: `backend/app/migrations/supabase/m069_dynamic_list_diagram_type.sql`.

## `data.dynamic_source` schema

Three keys on the diagram's `data` JSON:

| Key | Type | Default | Notes |
|---|---|---|---|
| `mode` | `"diagram_relationships"` \| `"package_elements"` | `"diagram_relationships"` | Selects the source-of-truth for bullets. |
| `package_id` | `string` \| `null` | `null` | Used only in `package_elements` mode. References `packages.id`. |
| `show_description` | `bool` | `false` | If true, appends `(description)` to each bullet (both modes). |

Backwards-compat at compute time: any missing key uses the default. No
migration backfills the field.

## Compute module

`backend/app/diagrams/dynamic_list.py`:

```python
async def compute_dynamic_list_content(
    db: DatabasePort,
    diagram_id: str,
    *,
    mode: str,
    package_id: str | None,
    show_description: bool,
) -> str:
    """Return the synthesised markdown for a dynamic_list diagram."""
```

Dispatch:

- `mode == "diagram_relationships"` → call
  `list_intra_diagram_relationships(db, diagram_id)` (shared helper,
  see below) and emit two bullets per row.
- `mode == "package_elements"` and `package_id` is non-null → call
  `list_package_elements(db, package_id, page=1, page_size=10000)`
  and emit one bullet per element.
- `mode == "package_elements"` with `package_id is None` → emit only
  the header and footer (caller hasn't picked a package yet).
- Unknown mode → fall back to `diagram_relationships`.

### Bullet helpers

```python
def _bullet(name: str, description: str | None, show_description: bool) -> str:
    if show_description and description:
        return f"- **{name}** ({description})"
    return f"- **{name}"
```

(`**` for bold is consistent with prior text-diagram markdown; the
existing markdown renderer supports it. Trailing `**` is closed by
the renderer; verify in tests.)

Sort:

- `diagram_relationships`: tuple
  `(source.name, target.name, relationship_type)` ascending.
- `package_elements`: `name` ascending (case-insensitive).

### Header / footer

```python
header = f"# {diagram.name}\n\n"
footer = "\n###### (Dynamic list — auto-generated)\n"
```

If there are zero bullets, the body between header and footer is the
literal string `_No items yet._` (so the rendered markdown is never
empty). The footer always appears.

## Intra-diagram relationships helper

`backend/app/package_relationships/service.py` already has
`list_element_relationships_for_diagram` — but that helper uses
`source_element_id IN (...) OR target_element_id IN (...)`, which
includes outbound relationships to elements NOT on this diagram. The
dynamic_list default mode wants strictly **intra-diagram** rows
(both endpoints on this diagram).

Add a new sibling:

```python
async def list_intra_diagram_relationships(
    db: DatabasePort,
    diagram_id: str,
) -> list[dict[str, object]]:
    """Like list_element_relationships_for_diagram but with both
    endpoints constrained to elements drawn on this diagram. Used by
    ADR-186 dynamic_list (default mode) and by the existing
    Relationships tab's element_relationships array (extracted for
    DRY)."""
```

Implementation: identical to the existing helper but the SQL is
`source_element_id IN (...) AND target_element_id IN (...)`. The
existing handler in `app/diagrams/router.py::get_diagram_relationships`
is refactored to call this helper (DRY) — its observable behaviour is
unchanged because `element_relationships` was always meant to be the
intra-diagram view.

## Read-time synthesis (ADR-187)

`backend/app/diagrams/service.py::get_diagram` adds:

```python
if diagram["diagram_type"] == "dynamic_list":
    src = (diagram.get("data") or {}).get("dynamic_source") or {}
    rendered = await compute_dynamic_list_content(
        db, diagram_id,
        mode=src.get("mode") or "diagram_relationships",
        package_id=src.get("package_id"),
        show_description=bool(src.get("show_description", False)),
    )
    data = diagram.get("data") or {}
    if not isinstance(data, dict):
        data = {}
    data["content"] = rendered
    data["is_content_locked"] = True
    diagram["data"] = data
```

Apply the same logic in `list_diagrams` row-by-row (so the search
surface gets the rendered text too) and in the bundle reader used by
export (already passes through the service hook in current code, but
verify).

## Frontend

### `DiagramDialog.svelte`

Add `{ value: 'dynamic_list', label: 'Dynamic List' }` to the
`markdown` notation's fallback diagram-types array. Primary
registry-driven path picks it up automatically once m065 runs.

### `DynamicListCanvas.svelte`

```svelte
<script lang="ts">
  import MarkdownView from '$lib/components/MarkdownView.svelte';
  import PackagePicker from '$lib/components/PackagePicker.svelte';

  interface Props {
    content: string;
    editing: boolean;
    setId: string | null;
    source: { mode: string; package_id: string | null; show_description: boolean };
    onsourcechange: (next: typeof source) => void;
  }
  let { content, editing, setId, source, onsourcechange }: Props = $props();
</script>

<div class="dynamic-list-canvas">
  <MarkdownView markdown={content} />
  {#if editing}
    <details open>
      <summary>Source for this list</summary>
      <label>
        Mode
        <select
          value={source.mode}
          on:change={(e) => onsourcechange({ ...source, mode: (e.currentTarget as HTMLSelectElement).value })}
        >
          <option value="diagram_relationships">Default (diagram relationships)</option>
          <option value="package_elements">Package elements</option>
        </select>
      </label>
      {#if source.mode === 'package_elements'}
        <PackagePicker
          initialSetId={setId}
          onselect={(pkg) => onsourcechange({ ...source, package_id: pkg.id })}
        />
      {/if}
      <label>
        <input
          type="checkbox"
          checked={source.show_description}
          on:change={(e) => onsourcechange({ ...source, show_description: (e.currentTarget as HTMLInputElement).checked })}
        />
        Show description
      </label>
    </details>
  {/if}
</div>
```

### `/views/[id]/+page.svelte`

In the canvas-rendering branch, route on `data.is_content_locked`:

```svelte
{#if diagram.data?.is_content_locked}
    <DynamicListCanvas
        content={diagram.data.content}
        {editing}
        setId={diagram.set_id}
        source={diagram.data.dynamic_source ?? { mode: 'diagram_relationships', package_id: null, show_description: false }}
        onsourcechange={(next) => { pendingDynamicSource = next; }}
    />
{:else if diagram.notation === 'markdown'}
    <TextCanvas ... />
{/if}
```

Save handler for dynamic_list strips `content` and `is_content_locked`
from the PUT body (synthesised, never persisted) and includes
`dynamic_source`:

```typescript
const putData = {
    ...diagram.data,
    dynamic_source: pendingDynamicSource,
};
delete putData.content;
delete putData.is_content_locked;
await apiFetch(`/api/diagrams/${diagram.id}`, {
    method: 'PUT',
    headers: { 'If-Match': String(diagram.current_version) },
    body: JSON.stringify({ ...metadata, data: putData }),
});
```

## Tests

### `backend/tests/test_dynamic_list_compute.py`

Coverage matrix:

| Case | Mode | show_description | Setup | Assertion |
|---|---|---|---|---|
| C1 | diagram_relationships | off | 2 elements, 1 relationship (A→B) | Bullets: `- **A`, `- **B` in that order. |
| C2 | diagram_relationships | on | A (desc="foo"), B (desc=None), rel A→B | `- **A** (foo)`, `- **B` (no parens). |
| C3 | diagram_relationships | on | A (desc=""), B (desc="bar"), rel A→B | `- **A`, `- **B** (bar)`. |
| C4 | diagram_relationships | off | 2 relationships A→B and A→C | 4 bullets `- A, - B, - A, - C` (sorted by source/target/type). |
| C5 | package_elements | off | Package with 2 elements (alpha sort) | Bullets in alphabetical order. |
| C6 | package_elements | on | Package with elements (mixed descriptions) | `(description)` overlay applied. |
| C7 | package_elements | n/a | `package_id` is null | Body = `_No items yet._`. |
| C8 | empty | n/a | No relationships at all | Body = `_No items yet._` between header/footer. |

### `backend/tests/test_diagrams/test_dynamic_list_read.py`

- `GET /api/diagrams/{id}` on a `dynamic_list` diagram returns
  populated `data.content` and `data.is_content_locked = true`.
- Raw `diagrams.data` row in the DB does NOT contain those keys.
- Diagram with `data.dynamic_source = {}` reads as if defaults applied.

### `backend/tests/test_export/test_dynamic_list_export.py`

- `GET /api/export/diagram/{id}?format=md` returns the same string
  as the API read's `data.content`.

### Registry-count tests

Update `backend/tests/test_diagrams/test_registry.py::test_list_diagram_types`
and `test_new_diagram_types.py::test_total_diagram_type_count` from
expected 18 → 19 (the upstream count was 18 in the source comment but
the actual seed has been at 19 for a while — refresh the comment too).
Note: those tests are pre-existing-broken on `main` as of v6.6.5
because the count had already drifted to 19; this PR fixes the
assertion as a side-effect.

### Playwright `frontend/tests/e2e/dynamic-list-diagram.spec.ts`

- Create a dynamic_list diagram via the dialog.
- Seed two elements + one relationship via the API; reload.
- Assert the rendered list contains both element names (default
  mode, no descriptions).
- Click Edit; assert the Source panel has all three controls.
- Toggle Show description on; Save; reload; assert bullets show
  descriptions in parentheses.
- Switch mode to `package_elements`; pick a package; Save; assert
  bullets become the package's elements.

## Out of scope

- Pagination for huge lists. Accept long rendered markdown for v1.
- Deduplication of repeated element appearances. Explicit non-feature
  per user clarification.
- AI-generated content prompts. Dynamic list is purely computed —
  no `ai_creation_prompts` seed.

## Verification

- All pytest suites listed above pass.
- `python scripts/check_surface_parity.py` passes unchanged.
- Playwright spec passes against a live `./scripts/dev.sh start`.
- Manual smoke: create a dynamic_list, see bullets render in browse
  mode, edit Source panel, toggle show_description, confirm new
  bullets.
