# SPEC-023-A: Browse Entity Panel

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-023-A |
| **ADR Reference** | [ADR-023: Browse Mode Entity Navigation](../ADR-023-Browse-Mode-Entity-Navigation.md) |
| **Date** | 2026-02-28 |
| **Status** | Active |

---

## Overview

This specification details the enhancements to the EntityDetailPanel component in browse mode, adding entity navigation links, cross-model reference listing, and linked model drill-down.

---

## A. CanvasNodeData Extension

### canvas.ts (MODIFY)

Add `linkedModelId` to the `CanvasNodeData` interface:

```typescript
export interface CanvasNodeData {
    label: string;
    entityType: SimpleEntityType;
    entityId?: string;
    description?: string;
    linkedModelId?: string;  // Model to drill-down to from browse mode
    [key: string]: unknown;
}
```

---

## B. EntityDetailPanel Enhancement

### EntityDetailPanel.svelte (MODIFY)

#### New Props

```typescript
interface Props {
    entity: CanvasNodeData | null;
    onclose: () => void;
    currentModelId?: string;  // Exclude current model from "Used In" list
}
```

#### API Integration

- When `entity.entityId` is present, fetch `GET /api/entities/{entityId}/models` using `apiFetch<EntityModelRef[]>()`
- Display results as a list of navigable links to `/models/{model_id}`
- Filter out `currentModelId` from the list to avoid self-referencing
- Handle loading and empty states

#### Navigation Links

1. **"View Entity"** — `<a href="/entities/{entityId}">` styled as a bordered button
2. **"Open Linked Model"** — `<a href="/models/{linkedModelId}">` styled as a primary filled button, only shown when `linkedModelId` is set
3. **Model list items** — `<a href="/models/{model_id}">` showing model name and type

#### Reactive Data Loading

Use Svelte 5 `$effect()` to reactively load models when the selected entity changes:

```typescript
$effect(() => {
    if (entity?.entityId) {
        loadModels(entity.entityId);
    } else {
        usedInModels = [];
    }
});
```

---

## C. Model Detail Page Integration

### +page.svelte (MODIFY)

Pass `currentModelId` to `EntityDetailPanel` so the current model is excluded from the "Used In Models" list:

```svelte
<EntityDetailPanel
    entity={selectedBrowseNode.data}
    onclose={() => (selectedBrowseNode = null)}
    currentModelId={model?.id}
/>
```

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| "View Entity" link navigates to entity detail page | Select entity node in browse mode; click "View Entity"; verify navigation to `/entities/{entityId}` |
| "Used In Models" lists all referencing models | Select entity used in multiple models; verify all models listed except current |
| Current model excluded from "Used In" list | Verify the model being viewed does not appear in the entity's model list |
| "Open Linked Model" shown when linkedModelId set | Set linkedModelId on a node; verify button appears and navigates correctly |
| Loading state displayed during API fetch | Select entity; verify "Loading..." text appears before results |
| Empty state when entity not used in other models | Select entity unique to current model; verify "Not used in any other models." message |
| Panel still works without entityId | Select node without entityId; verify basic info shown, no links or model list |

---

*This specification implements [ADR-023](../ADR-023-Browse-Mode-Entity-Navigation.md).*
