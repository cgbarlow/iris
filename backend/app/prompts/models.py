"""Pydantic models for the scope-prompt index endpoint (ADR-152)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ScopePromptIndexEntry(BaseModel):
    """One row in the scope-prompt index.

    Consumed by the Iris MCP server to populate `prompts/list` and
    `prompts/get` responses. `name` is the stable MCP prompt URI of
    the form `<scope_type>:<scope_id>` (v5.8.5: dropped the
    `iris:` prefix; MCP clients already namespace prompts by server
    name, e.g. `/iris:set:<uuid>` in Claude Code's slash menu). The
    body field carries the scope's full `system_prompt` so a single
    MCP `prompts/get` can be served without a follow-up HTTP
    round-trip.
    """

    name: str
    scope_type: Literal["collection", "set"]
    scope_id: str
    scope_name: str
    description: str | None = None
    body: str


class ScopePromptIndexResponse(BaseModel):
    items: list[ScopePromptIndexEntry]
