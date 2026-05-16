"""Shared helpers for the renderer modules (avoid circular imports)."""

from __future__ import annotations

import re
import uuid


def slug_filename(title: str, extension: str) -> str:
    """Produce a kebab-cased filename with a short UUID suffix.

    Title `"Banana Monoculture DoView"` + extension `"docx"` →
    `"banana-monoculture-doview-9f2c.docx"`. The UUID suffix avoids
    collisions when the same title is rendered multiple times.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", (title or "untitled").lower()).strip("-")
    if not slug:
        slug = "artefact"
    short_uuid = uuid.uuid4().hex[:4]
    return f"{slug}-{short_uuid}.{extension}"
