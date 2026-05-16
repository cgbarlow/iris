# ADR-185: Nullable-filter three-valued query convention

Status: Accepted (2026-05-16)

## Context

`GET /api/diagrams` already supports filtering by `parent_package_id`
with three distinct semantics, established in v6.6.4 to fix issue #133
Phase 1 UAT defects:

| Query string | Meaning |
|---|---|
| (omitted) | No filter applied — return diagrams at any parent. |
| `?parent_package_id=null` (literal string) | Return only diagrams with `parent_package_id IS NULL` (root-level). |
| `?parent_package_id=<uuid>` | Return only diagrams with `parent_package_id = <uuid>` (exact match). |

This is a useful pattern: the "root-level only" case is a common UX
need (e.g. "show me the top-level diagrams under this set") and would
otherwise require either a separate endpoint or out-of-band signalling.

Today the parsing logic for the three states is **inlined** in
`backend/app/diagrams/service.py::list_diagrams`. Issue #149 introduces
a second consumer (`list_elements.package_id`) and we expect more — for
example a future `list_diagrams.set_id` filter that distinguishes
"setless" from "any set".

Inlining the same three-branch logic in every list endpoint is the kind
of duplication protocols §13 specifically warns against.

## Decision

Extract the parsing into a single shared helper and codify the semantics
as a project-wide convention for any list endpoint that wants to filter
on a nullable ID column.

### Shared helper

```python
# backend/app/common/nullable_filter.py
from __future__ import annotations
from typing import Literal

NullableIdFilter = (
    tuple[Literal["none"]]
    | tuple[Literal["is_null"]]
    | tuple[Literal["eq"], str]
)


def parse_nullable_id(value: str | None) -> NullableIdFilter:
    """Parse a three-valued nullable-ID query parameter.

    - ``None`` (omitted) → ``("none",)`` — caller applies no filter.
    - ``"null"`` (literal string) → ``("is_null",)`` — caller adds
      ``WHERE col IS NULL``.
    - Any other string → ``("eq", value)`` — caller adds
      ``WHERE col = ?`` with ``value`` as the bound parameter.
    """
    if value is None:
        return ("none",)
    if value == "null":
        return ("is_null",)
    return ("eq", value)
```

### Call-site convention

Every list endpoint that uses a nullable-ID filter passes the parameter
through `parse_nullable_id` and switches on the tagged tuple to build
its SQL fragment. The string `"null"` is reserved as the sentinel for
"is null" — no other URL-encoded form (`?col=`, `?col=NULL`,
`?col=None`) is recognised. Documented in SPEC-185-A so future endpoint
authors converge on the same shape.

### Consumers

| Endpoint | Column | Status |
|---|---|---|
| `GET /api/diagrams` | `parent_package_id` | Existing (v6.6.4); refactored in v6.7.0 to use the shared helper. |
| `GET /api/elements` | `package_id` | New in v6.7.0 (ADR-184). |
| Future list endpoints | TBD | Use the helper from day one. |

## Why not booleans (`?include_null=true`)

- Two query parameters for one filter doubles the surface area and
  invites contradictions (`?col=<id>&include_null=true` — does it
  match the id, the null, or both?).
- The string sentinel `"null"` is unambiguous and matches the JSON
  primitive being modelled.

## Why not POST + body

- Listing endpoints are idempotent GETs; pushing them to POST to carry
  a JSON-typed body would break caching, history, and the principle of
  REST verb meaning.

## Why not OData / RHS Colon syntax

- `?col=is:null` or `?col:eq=<id>` works but adds a parsing layer for
  one corner case. The string-sentinel approach is the smallest delta
  to a plain `?col=<id>` query.

## Consequences

- New module `backend/app/common/nullable_filter.py`.
- `backend/app/diagrams/service.py::list_diagrams` refactored to use
  `parse_nullable_id` (DRY).
- `backend/app/elements/service.py::list_elements` adopts the helper
  for `package_id` (ADR-184).
- New tests `backend/tests/test_nullable_filter.py` cover the three
  branches and a small fuzzing case (whitespace, casing) to confirm
  only the literal `"null"` triggers the IS-NULL branch.

## Verification

- `pytest backend/tests/test_nullable_filter.py` — unit tests for the
  helper.
- `pytest backend/tests/test_diagrams_list_filter.py` (existing) —
  passes after the refactor with no behavioural change.
- `pytest backend/tests/test_element_package_membership.py` —
  exercises the helper end-to-end via the new endpoint.

## See also

- [SPEC-185-A](specs/SPEC-185-A-Nullable-Filter-Convention.md) — helper
  signature, examples, consumers.
- [ADR-184](ADR-184-Element-Package-Membership.md) — first new consumer.
- Issue [#149](https://github.com/cgbarlow/iris/issues/149).
- v6.6.4 release notes — origin of the existing semantics in
  `list_diagrams.parent_package_id`.
