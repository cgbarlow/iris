"""Pydantic schemas for the AI model management system (ADR-093)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ModelParameters(BaseModel):
    """LLM generation parameters."""

    temperature: float | None = Field(None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(None, ge=1, le=200000)
    top_p: float | None = Field(None, ge=0.0, le=1.0)


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
    history: list[dict[str, str]] | None = None  # prior conversation turns for multi-turn creation
    thread_id: str | None = None   # groups messages in a conversation thread


class MultiSetQARequest(BaseModel):
    """Request body for asking a question across multiple sets (ADR-102)."""

    set_ids: list[str] = Field(min_length=1)
    collection_id: str | None = None
    package_ids: list[str] | None = None
    docref_doc_ids: list[str] | None = None  # DocRef legislation document IDs (ADR-112)
    question: str = Field(min_length=1, max_length=4000)
    provider_id: str | None = None
    mode: str | None = None
    notation: str | None = None
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
    """Response for a single AI creation prompt."""

    id: str
    name: str
    description: str | None = None
    layer: str
    notation: str | None = None
    diagram_type: str | None = None
    prompt_text: str
    display_order: int
    is_active: bool
    created_by: str | None = None
    created_at: str
    updated_at: str


class CreationPromptUpdate(BaseModel):
    """Request body for updating an AI creation prompt."""

    prompt_text: str | None = None
    is_active: bool | None = None


class ApplyCreationRequest(BaseModel):
    """Request body for applying AI-generated diagram JSON."""

    diagrams_json: str  # JSON string produced by the AI
    package_id: str | None = None  # optional parent package for created diagrams


class ApplyCreationResponse(BaseModel):
    """Response after applying AI-generated diagrams."""

    diagram_ids: list[str]
    primary_diagram_id: str | None = None
