"""Pydantic models for the scope-prompt index endpoint (ADR-152)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ScopePromptIndexEntry(BaseModel):
    """One row in the scope-prompt index.

    Consumed by the Iris MCP server to populate `prompts/list` and
    `prompts/get` responses. `name` is the stable MCP prompt URI:

    - `<scope_type>:<scope_id>` for the scope's `system_prompt`
      (entry_kind `"system_prompt"`)
    - `<scope_type>:<scope_id>:<prompt_name>` for a named prompt
      (entry_kind `"named_prompt"`, ADR-154)

    v5.8.5 (ADR-153) dropped the `iris:` prefix; MCP clients already
    namespace prompts by server name (e.g. `/iris:set:<uuid>` in
    Claude Code's slash menu). The body field carries the full prompt
    body so a single MCP `prompts/get` can be served without a
    follow-up HTTP round-trip.
    """

    name: str
    entry_kind: Literal["system_prompt", "named_prompt"] = "system_prompt"
    scope_type: Literal["collection", "set"]
    scope_id: str
    scope_name: str
    description: str | None = None
    body: str
    prompt_name: str | None = None  # set only when entry_kind == "named_prompt"


class ScopePromptIndexResponse(BaseModel):
    items: list[ScopePromptIndexEntry]
