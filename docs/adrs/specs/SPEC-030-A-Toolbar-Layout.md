# SPEC-030-A: Toolbar Layout Implementation

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-030-A |
| **ADR Reference** | [ADR-030: Model Canvas Toolbar Layout](../ADR-030-Model-Canvas-Toolbar-Layout.md) |
| **Date** | 2026-02-28 |
| **Status** | Active |

---

## Overview

This specification defines the toolbar button ordering and grouping for both canvas-type and sequence-type model edit toolbars. Buttons are reorganised into four semantic groups — Create, Edit, Persist, and View — separated by visual gaps.

---

## A. Toolbar Group Structure

All toolbar groups follow this CSS pattern:

- **Parent container:** `<div class="mb-3 flex items-center gap-4">` — `gap-4` creates visual separation between groups
- **Group wrapper:** `<div class="flex items-center gap-2">` — `gap-2` keeps buttons within a group tight
- **View group:** Uses `<div class="ml-auto">` to push Focus button to rightmost position

---

## B. Canvas Toolbar Layout (Non-Sequence Models)

Applies to: simple, UML, ArchiMate, and component model types.

### Edit Mode Button Order

| Position | Group | Button | Notes |
|----------|-------|--------|-------|
| 1 | Create | Add Entity | Opens EntityDialog |
| 2 | Create | Link Entity | Opens EntityPicker |
| 3 | Edit | Delete Edge | *Placeholder — not yet implemented* |
| 4 | Edit | Undo | *Placeholder — not yet implemented* |
| 5 | Edit | Redo | *Placeholder — not yet implemented* |
| 6 | Persist | Save / Saving... | Disabled when clean or saving |
| 7 | Persist | Discard | Reverts to saved state |
| 8 | Persist | Unsaved changes | Conditional text indicator |
| 9 | View | Focus | Pushed right with `ml-auto` |

### Browse Mode

| Position | Group | Button |
|----------|-------|--------|
| 1 | — | Edit Canvas |
| 2 | View | Focus (ml-auto) |

---

## C. Sequence Toolbar Layout

Applies to: sequence model types.

### Edit Mode Button Order

| Position | Group | Button | Notes |
|----------|-------|--------|-------|
| 1 | Create | Add Participant | Opens ParticipantDialog |
| 2 | Create | Add Message | Opens MessageDialog; disabled when < 2 participants |
| 3 | Edit | Delete Selected | Disabled when no message selected |
| 4 | Persist | Save / Saving... | Disabled when clean or saving |
| 5 | Persist | Discard | Reverts to saved state |
| 6 | Persist | Unsaved changes | Conditional text indicator |
| 7 | View | Focus | Pushed right with `ml-auto` |

### Browse Mode

| Position | Group | Button |
|----------|-------|--------|
| 1 | — | Edit Canvas |
| 2 | View | Focus (ml-auto) |

---

## D. File Changes

### `frontend/src/routes/models/[id]/+page.svelte`

1. **Sequence toolbar** (~line 511): Change parent `gap-2` to `gap-4`. Wrap buttons in group divs. Reorder: Create group (Add Participant, Add Message), Edit group (Delete Selected), Persist group (Save, Discard, Unsaved indicator). Move Focus button into `ml-auto` wrapper.

2. **Canvas toolbar** (~line 626): Same restructuring. Reorder: Create group (Add Entity, Link Entity), Edit group (placeholder comments for Delete Edge, Undo, Redo), Persist group (Save, Discard, Unsaved indicator). Move Focus button into `ml-auto` wrapper.

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| Canvas toolbar groups visible | Enter edit mode on simple model; verify gap between Create, Edit, Persist groups |
| Canvas button order correct | Verify left-to-right: Add Entity, Link Entity, [gap], placeholders, [gap], Save, Discard, Unsaved, [spacer], Focus |
| Sequence toolbar groups visible | Enter edit mode on sequence model; verify gap between Create, Edit, Persist groups |
| Sequence button order correct | Verify left-to-right: Add Participant, Add Message, [gap], Delete Selected, [gap], Save, Discard, Unsaved, [spacer], Focus |
| Focus button rightmost | Verify Focus button aligned to right edge in both toolbars |
| Browse mode unaffected | Verify Edit Canvas and Focus buttons still work in browse mode |
| All button functionality preserved | Verify all onclick, disabled, and style attributes unchanged |

---

*This specification implements [ADR-030](../ADR-030-Model-Canvas-Toolbar-Layout.md).*
