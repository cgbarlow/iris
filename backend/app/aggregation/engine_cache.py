"""Two-layer cache for the aggregation engine and smart-markdown
resolvers (ADR-227, SPEC-227-A).

Layer 1 — per-request memoisation via a `ContextVar`. Callers wrap
their entry point in `set_request_cache()` (a context manager) and any
function deeper in the call tree can opportunistically dedupe work
through `lookup_request` / `store_request`. When the ContextVar is
unset the helpers are a no-op, so the same code paths work outside a
cache scope (tests, scripts).

Layer 2 — process-wide LRU keyed by `(profile_id, source_diagram_id)`,
value = the cached `AggregationResult`. On lookup we revalidate the
cached entry against:
  - the bound profile's `updated_at`
  - the `current_version` of every diagram in
    `AggregationResult.source_versions` (already populated by the
    engine, never previously consumed).

Mismatch → evict + recompute. Match → return the cached result. Two
SQL queries to validate vs the 50–150 the engine would otherwise
re-run.

Both layers are per-process. Multiple uvicorn workers each maintain
their own copy; that is acceptable at current Iris scale. Replacing
the in-process LRU with a shared Redis is a clean follow-up if cold
hit rates ever become a problem.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any

from app.aggregation.models import AggregationResult

if TYPE_CHECKING:
    from app.db.adapter import DatabasePort


# ─────────────────────────────────────────────────────────────────────
# Layer 1 — per-request memoisation
# ─────────────────────────────────────────────────────────────────────


# A `dict` keyed by a tuple of (kind, *id_parts). When None the helpers
# below short-circuit. Set by `set_request_cache()` at request entry,
# reset by the context manager on exit.
request_cache: ContextVar[dict[Any, Any] | None] = ContextVar(
    "iris_smart_markdown_request_cache", default=None,
)


@contextmanager
def set_request_cache() -> Iterator[dict[Any, Any]]:
    """Context manager: install a fresh per-request memo dict, restore
    the previous value on exit."""
    cache: dict[Any, Any] = {}
    token = request_cache.set(cache)
    try:
        yield cache
    finally:
        request_cache.reset(token)


def lookup_request(key: Any) -> Any | _Missing:
    """Return the cached value for `key`, or `MISSING` if not present.
    A bare `None` value is a valid hit; callers MUST compare against
    `MISSING` (or `is MISSING`) rather than truthiness."""
    cache = request_cache.get()
    if cache is None:
        return MISSING
    if key not in cache:
        return MISSING
    return cache[key]


def store_request(key: Any, value: Any) -> None:
    cache = request_cache.get()
    if cache is None:
        return
    cache[key] = value


# Sentinel used by `lookup_request` to distinguish "not cached" from
# "cached as None" (which is a real value for missing entities).
class _Missing:
    __slots__ = ()
    def __repr__(self) -> str: return "MISSING"


MISSING = _Missing()


# ─────────────────────────────────────────────────────────────────────
# Layer 2 — process-wide version-keyed LRU
# ─────────────────────────────────────────────────────────────────────


LRU_MAXSIZE = 512  # ADR-227: hard-coded for now; env-tunable in a follow-up.


class _AggregationLRU:
    """OrderedDict-backed LRU. Keys = `(profile_id, source_diagram_id)`,
    values = `AggregationResult`. Not thread-safe; backed by the GIL +
    asyncio single-task-at-a-time semantics. Race on concurrent miss
    is safe (both writers produce identical content; last write wins)."""

    def __init__(self, maxsize: int = LRU_MAXSIZE) -> None:
        self._data: OrderedDict[tuple[str, str], AggregationResult] = OrderedDict()
        self._maxsize = maxsize

    def get(self, key: tuple[str, str]) -> AggregationResult | None:
        v = self._data.get(key)
        if v is not None:
            self._data.move_to_end(key)
        return v

    def put(self, key: tuple[str, str], value: AggregationResult) -> None:
        self._data[key] = value
        self._data.move_to_end(key)
        while len(self._data) > self._maxsize:
            self._data.popitem(last=False)

    def evict(self, key: tuple[str, str]) -> None:
        self._data.pop(key, None)

    def clear(self) -> None:
        self._data.clear()

    @property
    def maxsize(self) -> int:
        return self._maxsize

    def set_maxsize(self, n: int) -> None:
        """Test-only escape hatch — lets the test suite shrink the LRU
        to verify eviction behaviour without filling 512 slots."""
        self._maxsize = n
        while len(self._data) > self._maxsize:
            self._data.popitem(last=False)

    def __len__(self) -> int:
        return len(self._data)


_LRU = _AggregationLRU()


def lru_get(key: tuple[str, str]) -> AggregationResult | None:
    return _LRU.get(key)


def lru_put(key: tuple[str, str], value: AggregationResult) -> None:
    _LRU.put(key, value)


def lru_evict(key: tuple[str, str]) -> None:
    _LRU.evict(key)


def lru_clear() -> None:
    _LRU.clear()


def lru_size() -> int:
    return len(_LRU)


def lru_set_maxsize(n: int) -> None:
    _LRU.set_maxsize(n)


# ─────────────────────────────────────────────────────────────────────
# Revalidation — used by engine.run on a Layer-2 hit
# ─────────────────────────────────────────────────────────────────────


async def revalidate(
    db: DatabasePort, cached: AggregationResult, *, profile_id: str,
    profile_updated_at: str,
) -> bool:
    """Return True iff the cached result is still consistent with the
    live profile `updated_at`, the `current_version` of every diagram
    in `cached.source_versions`, AND (ADR-227 v6.39.2 fix) the
    `current_version` of every element in `cached.element_versions`.

    Up to three SQL queries: the caller has already fetched the
    profile and passes its `updated_at`; this function batches one
    query for the referenced diagrams and (if the cached result
    walked any elements) one query for the referenced elements.
    """
    cached_profile_updated_at = cached.profile_updated_at
    if cached_profile_updated_at is None:
        # Cached pre-revalidation field — refuse to trust it.
        return False
    if cached_profile_updated_at != profile_updated_at:
        return False
    if not cached.source_versions:
        # Nothing to validate against — refuse to trust.
        return False

    # ── Diagram-level revalidation (covers source + outer-step refs) ──
    diag_ids = list(cached.source_versions.keys())
    placeholders = ",".join(["?"] * len(diag_ids))
    cursor = await db.execute(
        "SELECT id, current_version FROM diagrams "
        f"WHERE id IN ({placeholders}) AND is_deleted = 0",  # noqa: S608
        tuple(diag_ids),
    )
    rows = await cursor.fetchall()
    live_diagrams = {r[0]: r[1] for r in rows}
    if len(live_diagrams) != len(diag_ids):
        # Some referenced diagram was soft-deleted.
        return False
    for did, ver in cached.source_versions.items():
        if live_diagrams.get(did) != ver:
            return False

    # ── Element-level revalidation (ADR-227 v6.39.2 fix) ───────────────
    # The diagram-level check above misses pure element edits — e.g. a
    # status flip in `metadata.status`. The engine now records every
    # touched element's current_version in `element_versions`; verify
    # them all here. Older cached results have an empty dict and skip
    # straight to "valid" (safe: they were computed before the engine
    # tracked elements, but the diagram check still gates them).
    if cached.element_versions:
        elem_ids = list(cached.element_versions.keys())
        placeholders = ",".join(["?"] * len(elem_ids))
        cursor = await db.execute(
            "SELECT id, current_version FROM elements "
            f"WHERE id IN ({placeholders}) AND is_deleted = 0",  # noqa: S608
            tuple(elem_ids),
        )
        rows = await cursor.fetchall()
        live_elements = {r[0]: r[1] for r in rows}
        if len(live_elements) != len(elem_ids):
            # Some referenced element was soft-deleted.
            return False
        for eid, ver in cached.element_versions.items():
            if live_elements.get(eid) != ver:
                return False

    return True
