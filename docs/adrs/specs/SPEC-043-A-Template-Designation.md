# SPEC-043-A: Template Designation

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-043-A |
| **ADR Reference** | [ADR-043: Template Designation](../ADR-043-Template-Designation.md) |
| **Date** | 2026-03-01 |
| **Status** | Active |

---

## Overview

This specification details the frontend changes required to implement template designation for models. Templates are models tagged with the special `template` tag, managed via the existing tag API endpoints (`POST /api/models/{id}/tags` and `DELETE /api/models/{id}/tags/template`). The feature adds three UI elements: a Template checkbox on the model detail overview tab, a Templates toggle button on the model list page, and a template badge on model list items/cards.

---

## A. Model Detail Page — Template Checkbox

### A.1 Derived State

Add a derived `isTemplate` property computed from the model's tags:

```typescript
const isTemplate = $derived((model?.tags ?? []).includes('template'));
```

### A.2 Toggle Handler

Add a `toggleTemplate` async function that adds or removes the `template` tag:

```typescript
async function toggleTemplate() {
    if (!model) return;
    try {
        if (isTemplate) {
            await apiFetch(`/api/models/${model.id}/tags/${encodeURIComponent('template')}`, {
                method: 'DELETE',
            });
        } else {
            await apiFetch(`/api/models/${model.id}/tags`, {
                method: 'POST',
                body: JSON.stringify({ tag: 'template' }),
            });
        }
        await loadModel(model.id);
    } catch (e) {
        error = e instanceof ApiError ? e.message : 'Failed to update template status';
    }
}
```

### A.3 Checkbox UI

Add a "Template" checkbox in the overview tab, placed between the description definition list and the Tags section:

```svelte
<div class="mt-4 flex items-center gap-2">
    <label class="flex items-center gap-2 text-sm cursor-pointer" style="color: var(--color-fg)">
        <input
            type="checkbox"
            checked={isTemplate}
            onchange={toggleTemplate}
            aria-label="Mark as template"
        />
        Template
    </label>
    <span class="text-xs" style="color: var(--color-muted)">
        Mark this model as a reusable template
    </span>
</div>
```

---

## B. Model List Page — Templates Toggle Button

### B.1 State Variable

Add a `templateFilter` state variable:

```typescript
let templateFilter = $state(false);
```

### B.2 Filter Logic

Extend the `filteredModels` derived to include template filtering:

```typescript
if (templateFilter && !(m.tags ?? []).includes('template')) return false;
```

### B.3 Toggle Button

Add a "Templates" toggle button in the filters bar, after the view mode buttons:

```svelte
<button
    onclick={() => (templateFilter = !templateFilter)}
    aria-label="Show templates only"
    aria-pressed={templateFilter}
    class="rounded border px-3 py-2 text-sm"
    style="border-color: var(--color-border); {templateFilter
        ? 'background: var(--color-primary); color: white'
        : 'background: var(--color-bg); color: var(--color-fg)'}"
>
    Templates
</button>
```

---

## C. Template Badge on Model List Items

### C.1 List View Badge

Add a "Template" badge in the list view for models that have the `template` tag, placed before other tag badges:

```svelte
{#if (model.tags ?? []).includes('template')}
    <span
        class="rounded px-2 py-0.5 text-xs font-medium"
        style="background: var(--color-success, #16a34a); color: white"
    >
        Template
    </span>
{/if}
```

### C.2 Gallery View Badge

Add a "Template" badge in the gallery card view below the model type badge:

```svelte
{#if (model.tags ?? []).includes('template')}
    <span
        class="rounded px-2 py-0.5 text-xs font-medium w-fit"
        style="background: var(--color-success, #16a34a); color: white"
    >
        Template
    </span>
{/if}
```

---

## D. Tag Rendering

The `template` tag continues to appear in the regular tag pills via the existing `TagInput` component on the model detail page. The checkbox provides a convenient toggle, while the `TagInput` still allows manual removal. Both are kept in sync because both call `loadModel()` after modification.

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| Template checkbox visible on model detail overview tab | Navigate to model detail; verify checkbox appears |
| Checking the checkbox adds the `template` tag | Check the box; verify `template` appears in the tags list |
| Unchecking the checkbox removes the `template` tag | Uncheck the box; verify `template` is removed from tags |
| Checkbox reflects existing template tag state | Add `template` tag manually; verify checkbox is checked |
| Templates toggle button visible on model list page | Navigate to models list; verify "Templates" button appears |
| Toggling Templates button filters to template models | Click "Templates"; verify only models with `template` tag shown |
| Template badge appears on list items | Tag a model as template; verify badge shows in list view |
| Template badge appears on gallery cards | Tag a model as template; verify badge shows in gallery view |
| Template badge uses distinct color (success/green) | Verify badge has green background, distinct from type badge |
| No backend changes required | Verify all functionality uses existing tag API endpoints |

---

*This specification implements [ADR-043](../ADR-043-Template-Designation.md).*
