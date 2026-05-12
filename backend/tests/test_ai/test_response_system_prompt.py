"""v5.12.0 (ADR-157): `build_response_system_prompt` composes the
layered response_format prompts and is isolated from creation_format
prompts under the same `ai_creation_prompts` table.

Uses a minimal fixture: only the `ai_creation_prompts` table is
required for the composer (it queries no other tables). Seeds rows
directly to keep the test focused and independent of migration
ordering.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from app.ai.creation import (
    build_creation_system_prompt,
    build_response_system_prompt,
)

if TYPE_CHECKING:
    import aiosqlite


_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS ai_creation_prompts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    purpose TEXT NOT NULL DEFAULT 'creation_format',
    layer TEXT NOT NULL,
    notation TEXT,
    diagram_type TEXT,
    prompt_text TEXT NOT NULL,
    display_order INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_by TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
)
"""


def _seed_row(*, id: str, purpose: str, layer: str, notation: str | None,
              diagram_type: str | None, body: str) -> tuple:
    return (id, id, purpose, layer, notation, diagram_type, body)


@pytest.fixture
async def prompts_db(main_db: aiosqlite.Connection) -> aiosqlite.Connection:
    """A SQLite DB with only the `ai_creation_prompts` table and a
    small set of seed rows covering creation_format and response_format
    under both creation and response purposes."""
    await main_db.execute(_CREATE_TABLE)

    seeds = [
        # creation_format rows (existing v5.8.x behaviour — composer must
        # still find these under purpose='creation_format')
        _seed_row(
            id="creation-base",
            purpose="creation_format", layer="base",
            notation=None, diagram_type=None,
            body="## Creation base\nYou create diagrams.",
        ),
        _seed_row(
            id="creation-doview-notation",
            purpose="creation_format", layer="notation",
            notation="doview", diagram_type=None,
            body="## DoView Creation Methodology\nStage 0: Setup Questions.",
        ),
        _seed_row(
            id="creation-doview-outcomes_map",
            purpose="creation_format", layer="diagram_type",
            notation=None, diagram_type="outcomes_map",
            body="## Outcomes map layout rules\nColumns left to right.",
        ),

        # response_format rows (new v5.12.0 — composer with purpose='response_format'
        # filter must pick these up and only these)
        _seed_row(
            id="response-base",
            purpose="response_format", layer="base",
            notation=None, diagram_type=None,
            body="## Response format base\nApply these universal rules.",
        ),
        _seed_row(
            id="response-markdown-notation",
            purpose="response_format", layer="notation",
            notation="markdown", diagram_type=None,
            body="## Response format DoView framing\nOutcomes theory points out that.",
        ),
        _seed_row(
            id="response-doview-analysis",
            purpose="response_format", layer="diagram_type",
            notation=None, diagram_type="doview_analysis",
            body="## doview_analysis output structure\nI have prepared a summary response.",
        ),
    ]
    for row in seeds:
        await main_db.execute(
            "INSERT INTO ai_creation_prompts "
            "(id, name, purpose, layer, notation, diagram_type, prompt_text, display_order, is_active) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 0, 1)",
            row,
        )
    await main_db.commit()
    return main_db


class TestBuildResponseSystemPrompt:
    async def test_composes_three_layers_for_doview_analysis(
        self, prompts_db: aiosqlite.Connection,
    ) -> None:
        """For (notation=markdown, diagram_type=doview_analysis), the
        composer should stack base + notation + diagram_type layers."""
        text = await build_response_system_prompt(
            prompts_db, "markdown", "doview_analysis",
        )
        # Base layer.
        assert "Apply these universal rules" in text
        # Notation layer (DoView framing).
        assert "Outcomes theory points out that" in text
        # Diagram_type layer (output structure).
        assert "I have prepared a summary response" in text

    async def test_returns_empty_for_notation_with_no_response_format(
        self, prompts_db: aiosqlite.Connection,
    ) -> None:
        """A notation with no response_format rows returns just the base
        layer (which is shared). If we strip the base too, empty."""
        text = await build_response_system_prompt(prompts_db, "uml", "class")
        # No uml/class response_format seed → only the base layer
        # contributes; no notation or diagram_type content.
        assert "Apply these universal rules" in text
        assert "Outcomes theory" not in text
        assert "summary response" not in text.lower()

    async def test_does_not_leak_creation_prompt_content(
        self, prompts_db: aiosqlite.Connection,
    ) -> None:
        """The response composer must filter by purpose='response_format'
        and not pick up creation_format rows."""
        text = await build_response_system_prompt(
            prompts_db, "markdown", "doview_analysis",
        )
        # Creation seed bodies.
        assert "Creation base" not in text
        assert "DoView Creation Methodology" not in text
        assert "Outcomes map layout rules" not in text

    async def test_creation_composer_unchanged_by_response_seeds(
        self, prompts_db: aiosqlite.Connection,
    ) -> None:
        """The creation composer must filter by purpose='creation_format'
        and not pick up response_format rows."""
        text = await build_creation_system_prompt(
            prompts_db, "doview", "outcomes_map",
        )
        # Creation bodies present.
        assert "Creation base" in text
        assert "DoView Creation Methodology" in text
        assert "Outcomes map layout rules" in text
        # Response bodies absent.
        assert "Apply these universal rules" not in text
        assert "summary response" not in text.lower()


class TestPurposeIsolation:
    async def test_creation_and_response_use_separate_rows(
        self, prompts_db: aiosqlite.Connection,
    ) -> None:
        """ai_creation_prompts table has rows under both purposes; each
        composer filters correctly without leakage."""
        creation = await build_creation_system_prompt(
            prompts_db, "doview", "outcomes_map",
        )
        response = await build_response_system_prompt(
            prompts_db, "markdown", "doview_analysis",
        )

        # Both produced non-empty output.
        assert creation
        assert response

        # Each pulls its own seeds.
        assert "DoView Creation Methodology" in creation
        assert "DoView Creation Methodology" not in response

        assert "summary response" in response.lower()
        assert "summary response" not in creation.lower()
