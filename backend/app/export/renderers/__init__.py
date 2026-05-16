"""Markdown / Docx / PDF renderers for the artefact pipeline.

Each renderer module exposes a single `render(markdown, title)`
function returning `(bytes, filename)`. Used by
`app/export/router.py` POST endpoints and the MCP `export_diagram` /
`render_markdown` tools (ADR-179, v6.2.0).
"""

from __future__ import annotations

from app.export.renderers import docx as docx_renderer
from app.export.renderers import markdown as md_renderer
from app.export.renderers import pdf as pdf_renderer
from app.export.renderers._common import slug_filename

__all__ = ["docx_renderer", "md_renderer", "pdf_renderer", "render", "slug_filename"]


def render(
    markdown: str, title: str, fmt: str,
) -> tuple[bytes, str, str]:
    """Dispatch to the appropriate renderer.

    Returns `(bytes, filename, mime_type)`.
    Raises ValueError on unsupported format.
    """
    if fmt == "md":
        data, filename = md_renderer.render(markdown, title)
        return data, filename, "text/markdown"
    if fmt == "docx":
        data, filename = docx_renderer.render(markdown, title)
        return (
            data, filename,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    if fmt == "pdf":
        data, filename = pdf_renderer.render(markdown, title)
        return data, filename, "application/pdf"
    msg = f"Unsupported render format {fmt!r}. Use 'md', 'docx', or 'pdf'."
    raise ValueError(msg)
