"""v6.2.0 (ADR-179, SPEC-179-A): md → pdf renderer tests.

Exercises `app/export/renderers/pdf.py` by rendering a markdown
fixture and asserting the bytes are a valid PDF (header check) and
contain the expected text content (extracted via pdfplumber, which
is already a backend dep).
"""

from __future__ import annotations

from io import BytesIO

import pdfplumber

from app.export.renderers import pdf as pdf_renderer


def _render(markdown: str, title: str = "Test") -> bytes:
    data, filename = pdf_renderer.render(markdown, title)
    assert filename.endswith(".pdf")
    assert data.startswith(b"%PDF"), "PDF must start with %PDF byte-header"
    return data


def _extract_text(pdf_bytes: bytes) -> str:
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def test_simple_markdown_produces_valid_pdf() -> None:
    data = _render("Hello world", title="Simple")
    text = _extract_text(data)
    assert "Hello world" in text
    assert "Simple" in text  # title


def test_headings_render_visibly() -> None:
    md = "# Top Level\n\nBody paragraph.\n\n## Subsection\n\nMore body.\n"
    data = _render(md, title="HeadingsDoc")
    text = _extract_text(data)
    assert "Top Level" in text
    assert "Body paragraph" in text
    assert "Subsection" in text
    assert "More body" in text


def test_filename_slug_derives_from_title() -> None:
    _, filename = pdf_renderer.render("body", title="Banana Monoculture")
    assert filename.startswith("banana-monoculture-")
    assert filename.endswith(".pdf")


def test_long_markdown_produces_multipage_pdf() -> None:
    # Generate ~3 A4 pages worth of paragraphs.
    body = "\n\n".join(
        f"Paragraph {i}: " + ("Lorem ipsum dolor sit amet. " * 20)
        for i in range(60)
    )
    data = _render(body, title="LongDoc")
    with pdfplumber.open(BytesIO(data)) as pdf:
        assert len(pdf.pages) >= 2, (
            f"Expected multi-page PDF, got {len(pdf.pages)} page(s)"
        )


def test_empty_markdown_still_produces_valid_pdf() -> None:
    data = _render("", title="EmptyBody")
    text = _extract_text(data)
    assert "EmptyBody" in text  # title still rendered
