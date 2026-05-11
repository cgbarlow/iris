"""ADR-154: iris-client model accepts the extended scope-index shape
that includes named-prompt entries with `entry_kind` and `prompt_name`.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from iris_client import IrisClient
from iris_client.models.core import ScopePromptIndexEntry

BASE = "http://iris.test"


class TestListScopePromptsExtended:
    @pytest.mark.asyncio
    async def test_named_prompt_entry_round_trip(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        respx_mock.get(f"{BASE}/api/prompts/scope-index").mock(
            return_value=httpx.Response(200, json={
                "items": [
                    {
                        "name": "set:s-1",
                        "entry_kind": "system_prompt",
                        "scope_type": "set",
                        "scope_id": "s-1",
                        "scope_name": "DoView Book",
                        "description": "Default directive",
                        "body": "Use outcomes theory framing.",
                        "prompt_name": None,
                    },
                    {
                        "name": "set:s-1:outcomes-theory",
                        "entry_kind": "named_prompt",
                        "scope_type": "set",
                        "scope_id": "s-1",
                        "scope_name": "DoView Book",
                        "description": "Outcomes theory text response.",
                        "body": "Apply outcomes theory rules.",
                        "prompt_name": "outcomes-theory",
                    },
                ],
            }),
        )

        entries = await pat_client.list_scope_prompts()
        assert len(entries) == 2
        sys_entry = entries[0]
        named_entry = entries[1]
        assert sys_entry.entry_kind == "system_prompt"
        assert sys_entry.prompt_name is None
        assert named_entry.entry_kind == "named_prompt"
        assert named_entry.prompt_name == "outcomes-theory"
        assert named_entry.name == "set:s-1:outcomes-theory"

    @pytest.mark.asyncio
    async def test_legacy_payload_without_new_fields_still_validates(
        self, pat_client: IrisClient, respx_mock: respx.Router,
    ) -> None:
        """Backwards-compat: a v5.8.5-era backend that doesn't yet emit
        entry_kind or prompt_name must still produce valid entries
        (defaults: entry_kind='system_prompt', prompt_name=None)."""
        respx_mock.get(f"{BASE}/api/prompts/scope-index").mock(
            return_value=httpx.Response(200, json={
                "items": [
                    {
                        "name": "set:s-1",
                        "scope_type": "set",
                        "scope_id": "s-1",
                        "scope_name": "DoView Book",
                        "description": None,
                        "body": "Use outcomes theory framing.",
                    },
                ],
            }),
        )

        entries = await pat_client.list_scope_prompts()
        assert len(entries) == 1
        assert entries[0].entry_kind == "system_prompt"
        assert entries[0].prompt_name is None

    @pytest.mark.asyncio
    async def test_model_round_trip_independent_of_client(self) -> None:
        """ScopePromptIndexEntry alone must accept both shapes."""
        legacy = ScopePromptIndexEntry.model_validate({
            "name": "set:s-1",
            "scope_type": "set",
            "scope_id": "s-1",
            "scope_name": "X",
            "description": None,
            "body": "y",
        })
        assert legacy.entry_kind == "system_prompt"
        assert legacy.prompt_name is None

        extended = ScopePromptIndexEntry.model_validate({
            "name": "set:s-1:np",
            "entry_kind": "named_prompt",
            "scope_type": "set",
            "scope_id": "s-1",
            "scope_name": "X",
            "description": None,
            "body": "y",
            "prompt_name": "np",
        })
        assert extended.entry_kind == "named_prompt"
        assert extended.prompt_name == "np"
