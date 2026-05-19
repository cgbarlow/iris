"""Tests for diagram_type-layer creation prompts for the markdown types
(ADR-206, v6.15.0, issue #185 follow-up).

MCP `create_diagram` and the CLI `iris_client.create_diagram` are generic
write tools that accept any registered diagram_type. Without per-type
creation_format prompts, local-AI clients have no documentation of the
unique `data` shape for smart_markdown (`markdown_source` token syntax)
or dynamic_list (`source` + `show_description`). This test verifies
both rows land at seed time.
"""

from __future__ import annotations

import aiosqlite
import pytest
import pytest_asyncio

from app.migrations.m028_ai_creation_prompts import up as m028_up
from app.migrations.m051_response_format_prompts import up as m051_up
from app.seed.creation_prompts import seed_creation_prompts


@pytest_asyncio.fixture
async def db() -> aiosqlite.Connection:
    async with aiosqlite.connect(":memory:") as conn:
        await m028_up(conn)
        await m051_up(conn)
        await seed_creation_prompts(conn)
        yield conn


@pytest.mark.asyncio
async def test_smart_markdown_prompt_present(
    db: aiosqlite.Connection,
) -> None:
    cursor = await db.execute(
        "SELECT prompt_text FROM ai_creation_prompts "
        "WHERE layer='diagram_type' AND diagram_type='smart_markdown' "
        "AND is_active=1",
    )
    row = await cursor.fetchone()
    assert row is not None, "smart_markdown creation prompt row missing"
    text = row[0]
    assert "markdown_source" in text
    assert "attr:" in text
    assert "{{" in text  # the token syntax is mentioned


@pytest.mark.asyncio
async def test_dynamic_list_prompt_present(
    db: aiosqlite.Connection,
) -> None:
    cursor = await db.execute(
        "SELECT prompt_text FROM ai_creation_prompts "
        "WHERE layer='diagram_type' AND diagram_type='dynamic_list' "
        "AND is_active=1",
    )
    row = await cursor.fetchone()
    assert row is not None, "dynamic_list creation prompt row missing"
    text = row[0]
    assert "diagram_relationships" in text
    assert "package_elements" in text
    assert "show_description" in text


@pytest.mark.asyncio
async def test_reseed_is_idempotent(db: aiosqlite.Connection) -> None:
    """Running seed twice yields the same single row for each id."""
    await seed_creation_prompts(db)
    cursor = await db.execute(
        "SELECT COUNT(*) FROM ai_creation_prompts "
        "WHERE id IN (?, ?)",
        ("creation-md-smart-markdown-v1", "creation-md-dynamic-list-v1"),
    )
    count = (await cursor.fetchone())[0]
    assert count == 2
