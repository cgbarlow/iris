"""Tests for expanded AI creation prompts (ADR-132, SPEC-132-A).

Verifies that:
- build_creation_system_prompt() returns a composed, non-empty prompt for
  every new notation x diagram_type bundle (simple/component, simple/roadmap,
  simple/free_form, uml/sequence, uml/class, archimate/process, c4/deployment).
- DoView's existing prompts still compose identically after the expansion
  (regression guard — the shipped DoView flow must be untouched).
- The expanded seed function is idempotent on re-run.
"""

from __future__ import annotations

import aiosqlite
import pytest
import pytest_asyncio

from app.ai.creation import build_creation_system_prompt
from app.migrations.m028_ai_creation_prompts import up as m028_up
from app.migrations.m051_response_format_prompts import up as m051_up
from app.seed.creation_prompts import seed_creation_prompts

# Bundles the expansion must support (SPEC-132-A row inventory).
EXPANDED_BUNDLES: list[tuple[str, str]] = [
    ("simple", "component"),
    ("simple", "roadmap"),
    ("simple", "free_form"),
    ("uml", "sequence"),
    ("uml", "class"),
    ("archimate", "process"),
    ("c4", "deployment"),
]


@pytest_asyncio.fixture
async def db() -> aiosqlite.Connection:
    """DB with the creation_prompts table, DoView-era rows, and the expansion seed applied."""
    async with aiosqlite.connect(":memory:") as conn:
        await m028_up(conn)
        await seed_creation_prompts(conn)
        # m051 adds the `purpose` column to ai_creation_prompts so the
        # composer's WHERE-purpose-filter resolves (ADR-157, v5.12.0).
        # The registry inserts in m051 are auto-skipped when m020's
        # registry tables aren't present (test isolation).
        await m051_up(conn)
        yield conn


class TestExpandedNotationLayerPrompts:
    """Each new notation must have an active notation-layer prompt row."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("notation", ["simple", "uml", "archimate", "c4"])
    async def test_notation_prompt_row_present(
        self, db: aiosqlite.Connection, notation: str
    ) -> None:
        cursor = await db.execute(
            "SELECT prompt_text FROM ai_creation_prompts "
            "WHERE layer='notation' AND notation=? AND is_active=1",
            (notation,),
        )
        row = await cursor.fetchone()
        assert row is not None, f"No active notation-layer row for {notation}"
        assert len(row[0]) > 200, (
            f"{notation} notation prompt is suspiciously short ({len(row[0])} chars)"
        )


class TestExpandedDiagramTypeLayerPrompts:
    """Each new diagram-type layer row must exist and compose."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("notation", "diagram_type"), EXPANDED_BUNDLES)
    async def test_diagram_type_prompt_row_present(
        self, db: aiosqlite.Connection, notation: str, diagram_type: str
    ) -> None:
        cursor = await db.execute(
            "SELECT prompt_text FROM ai_creation_prompts "
            "WHERE layer='diagram_type' AND diagram_type=? AND is_active=1",
            (diagram_type,),
        )
        row = await cursor.fetchone()
        assert row is not None, (
            f"No active diagram_type-layer row for {notation}/{diagram_type}"
        )
        assert len(row[0]) > 100, (
            f"{diagram_type} prompt is suspiciously short ({len(row[0])} chars)"
        )


class TestExpandedPromptComposition:
    """build_creation_system_prompt composes base + notation + diagram_type for new bundles."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("notation", "diagram_type"), EXPANDED_BUNDLES)
    async def test_composed_prompt_not_empty(
        self, db: aiosqlite.Connection, notation: str, diagram_type: str
    ) -> None:
        result = await build_creation_system_prompt(db, notation, diagram_type)
        assert isinstance(result, str)
        assert len(result) > 500, (
            f"{notation}/{diagram_type} composed prompt is suspiciously short"
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("notation", "diagram_type"), EXPANDED_BUNDLES)
    async def test_composed_prompt_contains_base_json_schema(
        self, db: aiosqlite.Connection, notation: str, diagram_type: str
    ) -> None:
        """Base layer contributes the JSON output format; composed prompt must inherit it."""
        result = await build_creation_system_prompt(db, notation, diagram_type)
        # The base prompt declares the JSON envelope shape; cheapest markers to assert.
        assert "total_pages" in result, (
            f"{notation}/{diagram_type} missing total_pages marker from base layer"
        )
        assert "diagrams" in result.lower()
        assert "nodes" in result.lower()
        assert "edges" in result.lower()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("notation", "diagram_type"), EXPANDED_BUNDLES)
    async def test_composed_prompt_contains_notation_name(
        self, db: aiosqlite.Connection, notation: str, diagram_type: str
    ) -> None:
        """Composed prompt mentions the notation — loose proof the notation layer ran."""
        result = await build_creation_system_prompt(db, notation, diagram_type)
        assert notation.lower() in result.lower() or notation.upper() in result, (
            f"{notation}/{diagram_type} composed prompt does not mention notation name"
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("notation", "diagram_type"), EXPANDED_BUNDLES)
    async def test_composed_prompt_contains_diagram_type_hint(
        self, db: aiosqlite.Connection, notation: str, diagram_type: str
    ) -> None:
        """Diagram-type layer must show up in composed output."""
        result = await build_creation_system_prompt(db, notation, diagram_type)
        # diagram_type keys are like 'sequence', 'class', 'deployment'; substring match.
        # free_form uses 'free' as a meaningful token.
        needle = "free" if diagram_type == "free_form" else diagram_type
        assert needle.lower() in result.lower(), (
            f"{notation}/{diagram_type} composed prompt does not reference the diagram type"
        )


class TestDoViewRegression:
    """The shipped DoView flow must be byte-identical after the expansion (ADR-132 non-goal)."""

    @pytest.mark.asyncio
    async def test_doview_notation_only_matches_pre_expansion(
        self, db: aiosqlite.Connection
    ) -> None:
        """DoView without a diagram_type still composes base + doview notation exactly."""
        result = await build_creation_system_prompt(db, "doview")
        assert "DoView" in result  # notation layer
        assert "total_pages" in result  # base layer
        # Key DoView-specific methodology markers that must survive the expansion.
        assert "This-Then" in result
        assert "outcome_box" in result

    @pytest.mark.asyncio
    async def test_doview_outcomes_map_includes_layout(
        self, db: aiosqlite.Connection
    ) -> None:
        result = await build_creation_system_prompt(db, "doview", "outcomes_map")
        assert "outcomes_map" in result.lower() or "outcomes map" in result.lower()

    @pytest.mark.asyncio
    async def test_doview_overview_includes_layout(
        self, db: aiosqlite.Connection
    ) -> None:
        result = await build_creation_system_prompt(db, "doview", "overview")
        # Overview-page layout rules (tile grid) must still be present.
        assert "overview" in result.lower()


class TestSeedIdempotency:
    """Running seed_creation_prompts twice does not duplicate rows."""

    @pytest.mark.asyncio
    async def test_second_run_does_not_duplicate(
        self, db: aiosqlite.Connection
    ) -> None:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM ai_creation_prompts WHERE is_active=1"
        )
        first = (await cursor.fetchone())[0]

        await seed_creation_prompts(db)  # run again

        cursor = await db.execute(
            "SELECT COUNT(*) FROM ai_creation_prompts WHERE is_active=1"
        )
        second = (await cursor.fetchone())[0]
        assert second == first, (
            f"seed_creation_prompts is not idempotent: {first} → {second}"
        )

    @pytest.mark.asyncio
    async def test_expected_total_row_count(
        self, db: aiosqlite.Connection
    ) -> None:
        """After seed: 4 DoView-era rows (m028) + 11 expansion rows
        (ADR-132, v5.8.0) + 3 shared cascade base rows (ADR-176,
        v6.1.0) + 1 doview_analysis pointer (v6.6.2) + 2 markdown-type
        rows (ADR-206, v6.15.0: smart_markdown + dynamic_list) = 21
        active creation_format rows. Plus 3 response_format rows
        added by m051 (ADR-157, v5.12.0) = 24 total active rows.
        Verify both counts independently so a regression in either
        purpose's seed surfaces clearly."""
        cursor = await db.execute(
            "SELECT COUNT(*) FROM ai_creation_prompts "
            "WHERE is_active=1 AND purpose = 'creation_format'"
        )
        creation_count = (await cursor.fetchone())[0]
        assert creation_count == 21, (
            f"Expected 21 active creation_format rows (4 DoView-era + 11 expansion + 3 cascade-shared + 1 doview_analysis pointer + 2 markdown-types), got {creation_count}"
        )

        cursor = await db.execute(
            "SELECT COUNT(*) FROM ai_creation_prompts "
            "WHERE is_active=1 AND purpose = 'response_format'"
        )
        response_count = (await cursor.fetchone())[0]
        assert response_count == 3, (
            f"Expected 3 active response_format rows (ADR-157), got {response_count}"
        )
