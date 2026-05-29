# ADR-223: Element metadata, EA tagged-value, and computed-count tokens

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-223 |
| **Initiative** | Expose element metadata, Sparx EA tagged values, and computed counts to smart-markdown and aggregation |
| **Proposed By** | Engineering |
| **Date** | 2026-05-29 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** wanting to build dashboards and rollups over the
**actual model state** in Iris — Status (Approved/Proposed), Sparx EA
tagged values (Maturity, Last Review Date, etc.), connection density
(`relationship_count`), and reuse (`diagram_usage_count`) — rather than
hand-typed numbers; and finding that the smart-markdown resolver
(ADR-205/210) only walks ``element.data.attributes`` and the aggregation
engine (ADR-212) only resolves attribute paths,

**facing** that the data we want lives elsewhere on the element row:
- `element.metadata` carries `status`, `stereotype`, `author`, dates, and
  — for Sparx imports — a `tagged_values` array of `{property, value}`
  pairs. EA encodes its template defaults / option lists with a
  ``#NOTES#<description>`` suffix on the value, so a populated maturity
  level reads as ``"3#NOTES#Values: 0..5..."`` and an unset one reads as
  ``"-#NOTES#..."``.
- `relationship_count` and `diagram_usage_count` are derived counts the
  element service already computes, but they're inaccessible to
  smart-markdown / aggregation,

**we decided to** add a small token-surface extension on `element`
tokens — three new field-spec families, accepted by both the
smart-markdown resolver (field-spec `:`-form) and the aggregation engine
(path `/`-form for `value_attribute_path` / `bucket_attribute_path`, and
dot-form for `group_by`):

| Concept | Smart-markdown field-spec | Engine value path | Engine group_by |
|---|---|---|---|
| Metadata key | `meta:<key>` | `meta/<key>` | `element.meta.<key>` |
| EA tagged value | `tag:<property>` | `tag/<property>` | `element.tag.<property>` |
| Relationship count | `relationship_count` | `relationship_count` | `element.relationship_count` |
| Diagram usage count | `diagram_usage_count` | `diagram_usage_count` | `element.diagram_usage_count` |

**to achieve** a single, small token-surface change that unlocks live
rollups of *all* of: Status distribution by zone, hub elements ranked by
`relationship_count`, orphan lists (`diagram_usage_count == 0`),
documentation coverage (description present), and Maturity rollups
(populated `Current Maturity Level` tagged values). All of it via the
existing aggregation engine, with no engine algorithm changes — only
new resolvers behind the same `_resolve_token_value` / `_resolve_group_value`
abstractions.

**accepting** that:
- The EA tagged-value resolver **strips the ``#NOTES#`` suffix** and
  treats the empty string and the literal ``"-"`` (EA's "unset"
  placeholder) as None — so unset values render as strikethrough in
  smart-markdown and are skipped under `skip_blank_values: true` in
  aggregation. Populated values pass through as-is.
- `diagram_usage_count` uses the same `data LIKE '%<id>%'` substring
  match as `elements/service.get_element` — so a smart-markdown source
  that references an element via a token counts as a "usage" of that
  element. This is consistent with the existing counter; we did not
  redefine the metric.
- This is a **read-only surface** addition: no migration, no surface
  parity impact (no new write op), no aggregation algorithm change.
- Caching: each resolution does its own SQL read. For dashboards over
  ~50 elements the round-trip is negligible; if a future profile fans
  out to thousands, a per-run cache (mirroring the existing
  `element_cache` in `_format_output`) is the next step.

## Rejected alternatives

- **Materialise the values into `element.data.attributes`.** A copy that
  goes stale. The engine would work today against them, but maintaining
  parity with the source-of-truth on the element row is extra plumbing.
- **A bespoke "model health" report endpoint.** Hard-codes the questions
  we asked today and gives the user no way to ask new ones. Tokens
  compose with smart-markdown and aggregation, so any new question is a
  new profile or markdown source, not new code.

## Dependencies

- Builds on ADR-205/210 (smart-markdown tokens & overrides), ADR-209
  (`iris://` link wrapping), ADR-212/213 (aggregation engine and the
  `aggregation_list` synth-on-read surface), ADR-221 (`detail_diagram_id`
  is a `meta:` candidate — currently a column, but the pattern is the
  same), and ADR-222 (the `element_count` precedent for non-attribute
  token resolution).

## Consequences

- Spec: SPEC-223-A.
- New profiles authorable for: Status rollup, hub list, orphan list,
  maturity rollup (when values are populated), documentation coverage
  (via a follow-up "is-empty" predicate if wanted later).
