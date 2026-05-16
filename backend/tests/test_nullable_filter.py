"""Unit tests for the shared nullable-filter parser (ADR-185 / SPEC-185-A).

Three-valued semantics:

- ``None`` (omitted)  → ``("none",)``
- ``"null"`` (literal) → ``("is_null",)``
- any other string    → ``("eq", value)``
"""

from __future__ import annotations

from app.common.nullable_filter import parse_nullable_id


class TestParseNullableId:
    """Three branches plus a couple of guard cases."""

    def test_none_means_no_filter(self) -> None:
        assert parse_nullable_id(None) == ("none",)

    def test_lowercase_null_literal_means_is_null(self) -> None:
        assert parse_nullable_id("null") == ("is_null",)

    def test_uuid_string_means_eq(self) -> None:
        assert parse_nullable_id("abc-123") == ("eq", "abc-123")

    def test_uppercase_NULL_is_treated_as_value(self) -> None:
        """Only the exact lowercase ``"null"`` triggers IS NULL.
        Avoids ambiguity for ids that happen to use NULL casing."""
        assert parse_nullable_id("NULL") == ("eq", "NULL")

    def test_empty_string_is_treated_as_value(self) -> None:
        """Empty string isn't the IS-NULL sentinel; the caller may want
        to validate further but the parser stays simple."""
        assert parse_nullable_id("") == ("eq", "")
