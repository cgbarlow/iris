# SPEC-109-A: Package Context Selection

**ADR:** [ADR-109](../ADR-109-Package-Level-AI-Context.md)
**Part:** A — Package-level context filtering for multi-set AI Q&A
**Status:** Draft

---

## Overview

Extends the multi-set AI Q&A system (ADR-093) with optional package-level context filtering. Adds `package_ids` to `MultiSetQARequest`, filters the context builder to include only diagrams within selected packages (and their descendants), and enhances the frontend `MultiSetSelector` with an expandable package tree for drill-down selection.

---

## API Change

### `MultiSetQARequest` Model

```python
class MultiSetQARequest(BaseModel):
    question: str
    set_ids: list[UUID]
    package_ids: list[UUID] | None = None  # NEW
    conversation_id: UUID | None = None
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `question` | str | Yes | — | The user's question |
| `set_ids` | list[UUID] | Yes | — | Sets to include in context |
| `package_ids` | list[UUID] | No | None | Optional package filter; when provided, only diagrams in these packages (and descendants) are included |
| `conversation_id` | UUID | No | None | Existing conversation to continue |

**Backward compatibility:** When `package_ids` is `None` or `[]`, the context builder includes all diagrams from the selected sets — identical to pre-ADR-109 behaviour.

---

## Context Builder Changes

### `backend/app/ai/context_builder.py`

The context building function is modified to accept and apply the optional package filter.

#### Descendant Package Resolution

```python
async def resolve_package_ids_with_descendants(
    db: AsyncSession,
    package_ids: list[UUID],
) -> set[UUID]:
    """
    Given a list of package IDs, return the full set including
    all descendant packages (recursive).
    """
    expanded = set(package_ids)
    queue = list(package_ids)
    while queue:
        current_id = queue.pop()
        children = await db.execute(
            select(Package.id).where(Package.parent_package_id == current_id)
        )
        for (child_id,) in children:
            if child_id not in expanded:
                expanded.add(child_id)
                queue.append(child_id)
    return expanded
```

#### Diagram Filtering

When `package_ids` is provided and non-empty:

```python
async def build_context(
    db: AsyncSession,
    set_ids: list[UUID],
    package_ids: list[UUID] | None = None,
) -> str:
    query = select(Diagram).where(Diagram.set_id.in_(set_ids))

    if package_ids:
        expanded_ids = await resolve_package_ids_with_descendants(db, package_ids)
        query = query.where(Diagram.parent_package_id.in_(expanded_ids))

    diagrams = (await db.execute(query)).scalars().all()
    # ... continue with existing context serialisation
```

#### Entity Filtering

Entities are included only if they appear on at least one diagram that passed the package filter. This is derived from the filtered diagram set — no separate entity query modification is needed:

```python
# Existing pattern: entities are loaded via diagram.entities relationship
# Package filtering is inherited from the diagram query
entity_ids = set()
for diagram in diagrams:
    for node in diagram.canvas_data.get("nodes", []):
        if node.get("data", {}).get("entityId"):
            entity_ids.add(node["data"]["entityId"])
```

---

## Frontend Changes

### MultiSetSelector Enhancement

The `MultiSetSelector` component (used in the Ask AI panel) is enhanced with package drill-down.

#### Package Tree Display

```
[ ] Set: Strategic Plan 2026
  └─ [x] Health Programme          (12 diagrams)
  └─ [ ] Education Programme       (8 diagrams)
  └─ [x] Environment Programme     (6 diagrams)
      └─ [x] Water Quality          (3 diagrams)
      └─ [x] Air Quality            (3 diagrams)
[ ] Set: Operational Review
```

#### Interaction Rules

| Action | Behaviour |
|--------|-----------|
| Select a set (no packages expanded) | All packages in the set are included (no `package_ids` sent) |
| Expand a set | Shows package tree with checkboxes; all packages initially unchecked (full set context) |
| Check a package | Adds package to `package_ids`; includes all descendant packages automatically |
| Uncheck a package | Removes package (and descendants) from `package_ids` |
| Check all packages in a set | Equivalent to no filter — `package_ids` is cleared for that set |
| Uncheck all packages in a set | Set is still selected but all packages are explicitly included (same as no filter) |

#### State Management

```typescript
interface PackageSelection {
  setId: string;
  packageIds: string[] | null;  // null = all packages (no filter)
}

// When building the request:
const packageIds = selections
  .filter(s => s.packageIds !== null)
  .flatMap(s => s.packageIds!);

const request: MultiSetQARequest = {
  question: userQuestion,
  set_ids: selections.map(s => s.setId),
  package_ids: packageIds.length > 0 ? packageIds : undefined,
};
```

#### Package Loading

Packages for each set are loaded lazily when the user expands a set in the selector:

```typescript
async function loadPackagesForSet(setId: string): Promise<PackageTree[]> {
  const response = await fetch(`/api/sets/${setId}/packages`);
  return await response.json();
}
```

The package tree is built client-side from the flat list of packages using `parent_package_id` relationships.

---

## Diagram Count Badge

Each package node in the tree shows a diagram count badge (e.g., "(12 diagrams)") to help users understand the scope of each package. This count is returned by the `/api/sets/{set_id}/packages` endpoint.

---

## Test Coverage

### Backend Tests

- `backend/tests/test_ai/test_context_builder_packages.py`
  - No `package_ids` provided: all diagrams from selected sets included (no regression)
  - Empty `package_ids` list: same as no filter (no regression)
  - Single `package_id`: only diagrams with matching `parent_package_id` included
  - Multiple `package_ids`: diagrams from all specified packages included
  - Nested packages: selecting a parent package includes diagrams from descendant packages
  - Deeply nested packages (3+ levels): all descendants resolved correctly
  - Package from a non-selected set: ignored (no cross-set leakage)
  - Package with no diagrams: produces empty context for that package (no error)
  - Entity filtering: only entities appearing on filtered diagrams are included in context

- `backend/tests/test_ai/test_package_resolution.py`
  - `resolve_package_ids_with_descendants` returns input IDs plus all descendants
  - Single package with no children: returns only that package
  - Package with one level of children: returns parent + children
  - Package with deep nesting: returns entire subtree
  - Multiple input packages with overlapping descendants: no duplicates in result

- `backend/tests/test_ai/test_multi_set_qa_api.py`
  - `POST /api/ai/qa` with `package_ids` returns filtered response
  - `POST /api/ai/qa` without `package_ids` returns full-set response (regression test)
  - Invalid `package_ids` (non-existent UUIDs) are silently ignored
  - `package_ids` from sets not in `set_ids` are silently ignored

### Frontend Tests

- `frontend/tests/unit/multiSetSelector.test.ts`
  - Expanding a set loads and displays package tree
  - Checking a package adds it to selection
  - Checking a parent package auto-selects descendants
  - Unchecking all packages reverts to full-set context
  - Diagram count badges display correct counts
  - Package tree renders nested packages with correct indentation
  - `package_ids` is omitted from request when no packages are explicitly selected
  - `package_ids` is included in request when specific packages are selected
