# SPEC-094-A: DoView Notation

**ADR:** [ADR-094](../ADR-094-DoView-Notation-AI-Creation.md)
**Part:** A — DoView notation foundation
**Status:** In Progress

---

## Overview

Adds DoView as a fifth notation in Iris, alongside Simple, UML, ArchiMate, and C4.

---

## Database Changes

### Migration: `m027_doview_notation.py`

**Inserts into `notations`:**
```python
("doview", "DoView", "DoView outcomes-based theory of change notation", 4)
```

**Inserts into `diagram_types`:**
```python
("outcomes_map", "Outcomes Map", "Left-to-right causal outcomes flow", 7)
("overview",     "Overview",     "High-level overview with navigation tiles", 8)
```

**Inserts into `diagram_type_notations`:**
```python
("outcomes_map", "doview", 1)  # default
("overview",     "doview", 1)  # default
("free_form",    "doview", 0)  # DoView available on free_form
```

**Inserts into `themes`:**
- ID: `doview-default`, notation: `doview`
- Full config: see theme seeding section below

---

## Backend Changes

### `backend/app/diagrams/notation_detection.py`

Add:
```python
DOVIEW_TYPES: frozenset[str] = frozenset({
    "outcome_box", "final_outcome", "overview_tile", "source_reference",
})
```

Add branch to `detect_notations()`:
```python
elif entity_type in DOVIEW_TYPES:
    notations.add("doview")
```

Also update inline `_detect_notations_inline()` in `m020` to stay in sync (or note that old migration is fixed and new diagrams will auto-detect).

### `backend/app/themes/service.py`

Add DoView default theme in `seed_default_themes()`:

```python
doview_config = {
    "element_defaults": {
        "outcome_box":      {"bgColor": "#FFF2CC", "borderColor": "#D6B656", "fontColor": "#333333", "borderWidth": 2},
        "final_outcome":    {"bgColor": "#FFFFFF", "borderColor": "#CCCCCC", "fontColor": "#333333", "borderWidth": 2},
        "overview_tile":    {"bgColor": "#DAE8FC", "borderColor": "#6C8EBF", "fontColor": "#333333", "borderWidth": 2},
        "source_reference": {"bgColor": "#F5F5F5", "borderColor": "#666666", "fontColor": "#333333", "borderWidth": 1},
    },
    "stereotype_overrides": {
        "page_yellow":   {"bgColor": "#FFF2CC", "borderColor": "#D6B656"},
        "page_pink":     {"bgColor": "#F8CECC", "borderColor": "#B85450"},
        "page_blue":     {"bgColor": "#DAE8FC", "borderColor": "#6C8EBF"},
        "page_green":    {"bgColor": "#D5E8D4", "borderColor": "#82B366"},
        "page_beige":    {"bgColor": "#FFF4E6", "borderColor": "#D4A574"},
        "page_lavender": {"bgColor": "#E1D5E7", "borderColor": "#9673A6"},
        "page_peach":    {"bgColor": "#FFE6CC", "borderColor": "#D79B00"},
        "page_cyan":     {"bgColor": "#D4E1F5", "borderColor": "#7EA6E0"},
        "page_grey":     {"bgColor": "#F5F5F5", "borderColor": "#666666"},
        "page_white":    {"bgColor": "#FFFFFF", "borderColor": "#CCCCCC"},
    },
    "edge_defaults": {
        "causal_link": {"lineColor": "#C8C8C8", "lineWidth": 2},
    },
    "global": {
        "defaultBgColor": "#FFF2CC",
        "defaultBorderColor": "#D6B656",
        "defaultFontColor": "#333333",
    },
    "rendering": {
        "hideIcons": False,
        "borderRadius": 4,
    },
}
await db.execute(
    "INSERT OR REPLACE INTO themes (...) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
    ("doview-default", "DoView Default", "Official DoView 10-color palette", "doview",
     json.dumps(doview_config), 1, "system", now, now),
)
```

---

## Frontend Changes

### `frontend/src/lib/types/canvas.ts`

Add to `NotationType`:
```typescript
export type NotationType = 'simple' | 'uml' | 'archimate' | 'c4' | 'doview';
```

Add new types:
```typescript
export type DoviewEntityType =
    | 'outcome_box'
    | 'final_outcome'
    | 'overview_tile'
    | 'source_reference';

export type DoviewRelationshipType = 'causal_link';

export interface DoviewEntityTypeInfo {
    key: DoviewEntityType;
    label: string;
    icon: string;
    description: string;
}

export const DOVIEW_ENTITY_TYPES: DoviewEntityTypeInfo[] = [
    { key: 'outcome_box',      label: 'Outcome Box',      icon: '▭', description: 'A single achieved outcome in causal flow' },
    { key: 'final_outcome',    label: 'Final Outcome',    icon: '★', description: 'Ultimate impact — white box with grey top rule' },
    { key: 'overview_tile',    label: 'Overview Tile',    icon: '⬡', description: 'Navigation card linking to a subpage diagram' },
    { key: 'source_reference', label: 'Source Reference', icon: '◧', description: 'Citation or source URL' },
];

export const DOVIEW_RELATIONSHIP_TYPES: RelationshipTypeInfo[] = [
    { key: 'causal_link' as DoviewRelationshipType, label: 'Causal Link', description: 'A causes/leads to B — left-to-right causal flow' },
];

export const DOVIEW_DIAGRAM_TYPE_FILTER: Record<string, string[] | null> = {
    outcomes_map: ['outcome_box', 'final_outcome', 'source_reference'],
    overview:     ['final_outcome', 'overview_tile'],
    free_form:    null,
};
```

### `frontend/src/lib/canvas/registry.ts`

Add to `ALL_NODE_TYPE_KEYS`:
```typescript
// DoView
'outcome_box', 'final_outcome', 'overview_tile', 'source_reference',
```

Add to `ALL_EDGE_TYPE_KEYS`:
```typescript
// DoView
'causal_link',
```

### `frontend/src/lib/canvas/renderers/DoviewRenderer.svelte`

New component. Renders all four DoView entity types using `BaseNode`.

- `outcome_box`: Standard node, uses theme bgColor/borderColor, rounded corners (4px), centered text, bold font if `data.visual?.bold`.
- `final_outcome`: White box with a 3px solid grey top border (CSS: `border-top: 3px solid #CCCCCC`). Uses `nodeOverrideStyle`.
- `overview_tile`: Same as outcome_box but with a `🔗` link indicator if `data.linkedModelId` is set. Clickable navigation tile.
- `source_reference`: Compact box, smaller font (10px), muted grey colors.

```svelte
<script lang="ts">
    import BaseNode from '../BaseNode.svelte';
    import type { CanvasNodeData } from '$lib/types/canvas';
    import { nodeOverrideStyle } from '$lib/canvas/utils/visualStyles';

    interface Props { data: CanvasNodeData; selected?: boolean; }
    let { data, selected = false }: Props = $props();

    const DOVIEW_ICONS: Record<string, string> = {
        outcome_box:      '▭',
        final_outcome:    '★',
        overview_tile:    '⬡',
        source_reference: '◧',
    };

    const icon = $derived(DOVIEW_ICONS[data.entityType] ?? '▭');
    const visualStyle = $derived(nodeOverrideStyle(data.visual));
    const isFinalOutcome = $derived(data.entityType === 'final_outcome');
    const isOverviewTile = $derived(data.entityType === 'overview_tile');
    const isSourceRef = $derived(data.entityType === 'source_reference');
</script>

<div
    class="doview-node doview-node--{data.entityType}"
    class:doview-node--final={isFinalOutcome}
    style={visualStyle}
>
    <BaseNode {data} {selected} {icon} typeLabel={data.entityType} cssClass="canvas-node--{data.entityType}" />
</div>

<style>
    .doview-node--final_outcome {
        border-top: 3px solid #CCCCCC;
    }
</style>
```

### `frontend/src/lib/canvas/renderers/DoviewEdgeRenderer.svelte`

New edge renderer. Wraps existing `SimpleEdgeRenderer` or renders a plain step-routed edge with grey styling.

### `frontend/src/lib/canvas/DynamicNode.svelte`

Add DoView types set and dispatch branch (before the `{:else}` fallback):

```svelte
import DoviewRenderer from './renderers/DoviewRenderer.svelte';

const DOVIEW_TYPES = new Set([
    'outcome_box', 'final_outcome', 'overview_tile', 'source_reference',
]);
```

```svelte
{:else if notation === 'doview' || DOVIEW_TYPES.has(effectiveData.entityType)}
    <DoviewRenderer data={effectiveData} {selected} />
```

### `frontend/src/lib/canvas/DynamicEdge.svelte`

Add dispatch for `causal_link` edge type → `DoviewEdgeRenderer`.

### `frontend/src/lib/canvas/controls/EntityDialog.svelte`

Add DoView notation branch showing `DOVIEW_ENTITY_TYPES` when notation is `'doview'`.

### Diagram creation dialog

Add `outcomes_map` and `overview` diagram types for DoView notation (following existing pattern for notation-filtered diagram types).

---

## Seed Example Diagrams

Add to `backend/app/seed/example_models.py` (v6 revision):

1. **DoView Overview** — `overview` diagram, `doview` notation, ~6 `overview_tile` nodes in a 3-column grid
2. **DoView Final Outcomes** — `outcomes_map` diagram, `doview` notation, 5 `final_outcome` nodes stacked vertically
3. **DoView Outcomes Map** — `outcomes_map` diagram, `doview` notation, 4-column causal flow with `outcome_box` nodes and `causal_link` edges

---

## Tests

- `backend/tests/test_migrations/test_m027_doview_notation.py`
- `backend/tests/test_diagrams/test_notation_detection_doview.py`
- `backend/tests/test_themes/test_doview_theme.py`
- `backend/tests/test_seed/test_example_models.py` (update for v6)
- `frontend/tests/unit/doviewRenderer.test.ts`
- `frontend/tests/unit/doviewEdgeRenderer.test.ts`
- `frontend/tests/unit/registry.test.ts` (update)
- `frontend/tests/unit/canvasTypes.test.ts`
