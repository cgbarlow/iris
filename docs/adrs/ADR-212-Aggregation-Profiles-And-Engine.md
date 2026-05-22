# ADR-212: Generic aggregation profiles and aggregation engine

Status: Accepted (2026-05-22)

Builds on: [ADR-205](./ADR-205-Smart-Markdown-View-Type.md), [ADR-210](./ADR-210-Smart-Markdown-Value-Overrides.md), [ADR-211](./ADR-211-Element-Template-Stamps.md), [ADR-182](./ADR-182-Surface-Parity-Discipline.md).

## Context

ADR-210 (`=value` overrides) and ADR-211 (template stamps) give per-use values a first-class machine-parseable home. The shopping-list workflow ([issue #211](https://github.com/cgbarlow/iris/issues/211)) now needs the consumer side: walk a source smart-markdown diagram, collect those structured values, group, sum, and emit aggregated markdown.

A naïve implementation puts the algorithm inside a `shopping_list` diagram type. That makes the engine domain-specific (recipe / meal / ingredient / aisle terminology baked into Python). It also makes the engine invisible from outside the diagram lifecycle — agents (Claude Desktop, MCP callers) can only invoke it by GETting a diagram. Both consequences violate the principles already established: genericness (ADR-214) and "make compute a first-class Iris operation, not a buried Python script."

## Decision

Add **two coupled things**: a `aggregation_profiles` library table, and a generic `aggregation_engine` module that is callable directly from REST / MCP / CLI.

### Profile = user-managed JSON ruleset

A row in `aggregation_profiles` carries:

- Identity: `name`, `description`.
- Scope: `is_global` / `set_id` — same rules as element_templates.
- The ruleset itself in `profile_data` (JSON) — describes the traversal, attribute paths, multiplier rules, and output format.

The engine knows nothing about ingredients or sprints. Different profiles drive different aggregations on the same engine: shopping-list / sprint-points / time-tracking / expense-report / reading-log are *data*, not *code paths*. The seeded library ([§4.5 of the plan](../plans/issue-211-shopping-list-implementation.md)) ships five global profiles paired 1-for-1 with ADR-211's seeded stamps.

### Engine = ~200-line generic kernel

`backend/app/aggregation/engine.py` implements one function — `run(profile, source_diagram_id, db)` — that:

1. **Traverses** the source diagram's `markdown_source` to collect tokens of a configured type. The profile may declare an **outer** step (each collected token references another diagram; recurse one level) and an **inner** step (each collected token's `=value` overrides and entity-attribute lookups yield `(token_id, value, bucket)` rows).
2. **Multiplies** rows by an optional per-outer-token multiplier (e.g. diners / servings — generic ratio).
3. **Groups** by `(token_id, bucket)`, **aggregates** with a configured function (`sum`, `count`).
4. **Groups again** by an output `group_by` attribute path (e.g. the element's `package_name`).
5. **Formats** each line via a configurable template string with `{name}` / `{sum_value}` / `{bucket}` / `{sources_joined}` placeholders.

Output: a markdown string. Same pipeline as smart_markdown / dynamic_list (synth-on-read pattern — ADR-187).

### First-class Iris operation

Three surfaces, all parity (ADR-182):

| Surface | Call |
|---|---|
| **REST** | `POST /api/aggregation/run` body `{profile_id, source_diagram_id}` → `{markdown, computed_at}` |
| **MCP** | `aggregate(profile_id, source_diagram_id) -> string` |
| **CLI** | `iris aggregate --profile <id-or-name> --source <diagram-id>` |

Plus CRUD on `/api/aggregation/profiles` with full MCP + CLI parity.

The aggregation engine is **module-level callable** — no need for a persisted diagram to invoke it. ADR-213 ships an `aggregation_list` diagram type as the visual surface; this ADR ships the engine that diagram type wraps. Agents (Claude Desktop) call `aggregate(...)` directly without ever opening a UI.

### Profile JSON shape

```yaml
{
  "traversal": {
    "outer": {                              # optional
      "collect_token_type": "diagram",      # walk these tokens in the source
      "multiplier": {                       # optional
        "from_attribute_override": "attributes/Diners/type",  # value carried by the outer token
        "divisor_from_diagram_data": "data.servings",         # field on the referenced diagram
        "default_multiplier": 1
      }
    },
    "inner": {                              # required
      "collect_token_type": "element",      # walk these in the referenced diagrams (or source if no outer)
      "value_attribute_path": "attributes/Quantity/type",
      "bucket_attribute_path": "attributes/Unit/type",       # optional; null = single bucket
      "skip_blank_values": true
    }
  },
  "output": {
    "group_by": "element.package_name",     # or "element.attributes.Author/type", etc.
    "sort_groups": "alpha",                 # alpha | none
    "sort_items_within_group": "alpha",
    "aggregation_fn": "sum",                # sum | count
    "line_format": "- [{element.name}](iris://element/{element.id}) — {sum_value}{bucket_spaced}",
    "show_per_source_breakdown": true,
    "breakdown_format": " ({sources_joined})"
  }
}
```

JSONSchema validation (`backend/app/aggregation/schema.py`) is applied on every write. Profiles that fail validation never persist.

### Why a new module, not under `diagrams/`

DRY (§13) and module purity: aggregation has its own concerns (rule schema, traversal walks, format strings). Living under `diagrams/` would imply it's part of the diagram lifecycle — but it isn't. The `aggregation_list` diagram type (ADR-213) is one *consumer*; the MCP `aggregate` tool is another; future exports or scheduled jobs are more. Each surface uses the same engine.

## Consequences

**Positive:**

- One engine, many use cases. Shopping-list / sprint-points / time / expense / reading-log all run through the same code.
- Compute is callable from outside the UI — Claude Desktop walks a meal plan into a shopping list without any persisted aggregation_list diagram.
- Profiles are first-class library data — editable in admin/set settings ([§9.4 of the plan](../plans/issue-211-shopping-list-implementation.md)), exportable, version-able.
- No core code learns "ingredient" / "recipe" / "meal" / "aisle" terminology.

**Negative / accepted trade-offs:**

- The profile JSON is non-trivial. The form-based editor lands with ADR-213's UI; for v6.20 it's manageable via REST/MCP/CLI by agents (which is the `/goal` primary consumer).
- A user designing a new profile has to think about traversal levels and attribute paths. The seeded library reduces this for the common cases.
- Engine is fixed-shape (walk + collect + group + sum + format). Custom computations (joins, percentiles, LLM summarisation) need a different engine — explicitly not in scope.

## Rejected alternatives

- **Engine inside `aggregation_list` diagram type module.** Bakes compute into the diagram lifecycle; not callable from non-diagram surfaces; harder to test in isolation; obvious DRY violation when a second consumer arrives.
- **Hardcoded "shopping-list" diagram type.** Domain-specific code; fails the genericness invariant.
- **General-purpose DSL / scripting runtime.** Way more surface than needed; debugging burden; security implications. Aggregation is a single pattern — walk, collect, group, fold, format — and that's what the engine does.
- **Profile JSON stored on each diagram (no library).** Copy-paste reuse, no shared library, no editor scope. Rejected.

## References

- [SPEC-212-a — Profile schema, scope, CRUD endpoints](./specs/SPEC-212-a-Aggregation-Profile-Schema.md)
- [SPEC-212-b — Engine compute algorithm](./specs/SPEC-212-b-Aggregation-Engine.md)
- [SPEC-212-c — REST/MCP/CLI surfaces](./specs/SPEC-212-c-Aggregation-Surfaces.md)
- [ADR-213](./ADR-213-Aggregation-List-Diagram-Type.md) — visual wrapper diagram type.
- [`docs/plans/issue-211-shopping-list-implementation.md`](../plans/issue-211-shopping-list-implementation.md) §5–§6 — module layout, profile editor UX, the five seeded profiles.
