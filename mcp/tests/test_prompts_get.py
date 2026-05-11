"""ADR-152: MCP `prompts/get` handler.

Resolves an `iris:set:<uuid>` or `iris:collection:<uuid>` name and
returns a single user-role MCP message with the system_prompt body
preceded by a provenance preamble.
"""

from __future__ import annotations

from typing import Any

import pytest
from iris_client.models.core import ScopePromptIndexEntry
from mcp import types

from iris_mcp import prompts as iris_prompts


class _StubClient:
    def __init__(self, entries: list[ScopePromptIndexEntry]) -> None:
        self._entries = entries

    async def list_scope_prompts(self) -> list[ScopePromptIndexEntry]:
        return list(self._entries)


def _entry(**kwargs: Any) -> ScopePromptIndexEntry:
    defaults = {
        "name": "iris:set:11111111-1111-1111-1111-111111111111",
        "scope_type": "set",
        "scope_id": "11111111-1111-1111-1111-111111111111",
        "scope_name": "DoView Book",
        "description": None,
        "body": "Use outcomes theory framing.",
    }
    defaults.update(kwargs)
    return ScopePromptIndexEntry(**defaults)


class TestGetPromptHappyPath:
    @pytest.mark.asyncio
    async def test_set_returns_single_user_message(self) -> None:
        client: Any = _StubClient([_entry()])
        result = await iris_prompts.get_prompt(
            client, "iris:set:11111111-1111-1111-1111-111111111111",
        )

        assert isinstance(result, types.GetPromptResult)
        assert len(result.messages) == 1
        msg = result.messages[0]
        assert msg.role == "user"
        assert isinstance(msg.content, types.TextContent)
        # Body must be present.
        assert "Use outcomes theory framing." in msg.content.text
        # Preamble must announce the scope by name and type.
        assert "DoView Book" in msg.content.text
        assert "Set" in msg.content.text

    @pytest.mark.asyncio
    async def test_collection_returns_user_message(self) -> None:
        entry = _entry(
            name="iris:collection:22222222-2222-2222-2222-222222222222",
            scope_type="collection",
            scope_id="22222222-2222-2222-2222-222222222222",
            scope_name="NZISM",
            body="Always cite the control number.",
        )
        client: Any = _StubClient([entry])
        result = await iris_prompts.get_prompt(
            client, "iris:collection:22222222-2222-2222-2222-222222222222",
        )
        assert "Always cite the control number." in result.messages[0].content.text
        assert "Collection" in result.messages[0].content.text
        assert "NZISM" in result.messages[0].content.text

    @pytest.mark.asyncio
    async def test_includes_web_url_when_iris_web_url_set(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setenv("IRIS_WEB_URL", "https://iris-uat.chrisbarlow.nz")
        client: Any = _StubClient([_entry()])
        result = await iris_prompts.get_prompt(
            client, "iris:set:11111111-1111-1111-1111-111111111111",
        )
        text = result.messages[0].content.text
        assert "https://iris-uat.chrisbarlow.nz/sets/11111111-1111-1111-1111-111111111111" in text

    @pytest.mark.asyncio
    async def test_omits_web_url_when_iris_web_url_unset(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.delenv("IRIS_WEB_URL", raising=False)
        client: Any = _StubClient([_entry()])
        result = await iris_prompts.get_prompt(
            client, "iris:set:11111111-1111-1111-1111-111111111111",
        )
        text = result.messages[0].content.text
        # No URL anywhere in the preamble.
        assert "https://" not in text.split("\n\n")[0]


class TestGetPromptErrors:
    @pytest.mark.asyncio
    async def test_malformed_name_raises_value_error(self) -> None:
        client: Any = _StubClient([])
        with pytest.raises(ValueError, match="Invalid Iris scope-prompt name"):
            await iris_prompts.get_prompt(client, "nope")

    @pytest.mark.asyncio
    async def test_wrong_scope_type_in_name_raises(self) -> None:
        client: Any = _StubClient([])
        with pytest.raises(ValueError, match="Invalid Iris scope-prompt name"):
            await iris_prompts.get_prompt(
                client, "iris:diagram:11111111-1111-1111-1111-111111111111",
            )

    @pytest.mark.asyncio
    async def test_unknown_uuid_raises(self) -> None:
        client: Any = _StubClient([])  # empty index
        with pytest.raises(ValueError, match="not found"):
            await iris_prompts.get_prompt(
                client, "iris:set:99999999-9999-9999-9999-999999999999",
            )
