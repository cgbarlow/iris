# SPEC-101-A: Visual Toggles

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-101-A |
| **ADR** | [ADR-101](../ADR-101-Visual-Toggles.md) |
| **Status** | Draft |
| **Date** | 2026-03-23 |

---

## Overview

Three visual improvements: fix DoView double borders, add theme-controlled description visibility with per-node override, and add element usage count badge controlled by user setting.

---

## Fix: DoView Double Borders

**File:** `frontend/src/lib/canvas/renderers/DoviewRenderer.svelte`

Remove `visualStyle` from the wrapper `<div>` — only BaseNode's `.canvas-node` should apply border styles.

---

## Feature: Hide Description Toggle

**ThemeRenderingConfig extension:**
- Add `hideDescription?: boolean` to the interface
- DoView default theme sets `hideDescription: true`

**BaseNode change:** Check rendering config before showing description.

**Edit sidebar toggle:** "Show description" checkbox in ElementEditPanel dispatches `nodedatachange` with `field: 'hideDescription'`.

---

## Feature: Element Count Badge

**User setting:** `iris-show-element-count` in localStorage, toggled via Settings → Visual Toggles.

**Badge:** Small count in top-right of `.canvas-node` showing `diagram_usage_count` from the Element API response.

**Data flow:** Diagram page fetches Element per node (existing), passes `diagram_usage_count` to node data.
