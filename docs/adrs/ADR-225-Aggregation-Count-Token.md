# ADR-225: Smart-markdown `aggregation` token — group counts from aggregation_list views

| Field | Value |
|-------|-------|
| **Decision ID** | ADR-225 |
| **Initiative** | Make aggregation-derived counts embeddable in smart-markdown (including Mermaid charts) |
| **Proposed By** | Engineering |
| **Date** | 2026-05-30 |
| **Status** | Approved |

---

## ADR (WH(Y) Statement format)

**In the context of** wanting smart-markdown dashboards to show live
group counts from an aggregation_list view — "how many capabilities
are Approved", "how many are at Maturity level 3" — directly in prose
or inside a Mermaid pie / xychart-beta / flowchart block,

**facing** that the existing token surface (ADR-205 / ADR-222 / ADR-223)
exposes single-element fields and per-diagram element counts, but has
no way to read **aggregation engine output**. Authors can today render
an entire aggregation_list view inline, but cannot pull out one group's
count to drop into a sentence or a chart cell. The pie chart on the
GEANZ Dashboard, for instance, ships with hand-typed `"Approved" : 7`
/ `"Proposed" : 30` because no token resolves those numbers,

**we decided to** add a new smart-markdown entity type, ``aggregation``,
with a single field-spec ``group_count:<group>`` that runs the
aggregation profile bound to a named ``aggregation_list`` view and
returns the count for the named group:

  - `{{aggregation:<view_id>:group_count:Approved}}` → 7
  - `{{aggregation:<view_id>:group_count:Proposed:raw}}` → 30
  - `{{aggregation:<view_id>:group_count:3:raw}}` → 15 (Maturity rollup,
    level 3)

Resolution path: look up the target diagram, require
``diagram_type == "aggregation_list"``, read its
``data.source_diagram_id`` + ``data.profile_id``, run
``aggregation.engine.run(...)``, group the result rows by the profile's
``output.group_by`` (already done by the engine), and return the row
count for the matching group as a string. Composes with ADR-224
``:raw`` for Mermaid use.

**to achieve** one-line embedding of any aggregation group count inside
prose, tables, or Mermaid charts — exactly the same authoring shape as
ADR-223's ``relationship_count`` / ``diagram_usage_count``. No new
aggregation surface, no schema change.

**accepting** that:
- The token re-runs the aggregation engine on every smart-markdown
  resolve. The engine is already idempotent and is run on every
  aggregation_list GET, so the cost is the same as opening the rollup
  view. Page-level caching (if/when added) covers both.
- The token binds to a **view**, not directly to a (profile, source)
  pair. Forces the author to name the view, but keeps the token short
  and means renaming/moving the binding is a single edit on the view.
- The group key is matched against the resolved group value
  ``_resolve_group_value`` would return — string match, case-sensitive.
  Unknown group → ``"0"`` (consistent with "0 rows in that bucket"),
  not ``None`` (which would strikethrough). Missing/deleted view →
  ``None`` (strikethrough — same as a dangling element reference).
- Group values containing ``:`` would clash with the ``:raw`` suffix.
  All current group sources (status strings, maturity integers, zone
  names, package names) are colon-free; if a future group emits
  colons, the author can switch to a profile whose ``group_by`` maps
  them to a colon-free dimension. Documented, not engineered around.

## Rejected alternatives

- **Bind to ``(profile_id, source_id)`` directly.** More flexible but
  verbose and breaks the single-id pattern of every other token. View
  binding adds one layer of indirection that matches what the user is
  already authoring.
- **Reuse the ``diagram`` entity type with a new field-spec.** The
  resolver already knows about ``element_count``; we could add
  ``aggregation_group_count:<g>``. Cleaner namespace but worse for
  discoverability — aggregation isn't a property of every diagram,
  only of aggregation_list ones. A dedicated entity type sets the
  expectation right and lets the rejection path say "this only works
  on aggregation_list diagrams" instead of failing silently.
- **Inline the full aggregation result and let the author parse it
  with Mermaid.** Mermaid can't parse markdown lists into chart data.
  A discrete count token is the only authoring shape that works
  inside fenced blocks.

## Dependencies

- Builds on ADR-205 (smart-markdown tokens), ADR-209 (link-wrap that
  ``:raw`` from ADR-224 suppresses), ADR-212 (aggregation profiles),
  ADR-213 (aggregation_list synth-on-read). Composes with ADR-224.

## Consequences

- Spec: SPEC-225-A.
- No migration, no MCP/CLI write-surface impact (read-only token,
  Protocol §14 unaffected), no engine algorithm change. The new
  resolver delegates to the existing ``aggregation.engine.run``.
- Authors can now make the GEANZ Dashboard's status pie and any
  similar chart live against the model.
