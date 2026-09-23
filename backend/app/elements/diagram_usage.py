"""Batched diagram-usage counting for many elements (ADR-248, SPEC-248-A).

``get_element`` counts the live diagrams whose current version mentions an
element with ``dv.data LIKE '%<id>%'``: one substring scan of every
diagram's data per element. Doing that for N elements at once, in SQL or
in Python, still costs N scans of all diagram data. This module instead
walks each diagram's data once and collects every id it mentions.

Iris element ids are UUID strings, so each diagram's data is scanned once
for UUID-shaped substrings (overlapping matches included) and the result is
intersected with the requested ids. That costs O(total diagram bytes) per
request however many ids are asked about. An id that is not UUID-shaped
(none are generated today) falls back to a plain substring test, so the
answer is still exact for any id.

Semantics are those of ``LIKE '%<id>%'`` with two deliberate exceptions:
matching is case-sensitive (what PostgreSQL's LIKE does; SQLite's LIKE
folds ASCII case, but Iris always writes ids verbatim, so this only differs
if a diagram holds an id in a different letter case), and ``_``/``%`` in an
id are literal characters rather than wildcards.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

_HEX = "[0-9A-Fa-f]"
_UUID_SHAPE = f"{_HEX}{{8}}-{_HEX}{{4}}-{_HEX}{{4}}-{_HEX}{{4}}-{_HEX}{{12}}"
_UUID_ID = re.compile(_UUID_SHAPE)
# Zero-width lookahead so overlapping UUID-shaped substrings are all found.
_UUID_MENTIONS = re.compile(f"(?=({_UUID_SHAPE}))")


def count_diagram_usage(
    element_ids: Iterable[str],
    diagram_data: Iterable[str | None],
) -> dict[str, int]:
    """Return, per distinct id, how many of ``diagram_data`` mention it.

    ``diagram_data`` holds one entry per diagram (its current-version data
    as stored); ``None`` entries are ignored. Every requested id is present
    in the result, with 0 when no diagram mentions it.
    """
    counts = dict.fromkeys(element_ids, 0)
    if not counts:
        return counts
    uuid_ids = {eid for eid in counts if _UUID_ID.fullmatch(eid)}
    other_ids = [eid for eid in counts if eid not in uuid_ids]

    for data in diagram_data:
        if not data:
            continue
        if uuid_ids:
            for eid in uuid_ids.intersection(_UUID_MENTIONS.findall(data)):
                counts[eid] += 1
        for eid in other_ids:
            if eid in data:
                counts[eid] += 1
    return counts
