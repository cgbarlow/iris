# SPEC-055-C: Tree View

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-055-C |
| **ADR** | [ADR-055](../ADR-055-Model-Hierarchy.md) |
| **Status** | Implemented |

## Overview

Tree view mode added to the Models page alongside existing list and gallery views.

## Components

### TreeNode (`src/lib/components/TreeNode.svelte`)

Recursive Svelte 5 component for rendering hierarchy nodes:
- Expand/collapse with arrow keys and click
- Depth-based indentation (20px per level)
- Model type badge
- Current model highlighting via `aria-current="page"`
- Search filtering (shows matching nodes and ancestors to maintain structure)
- Auto-expands first 2 levels

### Models Page Changes

- Added `'tree'` to `viewMode` union type
- Tree view toggle button with `aria-pressed`
- Fetches `GET /api/models/hierarchy` when tree view is selected
- `searchQuery` passed to TreeNode for filtering

## Types

Added to `src/lib/types/api.ts`:
- `parent_model_id?: string | null` on `Model` interface
- New `ModelHierarchyNode` interface with recursive `children`
