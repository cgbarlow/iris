"""Three-valued nullable-ID query parameter convention (ADR-185).

Used by list endpoints that want to distinguish:

- "no filter" (URL omits the parameter)
- "match NULL" (URL uses the literal string ``"null"``)
- "match a specific id" (URL passes the id)

The historical precedent is ``list_diagrams.parent_package_id`` (v6.6.4);
``list_elements.package_id`` (ADR-184) adopts the same shape via this
helper so the convention is canonical.
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

    ``None`` (omitted) → ``("none",)``.
    Literal ``"null"`` (lowercase) → ``("is_null",)``.
    Any other string → ``("eq", value)``.
    """
    if value is None:
        return ("none",)
    if value == "null":
        return ("is_null",)
    return ("eq", value)
