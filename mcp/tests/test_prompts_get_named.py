"""ADR-154: MCP `prompts/get` handler resolves three-segment named-prompt
names (set:<uuid>:<name> / collection:<uuid>:<name>) and includes the
prompt name in the provenance preamble.
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


SET_UUID = "00000000-0000-0000-0000-000000000001"


def _named_entry(**kwargs: Any) -> ScopePromptIndexEntry:
    defaults = {
        "name": f"set:{SET_UUID}:outcomes-theory",
        "entry_kind": "named_prompt",
        "scope_type": "set",
        "scope_id": SET_UUID,
        "scope_name": "DoView Book",
        "description": "Outcomes-theory text response.",
        "body": "Apply outcomes theory rules.",
        "prompt_name": "outcomes-theory",
    }
    defaults.update(kwargs)
    return ScopePromptIndexEntry(**defaults)


class TestGetPromptNamed:
    @pytest.mark.asyncio
    async def test_named_prompt_happy_path(self) -> None:
        client: Any = _StubClient([_named_entry()])
        result = await iris_prompts.get_prompt(client, f"set:{SET_UUID}:outcomes-theory")
        assert len(result.messages) == 1
        msg = result.messages[0]
        assert msg.role == "user"
        text = msg.content.text
        # Body present.
        assert "Apply outcomes theory rules." in text
        # Preamble includes prompt name.
        assert 'prompt "outcomes-theory"' in text
        # Scope name present.
        assert '"DoView Book"' in text

    @pytest.mark.asyncio
    async def test_three_segment_name_rejected_when_malformed(self) -> None:
        client: Any = _StubClient([])
        # UPPERCASE in prompt segment is not allowed by the regex.
        with pytest.raises(ValueError, match="Invalid Iris prompt name"):
            await iris_prompts.get_prompt(client, f"set:{SET_UUID}:Has-Upper")

    @pytest.mark.asyncio
    async def test_unknown_named_prompt_raises(self) -> None:
        client: Any = _StubClient([])
        with pytest.raises(ValueError, match="not found"):
            await iris_prompts.get_prompt(client, f"set:{SET_UUID}:nope")

    @pytest.mark.asyncio
    async def test_description_includes_prompt_name(self) -> None:
        client: Any = _StubClient([_named_entry()])
        result = await iris_prompts.get_prompt(client, f"set:{SET_UUID}:outcomes-theory")
        assert result.description == "Set: DoView Book — outcomes-theory — Outcomes-theory text response."
