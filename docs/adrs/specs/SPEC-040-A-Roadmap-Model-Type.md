# SPEC-040-A: Roadmap Model Type Implementation

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-040-A |
| **ADR Reference** | [ADR-040: Roadmap Model Type](../ADR-040-Roadmap-Model-Type.md) |
| **Date** | 2026-03-01 |
| **Status** | Active |

---

## Overview

This specification details the frontend changes required to add a `roadmap` model type to Iris. The change is frontend-only: the backend already accepts arbitrary `model_type` strings. Roadmap models use the existing simple canvas view for rendering.

---

## A. ModelDialog.svelte

### File

`frontend/src/lib/components/ModelDialog.svelte`

### Change

Add a new entry to the `MODEL_TYPES` array:

```typescript
const MODEL_TYPES = [
    { value: 'simple', label: 'Simple' },
    { value: 'component', label: 'Component' },
    { value: 'sequence', label: 'Sequence' },
    { value: 'uml', label: 'UML' },
    { value: 'archimate', label: 'ArchiMate' },
    { value: 'roadmap', label: 'Roadmap' },
];
```

This makes "Roadmap" available in the model creation dialog's type dropdown.

---

## B. Model Detail Page (+page.svelte)

### File

`frontend/src/routes/models/[id]/+page.svelte`

### Change

In the `canvasType` derived expression, add a mapping for `roadmap` before the default fallback:

```typescript
const canvasType = $derived.by(() => {
    if (!model) return 'simple';
    const mt = model.model_type;
    if (mt === 'sequence') return 'sequence';
    if (mt === 'uml') return 'uml';
    if (mt === 'archimate') return 'archimate';
    if (mt === 'roadmap') return 'simple';
    return 'simple'; // 'simple' and 'component' both use simple view
});
```

This ensures roadmap models explicitly resolve to the simple canvas, making the intent clear rather than relying on the default fallback.

---

## C. Models List Page (+page.svelte)

### File

`frontend/src/routes/models/+page.svelte`

### Change

Add a new `<option>` to the type filter `<select>`:

```svelte
<option value="roadmap">Roadmap</option>
```

This allows users to filter the models list to show only roadmap models.

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| Roadmap appears in model creation dialog | Open "New Model" dialog; verify "Roadmap" is in the type dropdown |
| Roadmap model can be created | Select "Roadmap" type, enter name, submit; verify model is created |
| Roadmap model detail shows simple canvas | Navigate to a roadmap model; verify canvas tab renders the simple canvas view |
| Roadmap filter works on models list | Select "Roadmap" from type filter; verify only roadmap models are shown |
| No backend changes required | Verify no backend files were modified |

---

*This specification implements [ADR-040](../ADR-040-Roadmap-Model-Type.md).*
