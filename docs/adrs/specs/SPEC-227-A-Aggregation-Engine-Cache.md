# SPEC-227-A: Two-layer aggregation engine cache

Implements **[ADR-227](../ADR-227-Aggregation-Engine-Cache.md)**.

## Module layout

New file `backend/app/aggregation/engine_cache.py`:

```python
# Public surface (consumed by engine.py + smart_markdown.py + service.py)
request_cache: ContextVar[dict[Any, Any] | None]      # Layer 1
set_request_cache() -> contextlib.AbstractContextManager
def lru_get(key) -> AggregationResult | None
def lru_put(key, value: AggregationResult) -> None
def lru_clear() -> None        # tests only
def lru_size() -> int          # tests only
LRU_MAXSIZE = 512
```

The `request_cache` ContextVar holds either `None` (no active request
scope) or a plain `dict` used as a per-request scratch cache. Callers
do **not** mutate it directly — they go through the helpers
`lookup_request(key)` and `store_request(key, value)`, which no-op
when the ContextVar is `None`.

`set_request_cache()` returns a context manager that:
- on enter: tokens-and-sets a fresh `{}` on `request_cache`,
- on exit: restores the previous value via `request_cache.reset(token)`.

## Layer 1 — per-request memoisation (ContextVar)

Entry points that wrap the active context:

- `backend/app/diagrams/smart_markdown.py::compute_smart_markdown_content`
  — wrap the entire body in `with set_request_cache():`.
- `backend/app/diagrams/service.py::_maybe_synthesise_content`
  (aggregation_list branch) — wrap the engine call (and the existing
  content-mutation block) in `with set_request_cache():`.

Cache key conventions (kept in `engine_cache.py` as constants):
- `("agg", profile_id, source_diagram_id)` → `AggregationResult`
- `("element_row", element_id)` → `(name, package_name, data)` tuple
  returned by `_read_element_data` / `_fetch_element_field` shared
  read
- `("element_meta", element_id)` → `dict` returned by
  `_fetch_element_metadata_dict`
- `("rel_count", element_id)` → `int`
- `("usage_count", element_id)` → `int`
- `("display_name", entity_type, entity_id)` → `str | None`

The helpers in `smart_markdown.py` (`_read_element_data` — currently
inline inside `engine.py`; `_fetch_element_relationship_count`;
`_fetch_element_diagram_usage_count`; `_fetch_element_metadata_dict`;
`_fetch_entity_display_name`) gain a one-line consult-then-store at
the top of each function. The wrappers no-op when `request_cache.get()
is None`.

## Layer 2 — process-wide LRU

`engine_cache._AggregationLRU`:

```python
class _AggregationLRU:
    def __init__(self, maxsize: int = LRU_MAXSIZE) -> None:
        self._data: OrderedDict[tuple[str, str], AggregationResult] = OrderedDict()
        self._maxsize = maxsize

    def get(self, key) -> AggregationResult | None:
        v = self._data.get(key)
        if v is not None:
            self._data.move_to_end(key)
        return v

    def put(self, key, value: AggregationResult) -> None:
        self._data[key] = value
        self._data.move_to_end(key)
        while len(self._data) > self._maxsize:
            self._data.popitem(last=False)

    def evict(self, key) -> None:
        self._data.pop(key, None)

    def clear(self) -> None:
        self._data.clear()

    def __len__(self) -> int:
        return len(self._data)
```

Module-level singleton `_LRU = _AggregationLRU()`.

Validation helper (also in `engine_cache.py`):

```python
async def revalidate(
    db: DatabasePort, cached: AggregationResult, *, profile_id: str,
) -> bool:
    """Return True iff the cached result is still consistent with the
    live profile.updated_at and the current_version of every diagram
    in cached.source_versions."""
    # one query: profile.updated_at
    # one query: SELECT id, current_version FROM diagrams
    #            WHERE id IN (...) AND is_deleted = 0
    ...
```

## engine.py changes

`engine.py::run` is split:

```python
async def run(db, *, profile_id, source_diagram_id) -> AggregationResult:
    key = ("agg", profile_id, source_diagram_id)

    # Layer 1
    req = engine_cache.request_cache.get()
    if req is not None:
        hit = req.get(key)
        if hit is not None:
            return hit

    # Layer 2
    cached = engine_cache.lru_get((profile_id, source_diagram_id))
    if cached is not None:
        if await engine_cache.revalidate(db, cached, profile_id=profile_id):
            if req is not None:
                req[key] = cached
            return cached
        # Stale — evict so the next miss doesn't immediately revalidate.
        engine_cache.lru_evict((profile_id, source_diagram_id))

    # Cold path
    result = await _run_uncached(
        db, profile_id=profile_id, source_diagram_id=source_diagram_id,
    )
    engine_cache.lru_put((profile_id, source_diagram_id), result)
    if req is not None:
        req[key] = result
    return result
```

The current body of `run` is renamed `_run_uncached` (unchanged
semantics).

## Acceptance criteria

1. Two distinct `{{aggregation:<view>:group_count:Approved}}` and
   `{{aggregation:<view>:row_count}}` tokens in the same
   smart_markdown body trigger **one** `_run_uncached` call per
   render.
2. Second `compute_smart_markdown_content` call on the same diagram
   (with no underlying data changes) returns the same content and
   never enters `_run_uncached`.
3. Bumping the source diagram's `current_version` causes the next
   `engine.run` to enter `_run_uncached` (cache miss after
   revalidation).
4. Updating the profile (which bumps `aggregation_profiles.updated_at`)
   causes the next `engine.run` to enter `_run_uncached`.
5. LRU never grows past `LRU_MAXSIZE`; oldest entries evicted FIFO.
6. Two concurrent `compute_smart_markdown_content` invocations do not
   share `request_cache` state (ContextVar isolation).
7. `_read_element_data` (and the other element-fetch helpers) are
   each called at most once per `(helper, entity_id)` tuple per
   render — regardless of how many tokens reference the same
   element.

## Tests

`backend/tests/test_aggregation/test_engine_cache.py` (new):

- `test_per_request_dedupes_engine_calls` — patch `_run_uncached`
  with a `mock.AsyncMock`; render a smart_markdown body with two
  `group_count` + one `row_count` token on the same view; assert
  the mock's `call_count == 1`.
- `test_lru_hit_when_sources_unchanged` — render, then render again;
  assert `_run_uncached` is called once across both renders, but
  `revalidate` is called twice (once per Layer-2 lookup).
- `test_lru_miss_when_source_version_bumps` — render; bump the
  source diagram's `current_version` via direct DB update; render
  again; assert `_run_uncached` is called twice.
- `test_lru_miss_when_profile_updates` — render; bump
  `aggregation_profiles.updated_at` via direct DB update; render
  again; assert `_run_uncached` is called twice.
- `test_lru_respects_maxsize` — force `LRU_MAXSIZE = 3` via env or
  monkeypatch, write 5 distinct keys, assert `lru_size() == 3` and
  the two oldest entries are gone.
- `test_request_cache_isolated_between_requests` — two tasks under
  `asyncio.gather`, each with its own `set_request_cache()`, write
  the same key to their dicts with different values; assert no
  cross-pollination.

`backend/tests/test_diagrams/test_smart_markdown.py` (extend):

- `test_element_row_memoised_within_one_render` — body with
  `{{element:X:name}}`, `{{element:X:relationship_count}}`,
  `{{element:X:diagram_usage_count}}`; patch `_read_element_data` (or
  whatever helper the implementation chooses); assert it's called
  exactly once.

Regression: the existing 91 tests
(`tests/test_diagrams/test_smart_markdown.py` + `tests/test_aggregation/`)
must remain green.

## Verification (post-deploy)

```sh
for i in 1 2 3; do
  time curl -s -o /dev/null \
    https://iris-api-gtb3.onrender.com/api/diagrams/28f077ad-9693-42d1-be10-c469252885ec
done
```

Call 1 = cold (LRU populated). Calls 2 & 3 = warm (LRU hit, two
validation queries). Record wall-clock in PR comment.

Correctness check: edit a capability's `metadata.status` via MCP;
reload the dashboard; confirm the Status pie / table update on the
next page load (proves cache invalidation works).

## Constants

```python
LRU_MAXSIZE = 512    # entries; rule of thumb 100 KB/entry → ~50 MB cap
```
