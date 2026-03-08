"""Tests for note label deduplication (ADR-088).

Verifies that strip_label_from_note() removes the label prefix from
note text to prevent the title appearing twice in NoteNode rendering.
"""

from __future__ import annotations

from app.import_sparx.service import strip_label_from_note


class TestStripLabelFromNote:
    """Verify label prefix is stripped from note body text."""

    def test_strips_label_with_crlf(self) -> None:
        label = "Feature Properties"
        note = "Feature Properties\r\n\r\nAttributes and associations..."
        result = strip_label_from_note(label, note)
        assert result == "Attributes and associations..."

    def test_strips_label_with_lf(self) -> None:
        label = "Feature Properties"
        note = "Feature Properties\n\nAttributes and associations..."
        result = strip_label_from_note(label, note)
        assert result == "Attributes and associations..."

    def test_noop_when_label_differs(self) -> None:
        label = "Different Label"
        note = "Feature Properties\r\n\r\nAttributes and associations..."
        result = strip_label_from_note(label, note)
        assert result == note

    def test_noop_when_label_is_substring_not_prefix(self) -> None:
        label = "Properties"
        note = "Feature Properties\r\nSome text"
        result = strip_label_from_note(label, note)
        assert result == note

    def test_strips_leading_blank_lines_after_label(self) -> None:
        label = "Title"
        note = "Title\r\n\r\n\r\nBody text here"
        result = strip_label_from_note(label, note)
        assert result == "Body text here"

    def test_single_line_note_matching_label(self) -> None:
        """If note is exactly the label with no line break, return unchanged."""
        label = "Feature Properties"
        note = "Feature Properties"
        result = strip_label_from_note(label, note)
        assert result == note
