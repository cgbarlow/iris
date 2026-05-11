"""ADR-154: MCP `prompts/list` includes named-prompt entries with
prompt_name interpolated into the picker description.
"""

from __future__ import annotations

from typing import Any

import pytest
from iris_client.models.core import ScopePromptIndexEntry

from iris_mcp import prompts as iris_prompts


class _StubClient:
    def __init__(self, entries: list[ScopePromptIndexEntry]) -> None:
        self._entries = entries

    async def list_scope_prompts(self) -> list[ScopePromptIndexEntry]:
        return list(self._entries)


def _system_entry(**kwargs: Any) -> ScopePromptIndexEntry:
    defaults = {
        "name": "set:00000000-0000-0000-0000-000000000001",
        "entry_kind": "system_prompt",
        "scope_type": "set",
        "scope_id": "00000000-0000-0000-0000-000000000001",
        "scope_name": "DoView Book",
        "description": None,
        "body": "system body",
        "prompt_name": None,
    }
    defaults.update(kwargs)
    return ScopePromptIndexEntry(**defaults)


def _named_entry(**kwargs: Any) -> ScopePromptIndexEntry:
    defaults = {
        "name": "set:00000000-0000-0000-0000-000000000001:outcomes-theory",
        "entry_kind": "named_prompt",
        "scope_type": "set",
        "scope_id": "00000000-0000-0000-0000-000000000001",
        "scope_name": "DoView Book",
        "description": "Outcomes-theory text response.",
        "body": "named body",
        "prompt_name": "outcomes-theory",
    }
    defaults.update(kwargs)
    return ScopePromptIndexEntry(**defaults)


class TestListPromptsNamed:
    @pytest.mark.asyncio
    async def test_named_prompt_appears_in_list(self) -> None:
        client: Any = _StubClient([_named_entry()])
        result = await iris_prompts.list_prompts(client)
        assert len(result) == 1
        assert result[0].name == "set:00000000-0000-0000-0000-000000000001:outcomes-theory"

    @pytest.mark.asyncio
    async def test_description_format_includes_prompt_name(self) -> None:
        client: Any = _StubClient([_named_entry()])
        result = await iris_prompts.list_prompts(client)
        # Format: "Set: {scope_name} — {prompt_name} — {prompt_description}"
        assert result[0].description == "Set: DoView Book — outcomes-theory — Outcomes-theory text response."

    @pytest.mark.asyncio
    async def test_system_and_named_coexist_in_order(self) -> None:
        client: Any = _StubClient([_system_entry(), _named_entry()])
        result = await iris_prompts.list_prompts(client)
        assert len(result) == 2
        # Order preserved from upstream.
        assert result[0].name == "set:00000000-0000-0000-0000-000000000001"
        assert result[1].name == "set:00000000-0000-0000-0000-000000000001:outcomes-theory"

    @pytest.mark.asyncio
    async def test_named_prompt_description_without_body_description(self) -> None:
        """If a named prompt's own description happens to be empty,
        picker still shows scope + prompt_name."""
        client: Any = _StubClient([_named_entry(description="")])
        result = await iris_prompts.list_prompts(client)
        assert result[0].description == "Set: DoView Book — outcomes-theory"
