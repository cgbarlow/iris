"""Pydantic models for DocRef legislation extension (ADR-112)."""

from __future__ import annotations

from pydantic import BaseModel


class DocRefDocument(BaseModel):
    """Response model for a single DocRef document."""

    id: str
    slug: str
    title: str
    latest_version: str
    source_url: str
    csv_url: str
    chunk_count: int = 0
    status: str = "available"
    error_message: str | None = None
    imported_at: str | None = None
    imported_by: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class DocRefDocumentListResponse(BaseModel):
    """Response model for listing DocRef documents."""

    items: list[DocRefDocument]


class DocRefImportResponse(BaseModel):
    """Response after importing a document's chunks."""

    document_id: str
    status: str
    chunk_count: int


class DocRefRefreshResponse(BaseModel):
    """Response after refreshing the document index from DocRef."""

    documents_found: int
    new_documents: int
    updated_documents: int
