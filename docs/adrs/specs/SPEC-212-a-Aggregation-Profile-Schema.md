# SPEC-212-a: Aggregation profile schema, scope, CRUD

Implements: [ADR-212](../ADR-212-Aggregation-Profiles-And-Engine.md)

## 1. Database schema

### SQLite (`backend/app/migrations/m076_aggregation_profiles.py`)

```sql
CREATE TABLE IF NOT EXISTS aggregation_profiles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    set_id TEXT REFERENCES sets(id),
    is_global INTEGER NOT NULL DEFAULT 0,
    profile_data TEXT NOT NULL,            -- JSON
    is_default_for_set INTEGER NOT NULL DEFAULT 0,
    created_by TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    is_deleted INTEGER NOT NULL DEFAULT 0,
    CHECK ((is_global = 1 AND set_id IS NULL) OR (is_global = 0 AND set_id IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS idx_agg_profiles_set ON aggregation_profiles(set_id) WHERE is_deleted = 0;
CREATE INDEX IF NOT EXISTS idx_agg_profiles_global ON aggregation_profiles(is_global) WHERE is_deleted = 0;
```

### Supabase (`backend/app/migrations/supabase/m081_aggregation_profiles.sql`)

Mirror with `BOOLEAN` literals, `TIMESTAMPTZ` columns, and `profile_data JSONB`. See file.

## 2. profile_data JSON shape

```jsonc
{
  "$comment": "Required top-level keys: traversal, output.",
  "traversal": {
    "outer": {                              // optional; omit for single-level rollups
      "collect_token_type": "diagram",      // any entity-type variant from the smart-markdown grammar
      "multiplier": {                       // optional
        "from_attribute_override": "<attr-path-on-the-outer-token>",
        "divisor_from_diagram_data": "data.<field-path-on-the-referenced-diagram>",
        "default_multiplier": 1
      }
    },
    "inner": {                              // required
      "collect_token_type": "element",
      "value_attribute_path": "attributes/Quantity/type",
      "bucket_attribute_path": "attributes/Unit/type",  // optional (null = no bucket)
      "skip_blank_values": true             // default true; rows with no value are dropped
    }
  },
  "output": {
    "group_by": "element.package_name",     // dotted path; see §3.3 of SPEC-212-b
    "sort_groups": "alpha",                 // alpha | none
    "sort_items_within_group": "alpha",     // alpha | none
    "aggregation_fn": "sum",                // sum | count
    "line_format": "- {element.name}: {sum_value}{bucket_spaced}",
    "show_per_source_breakdown": false,
    "breakdown_format": " ({sources_joined})"
  }
}
```

## 3. Pydantic models (`backend/app/aggregation/models.py`)

```python
class TraversalStep(BaseModel):
    collect_token_type: Literal["element", "diagram", "package", "set", "collection"]
    value_attribute_path: str | None = None
    bucket_attribute_path: str | None = None
    skip_blank_values: bool = True

class MultiplierRule(BaseModel):
    from_attribute_override: str | None = None
    divisor_from_diagram_data: str | None = None
    default_multiplier: float = 1.0

class OuterTraversal(TraversalStep):
    multiplier: MultiplierRule | None = None

class TraversalConfig(BaseModel):
    outer: OuterTraversal | None = None
    inner: TraversalStep

class OutputConfig(BaseModel):
    group_by: str | None = None
    sort_groups: Literal["alpha", "none"] = "alpha"
    sort_items_within_group: Literal["alpha", "none"] = "alpha"
    aggregation_fn: Literal["sum", "count"] = "sum"
    line_format: str = "- {element.name}: {sum_value}{bucket_spaced}"
    show_per_source_breakdown: bool = False
    breakdown_format: str = " ({sources_joined})"

class ProfileData(BaseModel):
    traversal: TraversalConfig
    output: OutputConfig

class AggregationProfileCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    set_id: str | None = None
    is_global: bool = False
    profile_data: ProfileData
    is_default_for_set: bool = False

class AggregationProfileUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    set_id: str | None = None
    is_global: bool | None = None
    profile_data: ProfileData | None = None
    is_default_for_set: bool | None = None

class AggregationProfileResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    set_id: str | None = None
    set_name: str | None = None
    is_global: bool = False
    is_default_for_set: bool = False
    profile_data: dict[str, object]
    created_by: str | None = None
    created_by_username: str = "Unknown"
    created_at: str
    updated_at: str
```

## 4. Service (`backend/app/aggregation/profiles_service.py`)

Same shape as `element_templates/service.py`:

- `create_aggregation_profile(...)` — validates scope (mutually exclusive set_id/is_global), persists.
- `get_aggregation_profile(id)` — joined with `sets` for `set_name` and `users` for `created_by_username`.
- `list_aggregation_profiles(set_id, include_global, page, page_size)` — same scoping as element_templates.
- `update_aggregation_profile(id, **fields)` — sentinel-or-value for `set_id` to handle tri-state.
- `delete_aggregation_profile(id)` — soft-delete (sets `is_deleted = 1`).

Row access positional throughout (Protocol §15).

## 5. Scope rules

Identical to `element_templates`:

- `is_global = TRUE` ↔ `set_id IS NULL`. Enforced by CHECK constraint and service-layer `_validate_scope()`.
- Set-scoped profile visible to that set only; global profile visible to all sets.

## 6. Tests (`backend/tests/test_aggregation/test_profile_crud.py`)

- Create global / set-scoped / rejected mixed-scope.
- Create with invalid profile_data → 422.
- Get / list / update / delete round-trip.
- List with set_id + include_global returns set + globals.
- Boolean-literal regression check for the Supabase schema.
