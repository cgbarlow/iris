"""Pydantic schemas for the AI model management system (ADR-093)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ModelParameters(BaseModel):
    """LLM generation parameters."""

    temperature: float | None = Field(None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(None, ge=1, le=200000)
    top_p: float | None = Field(None, ge=0.0, le=1.0)
    top_k: int | None = Field(None, ge=1)
    min_p: float | None = Field(None, ge=0.0, le=1.0)
    frequency_penalty: float | None = Field(None, ge=-2.0, le=2.0)
    presence_penalty: float | None = Field(None, ge=-2.0, le=2.0)
    stop: list[str] | None = None


class ProviderCreate(BaseModel):
    """Request body for creating an AI provider."""

    name: str = Field(min_length=1, max_length=100)
    provider_type: Literal["openai", "anthropic", "ollama", "lmstudio", "openrouter", "custom"]
    base_url: str | None = None
    api_key: str | None = None  # stored in DB, never returned in responses
    model: str = Field(min_length=1, max_length=200)
    parameters: ModelParameters = Field(default_factory=ModelParameters)
    system_prompt: str | None = None
    timeout_ms: int = Field(30000, ge=1000, le=300000)
    retries: int = Field(3, ge=0, le=10)
    is_default: bool = False
    is_active: bool = True


class ProviderUpdate(BaseModel):
    """Request body for updating an AI provider."""

    name: str = Field(min_length=1, max_length=100)
    provider_type: Literal["openai", "anthropic", "ollama", "lmstudio", "openrouter", "custom"]
    base_url: str | None = None
    api_key: str | None = None  # None = leave existing key unchanged; "" = clear key
    model: str = Field(min_length=1, max_length=200)
    parameters: ModelParameters = Field(default_factory=ModelParameters)
    system_prompt: str | None = None
    timeout_ms: int = Field(30000, ge=1000, le=300000)
    retries: int = Field(3, ge=0, le=10)
    is_default: bool = False
    is_active: bool = True


class ProviderResponse(BaseModel):
    """Response for a single AI provider. API key is never returned."""

    id: str
    name: str
    provider_type: str
    base_url: str | None = None
    has_api_key: bool = False  # true if a key is stored; key value is never returned
    model: str
    parameters: ModelParameters
    system_prompt: str | None = None
    timeout_ms: int
    retries: int
    is_default: bool
    is_active: bool
    created_by: str | None = None
    created_at: str
    updated_at: str


class ActiveProviderResponse(BaseModel):
    """Lightweight provider info for non-admin users (ADR-114)."""

    id: str
    name: str
    model: str
    provider_type: str
    base_url: str | None = None
    is_default: bool = False


class ProviderTestResult(BaseModel):
    """Result of testing a provider connection."""

    ok: bool
    latency_ms: int | None = None
    error: str | None = None


class QARequest(BaseModel):
    """Request body for asking a question about a set."""

    question: str = Field(min_length=1, max_length=4000)
    provider_id: str | None = None
    mode: str | None = None        # 'creation' for diagram creation mode
    notation: str | None = None    # notation to use in creation mode (e.g. 'doview')
    diagram_type: str | None = None  # diagram type for non-DoView creation (ADR-132)
    history: list[dict[str, str]] | None = None  # prior conversation turns for multi-turn creation
    thread_id: str | None = None   # groups messages in a conversation thread


class FileContext(BaseModel):
    """File context included in chat requests (ADR-115)."""

    filename: str
    text: str


class MultiSetQARequest(BaseModel):
    """Request body for asking a question across multiple sets (ADR-102).

    At least one of set_ids, docref_doc_ids, or file_contexts must be non-empty.
    """

    set_ids: list[str] = Field(default_factory=list)
    collection_id: str | None = None
    package_ids: list[str] | None = None
    diagram_ids: list[str] | None = None  # Diagram-level context scoping
    docref_doc_ids: list[str] | None = None  # DocRef legislation document IDs (ADR-112)
    file_contexts: list[FileContext] | None = None  # Session file uploads (ADR-115)
    question: str = Field(min_length=1, max_length=4000)
    provider_id: str | None = None
    mode: str | None = None
    notation: str | None = None
    diagram_type: str | None = None  # ADR-132
    history: list[dict[str, str]] | None = None
    thread_id: str | None = None


class QAResponse(BaseModel):
    """Response for a Q&A request."""

    answer: str
    model_used: str
    provider_name: str
    tokens_in: int | None = None
    tokens_out: int | None = None
    duration_ms: int
    conversation_id: str


class ConversationResponse(BaseModel):
    """Response for a stored conversation."""

    id: str
    set_id: str
    question: str
    answer: str
    model_used: str
    provider_id: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    duration_ms: int | None = None
    created_at: str
    mode: str | None = "discuss"
    set_name: str | None = None
    thread_id: str | None = None


class CreationPromptResponse(BaseModel):
    """Response for a single AI creation or response prompt.

    Despite the name (kept for backwards compat), this model covers
    both `purpose='creation_format'` and `purpose='response_format'`
    rows (ADR-157, v5.12.0). The Admin UI uses `purpose` to segment
    creation-mode prompts from response-format prompts.
    """

    id: str
    name: str
    description: str | None = None
    purpose: str = "creation_format"  # 'creation_format' | 'response_format'
    layer: str
    notation: str | None = None
    diagram_type: str | None = None
    prompt_text: str
    display_order: int
    is_active: bool
    created_by: str | None = None
    created_at: str
    updated_at: str


class CreationPromptCreate(BaseModel):
    """Request body for creating a new AI creation or response prompt.

    Conflict detection (ADR-158, v5.13.0): the server returns 409 if
    another `is_active=true` row already exists with the same
    `(purpose, layer, notation, diagram_type)` tuple. Stage a
    replacement by setting the existing row to `is_active=false`
    first, OR pick a different combination.
    """

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    purpose: Literal[
        "creation_format", "response_format", "mcp_server_instructions",
    ] = "creation_format"
    layer: Literal["base", "notation", "diagram_type", "override"]
    notation: str | None = None
    diagram_type: str | None = None
    prompt_text: str = Field(min_length=1)
    display_order: int = 0
    is_active: bool = True


class CreationPromptUpdate(BaseModel):
    """Request body for updating an AI creation or response prompt.

    v5.13.0 (ADR-158): extends the v5.8.x update surface to allow
    editing `name`, `description`, `notation`, `diagram_type`, and
    `display_order` in addition to `prompt_text` and `is_active`.
    Conflict detection re-runs when any of `(purpose, layer, notation,
    diagram_type)` changes while `is_active=true`. `purpose` and
    `layer` themselves are immutable once created (use delete + create
    if you need to move a prompt between purposes or layers).
    """

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    notation: str | None = None
    diagram_type: str | None = None
    display_order: int | None = None
    prompt_text: str | None = None
    is_active: bool | None = None


class ResponsePromptComposed(BaseModel):
    """Composed response-format body for a (notation, diagram_type)
    cascade (ADR-157, v5.12.0).

    Anonymous-readable: scope content is universal across users; the
    response_format rules are admin-authored and editable but not
    sensitive.
    """

    notation: str
    diagram_type: str | None = None
    body: str  # composed cascade body — may be empty if no rows match


class ServerInstructionsResponse(BaseModel):
    """Singleton MCP-server-instructions body (ADR-163, v5.18.0).

    Returned by `GET /api/ai/server-instructions`. iris-mcp fetches
    this at startup and passes it to the MCP SDK `Server(instructions=…)`
    constructor so every MCP client receives it in the InitializeResult.
    """

    body: str  # may be empty if no active singleton row exists


class ResponseFormatType(BaseModel):
    """One available response-format type — a (notation, diagram_type)
    pair that has at least one active response_format prompt row
    (ADR-157, v5.12.0).

    Surfaced by `GET /api/ai/response-prompts/types` and used by MCP
    clients (via `applicable_response_types` on Set/Collection
    responses) to discover what formats can be composed.
    """

    notation: str
    diagram_type: str | None = None
    label: str  # human-friendly UI label (combines notation + diagram_type names)
    description: str | None = None  # optional description from the diagram_type row


class ApplyCreationRequest(BaseModel):
    """Request body for applying AI-generated diagram JSON."""

    diagrams_json: str  # JSON string produced by the AI
    package_id: str | None = None  # optional parent package for created diagrams


class ApplyCreationResponse(BaseModel):
    """Response after applying AI-generated diagrams."""

    diagram_ids: list[str]
    primary_diagram_id: str | None = None


class FileExtractResponse(BaseModel):
    """Response from file text extraction (ADR-115)."""

    filename: str
    content_type: str
    size_bytes: int
    extracted_text: str
    truncated: bool = False
    error: str | None = None
