"""Pydantic models for the artefacts module (ADR-179, v6.2.0)."""

from __future__ import annotations

from pydantic import BaseModel


class ArtefactResponse(BaseModel):
    """Response after a successful artefact create / fetch metadata.

    The `web_url` field is fully-qualified when `IRIS_WEB_URL` is set
    (decorated by `mcp.links.with_web_url`); empty/absent otherwise so
    backend responses don't leak the host. MCP-side tools decorate
    based on their own configured backend URL.
    """

    id: str
    filename: str
    mime_type: str
    size_bytes: int
    source_kind: str
    source_ref: str | None = None
    created_at: str
