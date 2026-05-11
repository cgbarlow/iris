"""Hand-curated response models for the v1 iris-client surface.

These mirror the backend's Pydantic response models so callers get typed
results without needing the backend running to regenerate them. Once
`iris-client-regen` is run against a live backend (SPEC-132-A), the
`generated.py` module supersedes this file. Until then, hand-curation
keeps the client fully usable in isolation.

Extras are permitted (`model_config = {"extra": "allow"}`) so backend
field additions do not break downstream callers.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class _Permissive(BaseModel):
    """Base with `extra="allow"` so backend additions don't break clients."""

    model_config = ConfigDict(extra="allow")


# --- Auth / Tokens -----------------------------------------------------------

class LoginResponse(_Permissive):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class UserSelf(_Permissive):
    id: str
    username: str
    role: str


class TokenRecord(_Permissive):
    """A PAT as returned by list — never carries the secret."""

    id: str
    name: str
    prefix: str
    created_at: str
    last_used_at: str | None = None
    expires_at: str | None = None
    revoked_at: str | None = None


class TokenCreated(TokenRecord):
    """Create-time response — secret present exactly once."""

    token: str


# --- Search ------------------------------------------------------------------

class SearchResult(_Permissive):
    id: str
    result_type: Literal["element", "diagram", "package", "set", "collection"]
    name: str
    type_detail: str | None = None
    description: str | None = None
    rank: float | None = None
    deep_link: str | None = None
    set_id: str | None = None
    set_name: str | None = None
    collection_name: str | None = None


class SearchResponse(_Permissive):
    query: str
    results: list[SearchResult] = Field(default_factory=list)
    total: int = 0


# --- Entities ----------------------------------------------------------------

class EntityBase(_Permissive):
    id: str
    name: str
    description: str | None = None
    created_at: str
    updated_at: str
    set_id: str | None = None


class Diagram(EntityBase):
    diagram_type: str
    current_version: int
    notation: str = "simple"
    parent_package_id: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class Element(EntityBase):
    element_type: str
    current_version: int
    notation: str = "simple"
    data: dict[str, Any] = Field(default_factory=dict)


class Package(EntityBase):
    current_version: int
    parent_package_id: str | None = None


class IrisSet(EntityBase):
    """Named `IrisSet` because `Set` collides with builtins."""

    collection_id: str | None = None
    system_prompt: str | None = None
    mcp_prompt: str | None = None  # ADR-155 (v5.10.0): MCP-only directive


class Collection(EntityBase):
    system_prompt: str | None = None
    mcp_prompt: str | None = None  # ADR-155 (v5.10.0): MCP-only directive


class ScopePromptIndexEntry(_Permissive):
    """One entry from `GET /api/prompts/scope-index` (ADR-152, v5.8.3;
    extended ADR-154, v5.9.0 to include named prompts).

    Surfaces:
    - every Collection / Set with a non-empty system_prompt (entry_kind
      "system_prompt"); name format `set:<uuid>` / `collection:<uuid>`
    - every named prompt on a Collection / Set (entry_kind "named_prompt");
      name format `set:<uuid>:<prompt_name>` / `collection:<uuid>:<prompt_name>`

    The MCP server maps these into MCP `prompts/list` and `prompts/get`
    responses so Claude Desktop / Claude Code users can invoke them
    explicitly.
    """

    name: str
    entry_kind: Literal["system_prompt", "named_prompt"] = "system_prompt"
    scope_type: Literal["collection", "set"]
    scope_id: str
    scope_name: str
    description: str | None = None
    body: str
    prompt_name: str | None = None  # set only when entry_kind == "named_prompt"


class Version(_Permissive):
    version: int
    name: str
    description: str | None = None
    change_type: str
    change_summary: str | None = None
    created_at: str


# --- AI ----------------------------------------------------------------------

class FileContext(_Permissive):
    filename: str
    text: str


class FileExtractResponse(_Permissive):
    filename: str
    content_type: str
    size_bytes: int
    extracted_text: str
    truncated: bool = False
    error: str | None = None


class QAResponse(_Permissive):
    answer: str
    model_used: str | None = None
    provider_name: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    duration_ms: int | None = None
    conversation_id: str | None = None


class ApplyCreationResponse(_Permissive):
    diagram_ids: list[str] = Field(default_factory=list)
    primary_diagram_id: str | None = None


class Conversation(_Permissive):
    id: str
    set_id: str | None = None
    question: str
    answer: str
    created_at: str
    model_used: str | None = None
    mode: str | None = None
    thread_id: str | None = None
