# SPEC-091-C: Icon Picker UI

**ADR:** ADR-091
**Date:** 2026-03-08

## Changes

### 1. IconPicker component

Create `IconPicker.svelte` — a popover panel with:
- **Search input**: filters icons by name across all sets using substring match
- **Set tabs**: toggle between `lucide`, `archimate` (and `custom` when available)
- **Grid display**: icons rendered at 24px in a responsive grid
- **Selection**: click an icon to assign it; highlight the currently assigned icon
- **Clear button**: remove the icon assignment from the node

### 2. Trigger from node context menu

In edit mode, add an "Assign Icon" item to the node right-click context menu. Clicking it
opens the IconPicker popover anchored to the node.

### 3. Trigger from properties panel

In the node properties/detail panel (edit mode), add an icon section showing the current
icon with a button to open the IconPicker.

### 4. Icon preview in picker

When hovering an icon in the grid, show a tooltip with the icon name. The selected icon
renders at the node's actual size in a preview area above the grid.

### 5. Persist selection

On icon selection, update the node's visual data (`icon: { set, name }`) and persist via
the existing visual override PATCH endpoint (same as SPEC-091-A).

## Test Plan

- Unit test: IconPicker renders, search filters icons correctly
- Unit test: selecting an icon updates node visual data
- Unit test: clear button removes icon assignment
- Integration test: icon picker accessible from context menu in edit mode, hidden in browse mode
