"""Tests for UML visibility prefix formatting (ADR-086)."""

import pytest

from app.import_sparx.converter import format_uml_visibility


class TestFormatUmlVisibility:
    """Unit tests for the format_uml_visibility utility."""

    def test_public(self) -> None:
        assert format_uml_visibility("Public") == "+"

    def test_private(self) -> None:
        assert format_uml_visibility("Private") == "-"

    def test_protected(self) -> None:
        assert format_uml_visibility("Protected") == "#"

    def test_package(self) -> None:
        assert format_uml_visibility("Package") == "~"

    def test_none_defaults_to_public(self) -> None:
        assert format_uml_visibility(None) == "+"

    def test_empty_string_defaults_to_public(self) -> None:
        assert format_uml_visibility("") == "+"

    def test_unknown_defaults_to_public(self) -> None:
        assert format_uml_visibility("UnknownScope") == "+"
