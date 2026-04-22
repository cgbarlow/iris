# SPEC-132-B: Creation Type Selector

**ADR:** [ADR-132](../ADR-132-Expanded-AI-Creation-Notations.md)
**Part:** B — Registry-driven notation + diagram-type selector in `SetQA.svelte`
**Status:** In Progress

---

## Overview

Replace the hardcoded DoView-only notation `<select>` in the Create Diagram mode with two registry-driven dropdowns. The user must pick a notation, and — for every notation except DoView — a diagram type, before the send button enables. DoView's in-prompt Stage 0 branching (outcomes_map vs overview) is preserved: when DoView is selected, the diagram-type selector is hidden entirely.

---

## Backend changes

### Endpoint: `GET /api/registry/creation-catalogue`

**Location:** `backend/app/diagrams/registry_router.py`

**Behaviour:** returns every `(notation, diagram_type)` pair for which AI creation is currently possible. A pair is considered creatable when:

- an active `layer='notation'` row exists for the notation, **and**
- either (a) the notation is `doview` (DoView does not use the diagram_type layer and relies on its own in-prompt branching), or (b) an active `layer='diagram_type'` row exists for the diagram_type.

**Response shape:**

```json
{
  "items": [
    {
      "notation": "doview",
      "notation_label": "DoView",
      "diagram_type": null,
      "diagram_type_label": null,
      "requires_diagram_type": false
    },
    {
      "notation": "uml",
      "notation_label": "UML",
      "diagram_type": "sequence",
      "diagram_type_label": "Sequence",
      "requires_diagram_type": true
    }
    // … one row per creatable pair
  ]
}
```

Labels for notation and diagram_type come from the existing `notations` and `diagram_types` registry tables (m020). `requires_diagram_type` tells the frontend whether to render the second selector — it is `false` only for `doview`.

**SQL (SQLite variant):**

```sql
SELECT DISTINCT
  n.id AS notation,
  n.label AS notation_label,
  CASE WHEN n.id = 'doview' THEN NULL ELSE dt.id END AS diagram_type,
  CASE WHEN n.id = 'doview' THEN NULL ELSE dt.label END AS diagram_type_label,
  CASE WHEN n.id = 'doview' THEN 0 ELSE 1 END AS requires_diagram_type
FROM notations n
LEFT JOIN diagram_type_notations dtn ON dtn.notation_id = n.id
LEFT JOIN diagram_types dt ON dt.id = dtn.diagram_type_id
WHERE EXISTS (
  SELECT 1 FROM ai_creation_prompts
  WHERE layer = 'notation' AND notation = n.id AND is_active = 1
)
AND (
  n.id = 'doview'
  OR EXISTS (
    SELECT 1 FROM ai_creation_prompts
    WHERE layer = 'diagram_type' AND diagram_type = dt.id AND is_active = 1
  )
)
ORDER BY n.display_order, dt.display_order;
```

For DoView, the LEFT JOIN still produces rows for its two diagram types, but the `CASE` collapses `diagram_type` to NULL and deduplicates. The backend reduces DoView's multiple rows into a single `{notation: 'doview', diagram_type: null}` entry before returning.

**Empty-catalogue fallback:** if the query returns zero rows (greenfield install, seeds not yet run), return a synthesised DoView entry so the UI does not appear broken. This matches current behaviour where DoView is the only option.

**Authorisation:** same as other registry endpoints (authenticated users; anonymous view-only per ADR-123 is fine since the catalogue is not sensitive).

### Router plumbing in `backend/app/ai/router.py`

Verify the existing creation-mode branch (line ~417) reads `diagram_type` from the request body and passes it to `build_creation_system_prompt()`. If missing, add the parameter. For DoView requests (where `diagram_type` is null or omitted), pass `None` so the builder composes `base + notation` only — matching today's DoView behaviour.

---

## Frontend changes

### `frontend/src/lib/components/SetQA.svelte`

**State:**

- Change initial value of `selectedNotation` (line 40) from `'doview'` to `''` — no pre-selection.
- Add `let selectedDiagramType = $state('')`.
- Add `let creationCatalogue = $state<CreationCatalogueItem[]>([])`.
- Add `let catalogueLoaded = $state(false)`.

**Derived helpers:**

```svelte
<script lang="ts">
  type CatalogueItem = {
    notation: string;
    notation_label: string;
    diagram_type: string | null;
    diagram_type_label: string | null;
    requires_diagram_type: boolean;
  };

  // Unique notations for the first dropdown
  const notations = $derived(
    [...new Map(creationCatalogue.map(i => [i.notation, i])).values()]
  );

  // Diagram types available for the selected notation
  const diagramTypesForNotation = $derived(
    creationCatalogue
      .filter(i => i.notation === selectedNotation && i.diagram_type !== null)
  );

  const requiresDiagramType = $derived(
    notations.find(n => n.notation === selectedNotation)?.requires_diagram_type ?? false
  );

  const canSubmit = $derived(
    creationMode
      ? !!selectedNotation && (!requiresDiagramType || !!selectedDiagramType)
      : true
  );
</script>
```

**On-mount fetch (inside existing `onMount` or equivalent):**

```ts
const res = await fetch('/api/registry/creation-catalogue');
if (res.ok) {
  const data = await res.json();
  creationCatalogue = data.items;
}
catalogueLoaded = true;
```

**Markup replacing lines 575–583:**

```svelte
{#if creationMode}
  <select
    bind:value={selectedNotation}
    onchange={() => { selectedDiagramType = ''; }}
    class="rounded border px-2 py-1.5 text-sm"
    style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
  >
    <option value="" disabled>Select notation…</option>
    {#each notations as n}
      <option value={n.notation}>{n.notation_label}</option>
    {/each}
  </select>

  {#if selectedNotation && requiresDiagramType}
    <select
      bind:value={selectedDiagramType}
      class="rounded border px-2 py-1.5 text-sm"
      style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
    >
      <option value="" disabled>Select diagram type…</option>
      {#each diagramTypesForNotation as dt}
        <option value={dt.diagram_type}>{dt.diagram_type_label}</option>
      {/each}
    </select>
  {/if}
{/if}
```

**Send button guard:** add `disabled={!canSubmit}` to the existing send button markup.

**Placeholder text (line 830):** replace the DoView-special-case ternary with a generic derived label:

```svelte
const creationPlaceholder = $derived(
  selectedNotation
    ? `Describe what you'd like a ${selectedDiagramType
        ? `${notationLabel(selectedNotation)} ${diagramTypeLabel(selectedDiagramType)}`
        : notationLabel(selectedNotation)} diagram of…`
    : 'Select a diagram notation above to begin…'
);
```

Where `notationLabel()` and `diagramTypeLabel()` look up the display label from `creationCatalogue`.

**Request body (line 242):**

```ts
{
  // … existing fields
  notation: selectedNotation,
  diagram_type: selectedNotation === 'doview' ? null : (selectedDiagramType || null),
  // … existing fields
}
```

Sending `null` (not omission) for DoView's `diagram_type` keeps the request shape stable for the router.

**DoView hidden-branch rule:** because DoView's catalogue row has `requires_diagram_type=false`, the `{#if requiresDiagramType}` block collapses and the diagram-type selector never renders. DoView's request body carries `diagram_type: null`, which `build_creation_system_prompt(db, 'doview', None)` handles today — composing only `base + doview notation`, identical to the current behaviour.

---

## Accessibility and UX

- Both `<select>` elements use `aria-label` matching their visible purpose ("Diagram notation" and "Diagram type") — currently the hardcoded select has no label at all, so this is an improvement.
- Send button disabled state has a matching tooltip explaining *why* it is disabled ("Select a notation and diagram type first" / "Select a notation first").
- Empty-catalogue state: if `catalogueLoaded && notations.length === 0`, show an inline hint "No diagram creation options available — contact an administrator." No broken UI.
- Loading state: during initial fetch show disabled selects with placeholder "Loading…".

---

## Acceptance criteria

- Opening Create Diagram mode with a freshly-seeded backend shows a single notation selector with no default selection and the send button disabled.
- Selecting DoView reveals no diagram-type selector; the send button enables as soon as a non-empty message is typed.
- Selecting UML reveals a diagram-type selector with options "Sequence" and "Class"; the send button remains disabled until both selectors and the message are non-empty.
- Changing the notation after a diagram type was picked resets the diagram-type selector to empty (user re-picks).
- The ask request body always contains `notation`; it contains `diagram_type: null` for DoView and `diagram_type: <value>` for others.
- Existing DoView conversations and the apply flow behave identically to pre-change (regression).
