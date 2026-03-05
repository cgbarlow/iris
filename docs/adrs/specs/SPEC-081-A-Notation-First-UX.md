# SPEC-081-A: Notation-First UX

## Overview

Implements ADR-081: surfaces notation as a first-class UX concept with user default setting, notation-first filtering in dialogs, and element-level notation storage.

## Database Schema

### Schema Changes

```sql
ALTER TABLE elements ADD COLUMN notation TEXT DEFAULT 'simple';
```

Migration: `m022_element_notation.py`, registered in `startup.py` after m021.

## Backend Changes

### Models (`elements/models.py`)

- `ElementCreate`: add `notation: str = "simple"`
- `ElementResponse`: add `notation: str = "simple"`

### Service (`elements/service.py`)

- `create_element()`: accept `notation` param, store in INSERT
- `get_element()`: include `e.notation` in SELECT and return dict
- `list_elements()`: include `e.notation` in SELECT and return

### Router (`elements/router.py`)

- `create()`: pass `body.notation` to service

### Seed Data (`seed/example_models.py`)

- Each element gets explicit `notation` value based on its type context

## Frontend Changes

### Default Notation Store

New file: `frontend/src/lib/stores/defaultNotation.svelte.ts`

```typescript
export function getDefaultNotation(): string {
    return localStorage?.getItem('iris-default-notation') ?? 'simple';
}
export function setDefaultNotation(value: string): void {
    localStorage?.setItem('iris-default-notation', value);
}
```

### Settings Page

Add "Default Notation" section after Theme with radio buttons for Simple, UML, ArchiMate, C4.

### DiagramDialog

Restructure create-mode form:
1. **Notation dropdown** (always visible, first field after Name) — defaults to user's `getDefaultNotation()`
2. **Diagram Type dropdown** (filtered by selected notation) — reset when notation changes

Notation→Type filtering matrix (from ADR-079):

| Notation | Available Types |
|----------|----------------|
| simple | component, sequence, deployment, process, roadmap, free_form |
| uml | component, sequence, class, deployment, process, free_form |
| archimate | component, deployment, process, free_form |
| c4 | component, deployment, free_form |

### EntityDialog

Add visible **Notation dropdown** above Type dropdown:
- Default: `notation` prop (from diagram) or user default
- When notation changes: reset entity type to first type of new notation
- `onsave` callback includes notation parameter

### EntityDetailPanel

Add "Notation" row in definition list after "Type".

### Element Detail Page

Add "Notation" row in Overview accordion after "Type".

### Type Changes

- `Element` interface: add `notation?: string`
- `CanvasNodeData`: add `notation?: string`

### Diagram Detail Page

- `handleAddElement`: accept and pass `notation` param
- `handleEditElementSave`: similarly
- `handleLinkElement`: set `notation` from element data
- `<EntityDialog>` usages: pass `notation` prop

## Test Plan

### Backend Tests (`test_elements/test_notation.py`)

- Create element with explicit notation
- Create element without notation (defaults to 'simple')
- Get element returns notation field
- List elements returns notation field

### Frontend Tests (`notationUx.test.ts`)

- `getDefaultNotation` returns 'simple' when unset
- `setDefaultNotation` stores value
- Type filtering by notation
