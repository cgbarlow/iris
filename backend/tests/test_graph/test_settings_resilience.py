"""Unit tests for graph-settings resilience (ADR-117 v5.7.1 amendment).

Background: UAT (Supabase) returned HTTP 500 from
`GET /api/graph/settings` because the read path raised an unhandled
exception when the DB query failed (e.g. table missing on a
partially-migrated deployment, or transient DB error). The frontend
caught the failure silently and fell back to hard-coded defaults —
making the bug invisible to admins (their localStorage carries their
saved settings) but observable to anonymous users.

This module tests the post-fix behaviour:
- `get_graph_settings` returns None on DB error (logs + swallows).
- `get_graph_settings_cascaded` returns hard-coded defaults on DB
  error rather than propagating.
- `seed_graph_settings_defaults` no-ops on DB error rather than
  crashing startup.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.graph.service import (
    GRAPH_SETTINGS_DEFAULTS,
    get_graph_settings,
    get_graph_settings_cascaded,
    seed_graph_settings_defaults,
)


class _FailingDB:
    """A DatabasePort double whose every read raises."""

    def __init__(self, exc: Exception | None = None) -> None:
        self._exc = exc or RuntimeError("relation \"graph_settings\" does not exist")

    async def execute(self, *_args: Any, **_kwargs: Any) -> Any:
        raise self._exc

    async def commit(self) -> None:  # pragma: no cover — never reached
        pass


class TestGetGraphSettingsResilience:
    @pytest.mark.anyio
    async def test_returns_none_on_db_error(self) -> None:
        """A failing SELECT must not propagate — return None so callers can fall back."""
        db = _FailingDB()
        result = await get_graph_settings(db, "global", "__global__")
        assert result is None


class TestGetGraphSettingsCascadedResilience:
    @pytest.mark.anyio
    async def test_returns_hardcoded_defaults_on_db_error(self) -> None:
        """The cascade must never raise — return hard-coded defaults so the endpoint stays alive."""
        db = _FailingDB()
        result = await get_graph_settings_cascaded(db)
        assert result["scope_type"] == "global"
        assert result["scope_id"] == "__global__"
        # Settings should be the hard-coded defaults verbatim.
        assert result["settings"]["label_density"] == GRAPH_SETTINGS_DEFAULTS["label_density"]
        assert result["settings"]["nodes"] == GRAPH_SETTINGS_DEFAULTS["nodes"]
        assert result["settings"]["edges"] == GRAPH_SETTINGS_DEFAULTS["edges"]

    @pytest.mark.anyio
    async def test_returns_hardcoded_defaults_on_db_error_with_scopes(self) -> None:
        """Same resilience when scoped params are present."""
        db = _FailingDB()
        result = await get_graph_settings_cascaded(
            db, set_id="set-id", collection_id="col-id"
        )
        assert result["scope_type"] == "global"
        assert result["settings"]["label_density"] == GRAPH_SETTINGS_DEFAULTS["label_density"]


class TestSeedGraphSettingsDefaultsResilience:
    @pytest.mark.anyio
    async def test_does_not_crash_when_table_missing(self) -> None:
        """Seed must log-and-skip on DB error rather than crashing app startup."""
        db = _FailingDB()
        # Must not raise.
        await seed_graph_settings_defaults(db)
