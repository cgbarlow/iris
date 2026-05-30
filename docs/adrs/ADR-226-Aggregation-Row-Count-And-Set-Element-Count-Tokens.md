# ADR-226: Smart-markdown `aggregation:…:row_count` and `set:…:element_count` tokens

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-226 |
| **Initiative** | Make the remaining dashboard "snapshot" cells (set totals, aggregation totals) live |
| **Proposed By** | Engineering |
| **Date** | 2026-05-30 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** a dashboard that already uses smart-markdown tokens
for per-element / per-diagram / per-group counts (ADR-222 / ADR-223 /
ADR-225) but still has hand-typed cells for two common shapes — *total
elements in a set* and *total rows in an aggregation* — so the dashboard
tells a half-live story,

**facing** that ADR-225's ``aggregation`` token exposes ``group_count``
but no aggregate-level total, and there is no token at all for "how
many elements in this set". The Coverage snapshot table on the GEANZ
Dashboard still hand-types **50** (set total) and **37**
(``ArchiMate_Capability`` count, which equals "rows in the Status or
Maturity rollup"). Drift is silent and visible — adding a capability
moves the dashboard out of sync without warning,

**we decided to** add two minimal token field-specs:

  - ``{{aggregation:<view_id>:row_count[:raw]}}`` — total rows across
    every group in the aggregation_list view's profile output.
  - ``{{set:<id>:element_count[:raw]}}`` — live count of non-deleted
    elements in the set.

Both compose with the ADR-224 ``:raw`` modifier for Mermaid use. The
``aggregation:row_count`` value reuses ``AggregationResult.row_count``
already exposed via ``/api/aggregate`` and MCP — no new traversal,
just a new field-spec on the existing entity type. The
``set:element_count`` value is a straight ``SELECT COUNT(*)`` against
``elements`` filtered by ``set_id`` and ``is_deleted = 0`` — mirrors
the existing ``set:name`` resolver shape.

**to achieve** four more live cells on the GEANZ Dashboard's Coverage
snapshot (Total elements, ArchiMate_Capability stereotype, Maturity
values populated (demo), Orphan capabilities — the last via an
``aggregation:…:group_count:0`` over a new orphan-rollup profile,
authoring-only). One small composable token surface, zero schema
change.

**accepting** that:
- ``aggregation:row_count`` doesn't filter — it's the total across all
  groups including ``"(no group)"`` rows. That matches how
  ``AggregationResult.row_count`` is computed; authors who want a
  subset use ``group_count`` instead. Documented, not engineered
  around.
- ``set:element_count`` counts EVERY non-deleted element regardless
  of stereotype/type. The GEANZ "50 = capabilities + themes" cell is
  the right number to render with this token; if a future cell wants
  "capabilities only" we already have ``aggregation:row_count`` over
  the rollup-source view (which has 37 capability tokens) — two
  paths, two intents.
- Re-running the aggregation engine on every smart-markdown resolve
  is the same cost as opening the rollup view. Same trade-off as
  ADR-225, and the same future caching solution applies to both.

## Rejected alternatives

- **Add a new top-level ``count`` token form** (``{{count:elements:set=<id>}}``
  etc.). More general, much larger surface, doesn't match how the
  other tokens already encode "entity + field-spec". The two narrow
  tokens here compose with the existing grammar instead of replacing
  it.
- **Expose set/diagram/package-level metrics via element-level token
  filters** (``{{element:*:meta:status:count}}``). Wildcard token
  shapes have never existed in smart-markdown and would force a
  whole new parser branch.
- **Compute the totals client-side from `group_count` sums in
  Mermaid blocks.** Mermaid doesn't do arithmetic in values. Same
  reason ``group_count`` had to be a token: the renderer can't sum.

## Dependencies

- Composes with ADR-224 ``:raw`` and ADR-225 ``aggregation`` entity
  type. No schema change, no MCP/CLI write surface change (Protocol
  §14 unaffected).

## Consequences

- Spec: SPEC-226-A.
- Dashboard's Coverage snapshot table can go from 2 live cells (the
  ADR-225 Approved / Proposed) to 6 live cells.
- Future "snapshot" cells on other dashboards can also use the new
  tokens directly.
