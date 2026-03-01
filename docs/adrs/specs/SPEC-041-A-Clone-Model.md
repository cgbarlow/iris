# SPEC-041-A: Clone Model

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-041-A |
| **ADR Reference** | [ADR-041: Clone Model](../ADR-041-Clone-Model.md) |
| **Date** | 2026-03-01 |
| **Status** | Active |

---

## Overview

This specification details the frontend changes required to add a "Clone" button to the model detail page. Cloning creates a new model pre-populated with the original model's canvas data (node positions, edges, sequence diagram data), name (suffixed with "(Copy)"), description, and model type. No backend changes are required — the existing `POST /api/models` endpoint already accepts all necessary fields including `data`.

---

## A. New State Variable

Add a `showCloneDialog` state variable to the model detail page script block:

```typescript
let showCloneDialog = $state(false);
```

---

## B. Clone Handler

Add a `handleClone` async function that POSTs to `/api/models` with the cloned data:

```typescript
async function handleClone(name: string, modelType: string, description: string) {
    if (!model) return;
    try {
        const created = await apiFetch<Model>('/api/models', {
            method: 'POST',
            body: JSON.stringify({
                model_type: modelType,
                name,
                description,
                data: model.data ?? {},
            }),
        });
        showCloneDialog = false;
        await goto(`/models/${created.id}`);
    } catch (e) {
        error = e instanceof ApiError ? e.message : 'Failed to clone model';
    }
}
```

Key details:
- Uses `model.data` from the currently loaded model (includes nodes, edges, or sequence data)
- Uses `apiFetch<Model>` for type-safe response
- Navigates to the new model's detail page on success
- Closes the dialog on success
- Sets error state on failure using the existing error pattern

---

## C. Clone Button in Toolbar

Add a "Clone" button in the toolbar area between the "Edit" and "Delete" buttons:

```svelte
<button
    onclick={() => (showCloneDialog = true)}
    class="rounded px-4 py-2 text-sm"
    style="border: 1px solid var(--color-border); color: var(--color-fg)"
>
    Clone
</button>
```

The button uses the same styling as the "Edit" button (outline style, not filled like Delete).

---

## D. Clone ModelDialog Instance

Add a second `ModelDialog` instance for cloning, below the existing edit dialog:

```svelte
<ModelDialog
    open={showCloneDialog}
    mode="create"
    initialName="{model.name} (Copy)"
    initialType={model.model_type}
    initialDescription={model.description ?? ''}
    onsave={handleClone}
    oncancel={() => (showCloneDialog = false)}
/>
```

Key details:
- Uses `mode="create"` so the model type selector is enabled (allowing the user to change it if desired)
- Pre-fills name with `"{original name} (Copy)"`
- Pre-fills description from the original model
- Pre-fills model type from the original model
- The dialog title will show "Create Model" (from ModelDialog's mode logic)

---

## E. Visibility

The Clone button is placed in the main toolbar alongside Edit and Delete buttons. This toolbar is always visible regardless of whether the user is in browse mode or edit mode, so the Clone button is accessible in both modes.

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| Clone button visible on model detail page | Navigate to any model; verify "Clone" button appears in toolbar |
| Clone button visible in both browse and edit modes | Toggle edit mode; verify Clone button remains visible |
| Clicking Clone opens ModelDialog | Click Clone; verify dialog opens with "Create Model" title |
| Dialog pre-fills name with "(Copy)" suffix | Click Clone; verify name field contains "{model name} (Copy)" |
| Dialog pre-fills description | Click Clone; verify description matches original model |
| Dialog pre-fills model type | Click Clone; verify model type matches original model |
| Model type is editable in clone dialog | Click Clone; verify model type dropdown is interactive (not readonly) |
| Save creates new model with canvas data | Save cloned model; verify new model has same canvas layout |
| Navigation to new model after save | Save cloned model; verify browser navigates to new model's page |
| Error handling on failure | Simulate API failure; verify error message displays |

---

*This specification implements [ADR-041](../ADR-041-Clone-Model.md).*
