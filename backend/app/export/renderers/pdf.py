"""Markdown → PDF renderer (ADR-179, v6.2.0).

Pipeline:
  1. Tokenise + render markdown to HTML via `markdown-it-py`.
  2. Wrap in a minimal HTML document with the Iris-branded CSS.
  3. Pass to `weasyprint.HTML(string=...).write_pdf()`.

Recipe modelled on Anthropic's `skills/pdf` (Apache 2.0). WeasyPrint
needs Pango / Cairo / GDK-PixBuf system libraries at runtime — the
Render image must include these (verified at the Phase 2 deploy
gate per `feedback_render_deploy_verification`).
"""

from __future__ import annotations

from html import escape
from pathlib import Path

from markdown_it import MarkdownIt

from app.export.renderers._common import slug_filename


_CSS_PATH = Path(__file__).parent / "styles" / "iris.css"


def _css() -> str:
    return _CSS_PATH.read_text(encoding="utf-8")


def _html_document(title: str, body_html: str) -> str:
    """Wrap rendered markdown HTML in a styled document shell."""
    css = _css()
    safe_title = escape(title or "Untitled")
    return (
        "<!DOCTYPE html>"
        "<html><head>"
        f"<meta charset='utf-8'><title>{safe_title}</title>"
        f"<style>{css}</style>"
        "</head><body>"
        f"<h1 class='iris-doc-title'>{safe_title}</h1>"
        f"{body_html}"
        "</body></html>"
    )


def render(markdown: str, title: str) -> tuple[bytes, str]:
    """Render markdown to a PDF bytes blob with Iris-branded styling."""
    md = MarkdownIt("commonmark", {"breaks": False, "html": False})
    body_html = md.render(markdown or "")
    html = _html_document(title, body_html)

    # Local import — weasyprint pulls in Pango/Cairo at import time
    # and the import is expensive. Defer until render() is called so
    # module import (and module-level test collection) is cheap.
    from weasyprint import HTML  # noqa: PLC0415

    pdf_bytes = HTML(string=html).write_pdf()
    return pdf_bytes, slug_filename(title, "pdf")
