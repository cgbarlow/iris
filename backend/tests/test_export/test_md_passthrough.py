"""v6.2.0 (ADR-179): markdown renderer passthrough + normalisation."""

from __future__ import annotations

from app.export.renderers import markdown as md_renderer


def test_renders_utf8_bytes_with_trailing_newline() -> None:
    data, filename = md_renderer.render("Hello world", "Test")
    assert data == b"Hello world\n"
    assert filename.endswith(".md")


def test_normalises_crlf_to_lf() -> None:
    data, _ = md_renderer.render("a\r\nb\r\nc\r\n", "Test")
    assert data == b"a\nb\nc\n"


def test_trims_trailing_whitespace_per_line() -> None:
    data, _ = md_renderer.render("foo   \nbar  \n", "Test")
    assert data == b"foo\nbar\n"


def test_collapses_multiple_trailing_newlines_to_one() -> None:
    data, _ = md_renderer.render("text\n\n\n\n", "Test")
    assert data == b"text\n"


def test_empty_string_renders_to_single_newline() -> None:
    data, _ = md_renderer.render("", "Test")
    assert data == b"\n"


def test_none_input_renders_to_single_newline() -> None:
    data, _ = md_renderer.render(None, "Test")  # type: ignore[arg-type]
    assert data == b"\n"
