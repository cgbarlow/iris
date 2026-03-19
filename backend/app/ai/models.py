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
    api_key_env_var: str | None = None
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
    api_key_env_var: str | None = None
    model: str = Field(min_length=1, max_length=200)
    parameters: ModelParameters = Field(default_factory=ModelParameters)
    system_prompt: str | None = None
    timeout_ms: int = Field(30000, ge=1000, le=300000)
    retries: int = Field(3, ge=0, le=10)
    is_default: bool = False
    is_active: bool = True


class ProviderResponse(BaseModel):
    """Response for a single AI provider."""

    id: str
    name: str
    provider_type: str
    base_url: str | None = None
    api_key_env_var: str | None = None
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
