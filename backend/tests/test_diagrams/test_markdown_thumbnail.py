"""Tests for markdown-notation thumbnail generation (v6.17.6, issue #205).

`generate_svg_from_diagram_data` learned in v6.17.6 to render markdown
views (smart_markdown / text / dynamic_list) as plain-text SVG previews
instead of the empty "Empty" placeholder. These cover the three types
plus heading rendering and token-stripping behaviour.
"""

from __future__ import annotations

from app.diagrams.thumbnail import (
    _resolved_to_plain_text,
    generate_svg_from_diagram_data,
)


def test_smart_markdown_preview_contains_heading() -> None:
    data = {"markdown_source": "# Pork mince recipe\n\n500g pork mince"}
    svg = generate_svg_from_diagram_data(data, "smart_markdown")
    assert "Pork mince recipe" in svg
    assert "500g pork mince" in svg
    assert "Empty" not in svg


def test_smart_markdown_strips_resolver_tokens() -> None:
    """Tokens like `{{element:GUID:name}}` are noise in a thumbnail —
    they should be replaced with a placeholder, not rendered raw."""
    data = {
        "markdown_source": (
            "# Recipe\n"
            "Use 500g of {{element:abc-123:name}} from your pantry."
        ),
    }
    svg = generate_svg_from_diagram_data(data, "smart_markdown")
    assert "abc-123" not in svg
    assert "{{element" not in svg
    # Placeholder substituted in.
    assert "[…]" in svg or "Use 500g" in svg


def test_text_uses_data_content() -> None:
    data = {"content": "## Notes\n- Buy bread\n- Pick up milk"}
    svg = generate_svg_from_diagram_data(data, "text")
    assert "Notes" in svg
    assert "Buy bread" in svg


def test_dynamic_list_shows_source_mode() -> None:
    data = {"source": "package_elements", "show_description": True}
    svg = generate_svg_from_diagram_data(data, "dynamic_list")
    assert "Dynamic list" in svg
    assert "package_elements" in svg
    assert "yes" in svg  # show_description toggle rendered


def test_empty_markdown_renders_placeholder_not_empty_label() -> None:
    """Empty markdown still produces a useful tile (not the literal
    `Empty` text used for visual diagrams with no nodes)."""
    data = {"markdown_source": ""}
    svg = generate_svg_from_diagram_data(data, "smart_markdown")
    # `(empty)` parens are the marker used in `_markdown_preview_lines`.
    assert "(empty)" in svg
    # Sanity: still wrapped in an SVG.
    assert svg.startswith("<svg")
    assert svg.rstrip().endswith("</svg>")


def test_markdown_preview_truncates_long_lines() -> None:
    long = "x" * 200
    data = {"content": long}
    svg = generate_svg_from_diagram_data(data, "text")
    # Per `_markdown_preview_lines`, each line is capped at 60 chars.
    assert "x" * 200 not in svg
    assert "x" * 60 in svg


def test_markdown_preview_caps_line_count() -> None:
    """Only first 6 non-blank lines are rendered."""
    source = "\n".join(f"line{i}" for i in range(20))
    data = {"content": source}
    svg = generate_svg_from_diagram_data(data, "text")
    assert "line0" in svg
    assert "line5" in svg
    assert "line6" not in svg
    assert "line19" not in svg


def test_resolved_to_plain_text_strips_link_syntax() -> None:
    """The smart_markdown resolver wraps each token as
    `[value](iris://... "name")`. For the thumbnail we want just the
    rendered text, no markdown link noise."""
    resolved = 'Use 500g of [pork mince](iris://element/abc-123 "Pork Mince") from pantry.'
    assert _resolved_to_plain_text(resolved) == "Use 500g of pork mince from pantry."


def test_resolved_to_plain_text_unwraps_strikethrough_unresolvable() -> None:
    """The resolver wraps unresolvable tokens in `~~...~~`. Drop the
    markers so the thumbnail isn't visually noisy."""
    resolved = "Missing: ~~{{element:gone:name}}~~ here."
    out = _resolved_to_plain_text(resolved)
    assert "~~" not in out
    assert "{{element:gone:name}}" in out  # raw token surfaced as fallback


def test_resolved_to_plain_text_replaces_img_with_placeholder() -> None:
    """Inline `<img>` HTML returned by the image resolver can't render
    in the cairosvg thumbnail; substitute a short placeholder."""
    resolved = 'Photo: <img src="data:image/png;base64,abc" alt="x"> below.'
    out = _resolved_to_plain_text(resolved)
    assert "<img" not in out
    assert "[image]" in out


def test_visual_diagram_still_uses_nodes_path() -> None:
    """Regression: visual diagram types still use the existing
    node/edge SVG generator, not the markdown preview."""
    data = {"nodes": [{"id": "n1", "data": {"label": "Hello"}, "position": {"x": 0, "y": 0}}]}
    svg = generate_svg_from_diagram_data(data, "component")
    assert "Hello" in svg
    assert "Dynamic list" not in svg
