# SPEC-055-D: Breadcrumbs

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-055-D |
| **ADR** | [ADR-055](../ADR-055-Model-Hierarchy.md) |
| **Status** | Implemented |

## Overview

Breadcrumb navigation on model detail page showing ancestor chain.

## Implementation

On `models/[id]/+page.svelte`:

- `loadAncestors(id)` called during model load
- Fetches `GET /api/models/{id}/ancestors` — returns root-first ancestor chain
- Rendered as `<nav aria-label="Model hierarchy breadcrumb">` with `<ol>` structure
- Each ancestor is a link to its model detail page
- Current model shown as `<span aria-current="page">`
- Only rendered when ancestors exist (root models show no breadcrumb)
