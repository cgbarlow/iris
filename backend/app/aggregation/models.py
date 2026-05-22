"""Pydantic models for aggregation profiles + engine (ADR-212).

Profile data validation lives in pydantic — JSONSchema would be
redundant when ProfileData is already a typed pydantic root model.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────
# Profile shape (the ruleset)
# ─────────────────────────────────────────────────────────────────────

TokenType = Literal["element", "diagram", "package", "set", "collection"]


class MultiplierRule(BaseModel):
    """Per-outer-token multiplier rule.

    The outer token may carry a value via ``=value`` override on a
    specific attribute path (``from_attribute_override``); divided by
    the referenced diagram's ``data.<divisor_from_diagram_data>``
    field; with ``default_multiplier`` used when the override is
    absent. Returns 1.0 when nothing resolves.
    """

    from_attribute_override: str | None = None
    divisor_from_diagram_data: str | None = None
    default_multiplier: float = 1.0


class InnerStep(BaseModel):
    collect_token_type: TokenType = "element"
    value_attribute_path: str | None = None
    bucket_attribute_path: str | None = None
    skip_blank_values: bool = True


class OuterStep(BaseModel):
    collect_token_type: TokenType = "diagram"
    multiplier: MultiplierRule | None = None


class TraversalConfig(BaseModel):
    outer: OuterStep | None = None
    inner: InnerStep


SortMode = Literal["alpha", "none"]
AggregationFn = Literal["sum", "count"]


class OutputConfig(BaseModel):
    group_by: str | None = None
    sort_groups: SortMode = "alpha"
    sort_items_within_group: SortMode = "alpha"
    aggregation_fn: AggregationFn = "sum"
    line_format: str = "- {element.name}: {sum_value}{bucket_spaced}"
    show_per_source_breakdown: bool = False
    breakdown_format: str = " ({sources_joined})"


class ProfileData(BaseModel):
    traversal: TraversalConfig
    output: OutputConfig


# ─────────────────────────────────────────────────────────────────────
# Profile CRUD request / response
# ─────────────────────────────────────────────────────────────────────


class AggregationProfileCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    set_id: str | None = None
    is_global: bool = False
    profile_data: ProfileData
    is_default_for_set: bool = False


class AggregationProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
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
    # Seeded profiles have created_by NULL (no user at migration time).
    created_by: str | None = None
    created_by_username: str = "Unknown"
    created_at: str
    updated_at: str


class AggregationProfileListResponse(BaseModel):
    items: list[AggregationProfileResponse]
    total: int
    page: int
    page_size: int


# ─────────────────────────────────────────────────────────────────────
# Run request / response
# ─────────────────────────────────────────────────────────────────────


class AggregationRunRequest(BaseModel):
    profile_id: str = Field(min_length=1)
    source_diagram_id: str = Field(min_length=1)


class AggregationResult(BaseModel):
    markdown: str
    computed_at: str
    source_versions: dict[str, int] = Field(default_factory=dict)
    row_count: int = 0
    warnings: list[str] = Field(default_factory=list)
