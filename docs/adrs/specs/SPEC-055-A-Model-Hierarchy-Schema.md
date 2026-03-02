# SPEC-055-A: Model Hierarchy Schema

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-055-A |
| **ADR** | [ADR-055](../ADR-055-Model-Hierarchy.md) |
| **Status** | Implemented |

## Schema Change

Migration `m011_model_hierarchy.py` adds:

```sql
ALTER TABLE models ADD COLUMN parent_model_id TEXT REFERENCES models(id);
CREATE INDEX idx_models_parent ON models(parent_model_id);
```

- `parent_model_id` defaults to NULL (root model)
- Self-referential FK to `models(id)`
- Index for efficient child queries
- Idempotent (checks column existence before altering)

## Pydantic Models

- `ModelCreate`: added `parent_model_id: str | None = None`
- `ModelResponse`: added `parent_model_id: str | None = None`
- `ModelHierarchyNode`: new model with `id`, `name`, `model_type`, `parent_model_id`, `children: list[ModelHierarchyNode]`
