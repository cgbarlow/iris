# SPEC-185-A: Nullable-filter three-valued query convention

ADR: [ADR-185](../ADR-185-Nullable-Filter-Convention.md)

## Summary

A single shared helper `parse_nullable_id(value)` that codifies the
three-valued query semantics already in use by
`list_diagrams.parent_package_id` and now adopted by
`list_elements.package_id`.

## Module: `backend/app/common/nullable_filter.py`

```python
"""Three-valued nullable-ID query parameter convention.

Used by list endpoints that want to distinguish:

- "no filter" (URL omits the parameter)
- "match NULL" (URL uses the literal string ``"null"``)
- "match a specific id" (URL passes the id)

See ADR-185 for rationale and SPEC-185-A for the helper signature.
"""

from __future__ import annotations

from typing import Literal

NullableIdFilter = (
    tuple[Literal["none"]]
    | tuple[Literal["is_null"]]
    | tuple[Literal["eq"], str]
)


def parse_nullable_id(value: str | None) -> NullableIdFilter:
    """Parse a three-valued nullable-ID query parameter.

    Args:
        value: The query parameter as received from FastAPI. ``None``
            when the parameter is omitted; otherwise the raw string.

    Returns:
        A tagged tuple. ``("none",)`` means no filter; ``("is_null",)``
        means add ``WHERE col IS NULL``; ``("eq", id)`` means add
        ``WHERE col = ?`` with ``id`` as the bound parameter.

    Examples:
        >>> parse_nullable_id(None)
        ('none',)
        >>> parse_nullable_id("null")
        ('is_null',)
        >>> parse_nullable_id("abc-123")
        ('eq', 'abc-123')
        >>> parse_nullable_id("NULL")   # uppercase is treated as a value
        ('eq', 'NULL')
    """
    if value is None:
        return ("none",)
    if value == "null":
        return ("is_null",)
    return ("eq", value)
```

## Call-site pattern

```python
from app.common.nullable_filter import parse_nullable_id

f = parse_nullable_id(package_id)
match f:
    case ("none",):
        pass
    case ("is_null",):
        where_clauses.append("e.package_id IS NULL")
    case ("eq", value):
        where_clauses.append("e.package_id = ?")
        params.append(value)
```

`match` keeps the three branches obvious and exhaustive. Python's
match-statement is available on every supported runtime in this repo.

## Refactor: `backend/app/diagrams/service.py::list_diagrams`

The existing v6.6.4 inline implementation is replaced:

**Before** (inlined):

```python
if parent_package_id == "null":
    where_clauses.append("d.parent_package_id IS NULL")
elif parent_package_id is not None:
    where_clauses.append("d.parent_package_id = ?")
    params.append(parent_package_id)
```

**After**:

```python
match parse_nullable_id(parent_package_id):
    case ("none",):
        pass
    case ("is_null",):
        where_clauses.append("d.parent_package_id IS NULL")
    case ("eq", pid):
        where_clauses.append("d.parent_package_id = ?")
        params.append(pid)
```

Existing `list_diagrams` tests pass unchanged — the refactor is
behaviour-preserving.

## New consumer: `backend/app/elements/service.py::list_elements`

Adds a `package_id: str | None` parameter wired through to the same
helper. See SPEC-184-A for the full element list signature.

## Tests: `backend/tests/test_nullable_filter.py`

```python
from app.common.nullable_filter import parse_nullable_id


def test_parse_none() -> None:
    assert parse_nullable_id(None) == ("none",)


def test_parse_null_literal() -> None:
    assert parse_nullable_id("null") == ("is_null",)


def test_parse_uuid_literal() -> None:
    assert parse_nullable_id("abc-123") == ("eq", "abc-123")


def test_parse_uppercase_null_is_treated_as_value() -> None:
    assert parse_nullable_id("NULL") == ("eq", "NULL")


def test_parse_empty_string_is_treated_as_value() -> None:
    assert parse_nullable_id("") == ("eq", "")
```

## Out of scope

- Generalising to non-ID columns (booleans, enums). Different problem,
  different helper.
- A second sentinel for "not null" (`?col=not-null`). Not requested
  today; would be a small extension if needed later.
- URL aliases (`?col=is:null`, `?col=&include_null=true`). ADR-185
  rejects these.

## Verification

- `pytest backend/tests/test_nullable_filter.py` — unit tests green.
- `pytest backend/tests/test_diagrams_list_filter.py` — pre-existing
  tests still pass after refactor.
- `pytest backend/tests/test_element_package_membership.py` —
  exercises the helper end-to-end (ADR-184).
