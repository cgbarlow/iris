"""Chunking for ``WHERE id IN (...)`` lookups (ADR-248, ADR-252).

``ID_CHUNK_SIZE`` ids per IN-list keeps a statement that binds each chunk
twice under SQLite's historical 999-variable limit (and far under
PostgreSQL's 32767).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

ID_CHUNK_SIZE = 400


def id_chunks(
    ids: Iterable[str | None], size: int = ID_CHUNK_SIZE,
) -> Iterator[list[str]]:
    """Yield the distinct non-empty ``ids``, in first-seen order, in chunks
    of at most ``size``."""
    ordered = list(dict.fromkeys(i for i in ids if i))
    for start in range(0, len(ordered), size):
        yield ordered[start:start + size]
