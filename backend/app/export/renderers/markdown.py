"""Markdown renderer (passthrough + normalisation).

Markdown content is already markdown — this module just normalises
trailing whitespace and ensures a single trailing newline so the
output is byte-stable. Mirrors the existing `app/export/markdown.py`
bundle renderer's output shape.
"""

from __future__ import annotations

from app.export.renderers._common import slug_filename


def render(markdown: str, title: str) -> tuple[bytes, str]:
    """Return (bytes, filename) for a markdown artefact.

    Normalisation:
      - strip CRLF → LF
      - trim trailing whitespace per line
      - ensure exactly one trailing newline
    """
    if markdown is None:
        markdown = ""
    text = markdown.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    normalised = "\n".join(lines).rstrip("\n") + "\n"
    return normalised.encode("utf-8"), slug_filename(title, "md")
