"""Aggregation engine exceptions (ADR-212)."""

from __future__ import annotations


class AggregationProfileNotFound(LookupError):
    """Profile id resolves to no row. Router maps to 404."""


class AggregationProfileScopeError(ValueError):
    """is_global ↔ set_id invariant violated, or content missing.
    Router maps to 422."""


class AggregationSourceNotFound(LookupError):
    """The source diagram id resolves to no row. Router maps to 404."""


class AggregationProfileInvalid(ValueError):
    """profile_data fails validation. Router maps to 422."""
