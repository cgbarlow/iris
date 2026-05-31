# ADR-227: Two-layer aggregation engine cache

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-227 |
| **Initiative** | Make dashboards that use `aggregation` smart-markdown tokens fast to load |
| **Proposed By** | Engineering |
| **Date** | 2026-05-31 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** dashboards composed of smart-markdown bodies that
embed multiple `{{aggregation:<view>:…}}` tokens (ADR-225 / ADR-226) —
notably the GEANZ Capability Model Dashboard, which carries six
aggregation tokens pointing at three distinct aggregation_list views —
plus a hub-list section that references the same five capability-area
elements four times each across name / status / relationship_count /
diagram_usage_count tokens,

**facing** that each `aggregation` token in `smart_markdown.py` calls
`agg_engine.run(...)` from scratch — the same `(profile_id,
source_diagram_id)` pair is computed up to **5× per page render** — and
each `engine.run` costs 50–150 DB queries (one for the profile, one
for the source markdown, plus 37+ element-row reads for the GEANZ
rollup-source view). Element fetches in `smart_markdown.py` are
similarly un-memoised, so the same hub-element rows are re-read 20×
per render. The dashboard loads noticeably slowly. `AggregationResult.
source_versions` is already populated (`engine.py:619`, `:636`) but
read by nothing — a ready-made cache-invalidation key,

**we decided to** add two cache layers to the aggregation engine and
smart-markdown resolver, both keyed on version metadata that already
exists. **No new dependency, no schema change, no public API change**:

  - **Layer 1 — per-request memoisation via `ContextVar`.** A
    `ContextVar[dict[Any, Any] | None]` set at the entry of
    `compute_smart_markdown_content` and the aggregation_list synth
    hook in `diagrams/service.py`. Inside `agg_engine.run` and the
    element-fetch helpers in `smart_markdown.py`, the cache is
    consulted first; hits return immediately, misses compute then
    store. Removes 5× redundant engine runs and 4× redundant element
    reads within a single render.

  - **Layer 2 — process-wide version-keyed LRU.** A module-level
    `OrderedDict` LRU in a new `engine_cache.py` keyed by
    `(profile_id, source_diagram_id)`, value = the full
    `AggregationResult`. On lookup, the LRU is **revalidated** by
    re-fetching the profile (for its `updated_at`) and batch-fetching
    the `current_version` of every diagram in the cached
    `source_versions` (one `SELECT id, current_version FROM diagrams
    WHERE id IN (...)` query). If profile timestamp and every diagram
    version match → cache hit. Otherwise evict and recompute. Two
    validation queries replace the 50–150 query engine walk on hit.

**to achieve** a 60–70% wall-clock improvement on first dashboard load
(Layer 1 alone) and near-instant subsequent loads while the model is
unchanged (Layer 2 hit). Invalidation is **implicit** — cache keys
and validation tokens carry the version, so a write that bumps any
referenced diagram's `current_version` or the profile's `updated_at`
naturally invalidates without explicit eviction hooks.

**accepting** that:
- LRU is **per uvicorn worker** — on Render's multi-worker setup each
  worker has its own cache. First request per worker after restart
  hits the cold path. Acceptable for current scale; an explicit
  shared cache (Redis) is a clean follow-up if traffic grows.
- Race on concurrent cache miss is safe: both requests compute and
  both write the same `AggregationResult`; last write wins; no
  corruption.
- A code change that alters the shape of `AggregationResult` requires
  a worker restart to invalidate stale entries. Same restart is
  already part of any backend release rollout — no explicit
  cache-bust hook needed.
- The `source_versions` dict only includes diagrams the engine
  actually read. Verified at `engine.py:619, 636` — every diagram
  touched by the outer or inner walk is recorded. No silently-skipped
  reads.
- Smart-markdown **content-level** caching (caching the resolved
  `data.content` of an entire smart_markdown diagram keyed on every
  entity it touches) is out of scope. The engine-level cache hits
  the dominant cost path; a content-level cache would need a
  dependency tracker for elements / packages / sets too and is a
  larger surface change.
- ETag/304 on `/api/diagrams/<id>` is out of scope (clean follow-up
  using the same `source_versions` for the ETag value).

## Rejected alternatives

- **Cache the resolved `data.content` directly** — biggest possible
  win, but invalidation requires tracking every entity the resolver
  touches (each `{{element:…}}` token). That dependency tracker is
  real code with real edge cases (deleted entities, renamed
  diagrams). Engine-level cache covers ~80% of the cost at a tiny
  fraction of the complexity.
- **Redis / external cache** — overkill at current scale, adds a
  dependency, requires ops setup on Render. In-process LRU is
  sufficient until single-worker hit rate stops being acceptable.
- **`functools.lru_cache`** — doesn't support async-native code and
  has no hook for cache-entry revalidation. Manual `OrderedDict` is
  ~30 lines and gives us exactly the validation hook we need.
- **Explicit invalidation hooks on element/diagram/profile writes** —
  bigger code surface and harder to keep right than version-keyed
  validation. The version columns already exist; piggyback on them.

## Dependencies

- Builds on ADR-212 (aggregation engine), ADR-213 (aggregation_list
  synth-on-read), ADR-225 / ADR-226 (aggregation smart-markdown
  tokens). No new dependencies.

## Consequences

- Spec: SPEC-227-A.
- No migration, no MCP/CLI write-surface impact (Protocol §14
  unaffected), no behavioural change at the API boundary.
- Dashboards composed of aggregation tokens load 60–70% faster on
  first hit and near-instantly on subsequent hits.
- LRU size hard-coded to 512 entries. Env-tunable in a follow-up if
  usage shows pressure.
