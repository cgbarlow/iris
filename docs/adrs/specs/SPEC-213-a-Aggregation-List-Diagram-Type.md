# SPEC-213-a: `aggregation_list` diagram type

Implements: [ADR-213](../ADR-213-Aggregation-List-Diagram-Type.md)

## 1. Diagram-type registration

### SQLite (`backend/app/migrations/m078_aggregation_list_diagram_type.py`)

```sql
INSERT OR IGNORE INTO diagram_types
    (id, name, description, notation, display_order, is_active)
VALUES
    ('aggregation_list', 'Aggregation list',
     'Synth-on-read aggregation of a source smart-markdown diagram',
     'markdown', 99, 1);
```

### Supabase (`backend/app/migrations/supabase/m083_aggregation_list_diagram_type.sql`)

```sql
-- Mirrors SQLite m078.
INSERT INTO public.diagram_types
    (id, name, description, notation, display_order, is_active)
VALUES
    ('aggregation_list', 'Aggregation list',
     'Synth-on-read aggregation of a source smart-markdown diagram',
     'markdown', 99, TRUE)
ON CONFLICT (id) DO NOTHING;
```

## 2. Synth-on-read dispatch

Extend `backend/app/diagrams/service.py::_maybe_synthesise_content` with a new branch:

```python
if diagram_type == "aggregation_list":
    from app.aggregation import engine as agg_engine
    from app.aggregation.exceptions import (
        AggregationProfileNotFound,
        AggregationSourceNotFound,
    )
    data = diagram.get("data") or {}
    if not isinstance(data, dict):
        data = {}
    src = data.get("source_diagram_id")
    profile = data.get("profile_id")
    if src and profile:
        try:
            result = await agg_engine.run(
                db, profile_id=profile, source_diagram_id=src,
            )
            data["content"] = result.markdown
        except AggregationProfileNotFound:
            data["content"] = "_Aggregation profile not found._"
        except AggregationSourceNotFound:
            data["content"] = "_Source diagram not found._"
        except Exception as exc:  # noqa: BLE001
            data["content"] = f"_Aggregation failed: {exc}_"
    else:
        data["content"] = "_Pick a source diagram and aggregation profile to compute._"
    data["is_content_locked"] = True
    diagram["data"] = data
    return
```

The dispatch is intentionally permissive — any exception in the engine renders an informative placeholder in the content rather than crashing the GET. This keeps the diagram visible/editable even when the configured source or profile becomes invalid.

## 3. Frontend canvas

A new `AggregationListCanvas.svelte` (under `frontend/src/lib/canvas/text/`) — small wrapper around `MarkdownView` for the read path and a source/profile picker form for the edit path:

```svelte
<script lang="ts">
  import MarkdownView from '$lib/components/MarkdownView.svelte';
  // edit-mode source + profile pickers omitted for brevity (see PR).
  let { content, editing, source = $bindable(), profile = $bindable(),
        onsourcechange, onprofilechange } = $props();
</script>

{#if editing}
  <form class="agg-list-config">
    <label>Source diagram <input bind:value={source}/></label>
    <label>Profile <input bind:value={profile}/></label>
  </form>
{:else}
  <MarkdownView source={content ?? ''} />
{/if}
```

The v6.21.0 picker is minimal — text inputs for the two UUIDs. A richer picker (browse + autocomplete) is a follow-up; the data model is the source of truth and any picker shape can be layered later.

`frontend/src/routes/views/[id]/+page.svelte` dispatches on `diagram_type === 'aggregation_list'` to this canvas (same shape as the existing dispatch for `smart_markdown` / `dynamic_list`).

## 4. Create dialog

`DiagramDialog.svelte` already supports per-diagram-type create flows. The aggregation_list option appears in the new-diagram menu under the `markdown` notation. The dialog asks for:

- Name (existing)
- Source diagram id (UUID)
- Aggregation profile id (UUID)

On submit, `POST /api/diagrams` with `diagram_type: "aggregation_list"`, `notation: "markdown"`, and `data: {source_diagram_id, profile_id}`.

## 5. Tests

`backend/tests/test_diagrams/test_aggregation_list.py`:

- Create an `aggregation_list` diagram with a valid source + profile → GET returns `data.content` with the aggregated markdown.
- Missing source → returns a "Source diagram not found" placeholder, not a 5xx.
- Missing profile → returns a "Aggregation profile not found" placeholder.
- Empty `data.source_diagram_id` → "Pick a source..." placeholder.
- The diagram type appears in the `diagram_types` registry after migration.

`backend/tests/test_migrations/test_aggregation_list_diagram_type_schema.py`:

- The migration is idempotent.
- The seeded `diagram_types` row is present with correct notation + name.

## 6. Out of scope (v6.21.x follow-ups)

- Form-based profile editor (current edit mode = raw JSON via REST/CLI).
- Picker-style source/profile selectors in the diagram editor (current = UUID text inputs).
- Per-diagram cache for the aggregation result.
- Real-time / push refresh when the source diagram changes.
